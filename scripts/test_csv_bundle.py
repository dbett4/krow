"""Fresh extraction under clean environment without site packages or wk on PATH."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
from test_csv_review import request  # noqa: E402
from test_review_decisions import SCOPE, decision  # noqa: E402


def test_bundle_reproducible_and_runs_without_credentials_or_site_packages(tmp_path):
    command = [sys.executable, str(ROOT / "scripts/build_csv_review_bundle.py")]
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    for output in (first, second):
        subprocess.run(command + [str(output)], check=True, capture_output=True, text=True, timeout=5)
    assert first.read_bytes() == second.read_bytes()
    assert subprocess.run(command + [str(first)], capture_output=True, timeout=5).returncode != 0
    extract = tmp_path / "extracted"
    with zipfile.ZipFile(first) as bundle:
        assert {"server/csv_native.py", "server/csv_context.py", "server/csv_checks.py"} <= set(bundle.namelist())
        assert not any(".env" in p or "local-config" in p or p.endswith(".pem") for p in bundle.namelist())
        bundle.extractall(extract)
    home = tmp_path / "empty-home"; home.mkdir()
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"}
    log_path = tmp_path / "preview.log"
    with log_path.open("w+") as log:
        process = subprocess.Popen([sys.executable, "-S", "server/csv_review.py", "--port", "0"],
                                   cwd=extract, env=env, stdout=log, stderr=log)
        try:
            for _ in range(100):
                log.seek(0); text = log.read()
                assert process.poll() is None, text
                if "ready on port " in text:
                    url = "http://127.0.0.1:" + text.split("ready on port ")[1].split(";")[0]
                    break
                time.sleep(.05)
            else:
                pytest.fail("Fresh bundle did not start")
            for asset in ("/", "/csv-review.js", "/csv-review.css", "/setup.css", "/icon.png"):
                assert request(url, path=asset, method="GET")[0] == 200
            assert request(url, path="/api/schema", body={})[0] == 400
            source = "period,currency,unit,amount\n2026-10,USD,cents,1001\n2026-10,USD,cents,-2\n"
            arguments = {"csv_text": source, "columns": [{"name": name, "type": "integer" if name == "amount" else "string"}
                          for name in ("period", "currency", "unit", "amount")], "key_columns": [],
                         "reporting_policy": {"period_column": "period", "expected_period": "2026-10",
                          "currency_column": "currency", "expected_currency": "USD", "unit_column": "unit",
                          "expected_unit": "cents", "amount_columns": ["amount"], "accounting_basis": "accrual"}}
            status, _, raw = request(url, body=arguments)
            packet = json.loads(raw)
            assert status == 200 and packet["reporting_context"]["status"] == "matched"
            assert packet["result"]["numeric_totals"]["amount"]["total"] == "999"
            assert packet["workiva_requests"] == 0 and packet["period_and_units_verified"] is False
            saved, csv_path = tmp_path / "packet.json", tmp_path / "input.csv"
            saved.write_bytes(raw); csv_path.write_text(source)
            replay = subprocess.run([sys.executable, "-S", "server/csv_review.py", "--verify-packet", str(saved), "--csv", str(csv_path)],
                                    cwd=extract, env=env, capture_output=True, text=True, timeout=5)
            assert replay.returncode == 0 and json.loads(replay.stdout)["status"] == "reproduced"
        finally:
            process.terminate(); process.wait(timeout=5)
    assert list(home.iterdir()) == []
    assert not list(extract.rglob("__pycache__"))


def test_timed_isolated_journal_onboarding_restart_and_backup_readback(tmp_path):
    started = time.monotonic()
    stages = {}
    archive = tmp_path / "candidate.zip"
    subprocess.run([sys.executable, str(ROOT / "scripts/build_csv_review_bundle.py"), str(archive)],
                   check=True, capture_output=True, timeout=5)
    extract = tmp_path / "extracted"
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(extract)
    stages["bundle_extract_seconds"] = time.monotonic() - started
    home = tmp_path / "home"; home.mkdir()
    private = tmp_path / "private"; private.mkdir(mode=0o700)
    journal = private / "review.db"
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"}
    source = {"csv_text": "id,amount\n001,100.01\n1,-0.02\n001,bad\n",
              "columns": [{"name": "id", "type": "string"}, {"name": "amount", "type": "decimal"}],
              "key_columns": ["id"], "review_scope": SCOPE}
    startup_seconds = []
    for phase in ("first_inspection", "restart", "restored_backup"):
        phase_start = time.monotonic()
        log_path = tmp_path / (phase + ".log")
        with log_path.open("w+") as log:
            process = subprocess.Popen([sys.executable, "-S", "server/csv_review.py", "--port", "0",
                                        "--review-db", str(journal)], cwd=extract, env=env, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    log.seek(0); text = log.read()
                    assert process.poll() is None, text
                    if "ready on port " in text:
                        url = "http://127.0.0.1:" + text.split("ready on port ")[1].split(";")[0]
                        break
                    time.sleep(.05)
                else:
                    pytest.fail("Isolated journal failed to start")
                startup_seconds.append(time.monotonic() - phase_start)
                if phase == "first_inspection":
                    status, _, raw = request(url, body=source)
                    observed = json.loads(raw)
                    assert status == 200 and observed["packet"]["result"]["numeric_totals"]["amount"]["total"] == "99.99"
                    stages["time_to_real_inspection_seconds"] = time.monotonic() - started
                    confirmation = decision(observed["saved_review"])
                    assert request(url, "/api/review-decisions", body=confirmation)[0] == 200
                else:
                    status, _, raw = request(url, "/api/review-history", body={"scope": SCOPE})
                    readback = json.loads(raw)
                    assert status == 200 and readback["history_count"] == 1
                    assert readback["history"][0]["reason"] == confirmation["reason"]
                    assert any(f["state"] == "accepted_exception" for f in readback["findings"])
                    assert request(url, "/api/review-decisions", body=confirmation)[0] == 400
                # Native access fails closed, without credentials or grant provisioning.
                assert request(url, "/api/schema", body={})[0] == 400
                for path in ("/api/apply", "/api/import", "/api/undo", "/api/approve"):
                    assert request(url, path, body={"confirmed": True})[0] == 404
                assert request(url, "/api/review-decisions", body={**confirmation, "confirmed": False})[0] == 400
            finally:
                process.terminate(); process.wait(timeout=5)
        stages[phase + "_seconds"] = time.monotonic() - phase_start
        if phase == "restart":
            backup = tmp_path / "backup"; backup.mkdir(mode=0o700)
            restored = backup / "review.db"
            shutil.copyfile(journal, restored); restored.chmod(0o600)
            assert restored.read_bytes() == journal.read_bytes()
            journal = restored
    assert stages["time_to_real_inspection_seconds"] < 600
    assert os.stat(journal).st_mode & 0o777 == 0o600
    assert list(home.iterdir()) == [] and not list(extract.rglob("__pycache__"))
    (tmp_path / "timed-onboarding.json").write_text(json.dumps({
        "status": "automated_isolated_smoke_passed", "independent_reviewer_verified": False,
        "clean_machine_verified": False, "native_acceptance_verified": False,
        "environment": "existing VPS; empty HOME, minimal PATH, Python -S; no credentials",
        "stages": stages, "startup_seconds": startup_seconds,
        "total_seconds": time.monotonic() - started}, indent=2))

"""Fresh extraction under clean environment without site packages or wk on PATH."""
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
from test_csv_review import request  # noqa: E402


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

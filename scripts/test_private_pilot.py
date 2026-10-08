"""Shipped-guide fresh-browser handoff rehearsal; not independent human acceptance."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import zipfile

from test_durable_review_browser import ROOT, service
sys.path.insert(0, str(ROOT / "server"))
from test_csv_review import request


def test_extracted_packet_handoff_replay_fresh_review_and_restart(tmp_path):
    start = time.monotonic()
    archive = tmp_path / "candidate.zip"
    subprocess.run([sys.executable, str(ROOT / "scripts/build_csv_review_bundle.py"), str(archive)],
                   check=True, capture_output=True, timeout=5)
    runtime = tmp_path / "extracted"
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(runtime)
    assert "Continue a previous CSV review" in (runtime / "docs/csv-review.md").read_text()
    home = tmp_path / "empty-home"; home.mkdir()
    private = tmp_path / "private"
    runtime_env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"}
    executable = shutil.which("agent-browser"); assert executable
    session = "wingman-pilot-" + uuid.uuid4().hex[:8]
    env = {**os.environ, "AGENT_BROWSER_ENGINE": "chrome"}
    interaction_count = 0
    def run(*args):
        nonlocal interaction_count
        if args[0] in {"open", "click", "upload", "fill", "check", "download"}:
            interaction_count += 1
        if args[0] in {"click", "fill", "check", "download"}:
            # Scroll before Chrome coordinate actions after dynamic layout changes.
            subprocess.run([executable, "--session", session, "eval",
                            "document.querySelector(" + json.dumps(args[1]) + ").scrollIntoView({block:'center'})"],
                           env=env, check=True, capture_output=True, text=True, timeout=10)
        result = subprocess.run([executable, "--session", session, *args], env=env,
                                capture_output=True, text=True, timeout=45)
        if result.returncode:
            state = subprocess.run([executable, "--session", session, "eval", "JSON.stringify({message:document.getElementById('message')?.textContent,replay:document.getElementById('replay-status')?.textContent,disabled:document.getElementById('replay')?.disabled})"],
                                   env=env, capture_output=True, text=True, timeout=10)
            raise AssertionError(result.stdout + result.stderr + state.stdout)
        return result.stdout
    def check(expression):
        run("eval", "(() => { if (!(" + expression + ")) throw new Error('Pilot assertion'); return true; })()")
    source = "id,period,currency,unit,amount\n041,2026-10,USD,cents,1037\n4,2026-10,USD,cents,-11\n042,2026-09,EUR,units,bad\n"
    source_path = tmp_path / "original.csv"; source_path.write_text(source)
    schema = [{"name": name, "type": "integer" if name == "amount" else "string", "required": True}
              for name in ("id", "period", "currency", "unit", "amount")]
    policy = {"period_column": "period", "expected_period": "2026-10", "currency_column": "currency",
              "expected_currency": "USD", "unit_column": "unit", "expected_unit": "cents",
              "amount_columns": ["amount"], "accounting_basis": "modified_accrual"}
    try:
        with service(private, runtime, runtime_env) as url:
            # Source-owner packet comes from the real extracted HTTP validator.
            status, _, raw = request(url, body={"csv_text": source, "columns": schema, "key_columns": ["id"], "reporting_policy": policy})
            assert status == 200
            packet_path = tmp_path / "owner-evidence.json"; packet_path.write_bytes(raw)
            run("open", url); run("set", "media", "light"); run("set", "viewport", "1440", "1000")
            run("screenshot", str(tmp_path / "pilot-default.png"), "--full")
            check("localStorage.length===0 && sessionStorage.length===0 && document.getElementById('download').disabled")
            run("click", "#handoff-options > summary")
            run("upload", "#file", str(source_path))
            run("upload", "#packet-file", str(packet_path))
            run("wait", "--fn", "document.getElementById('message').textContent.includes('Packet policy loaded')")
            check("document.getElementById('columns').children.length===5 && document.getElementById('expected-period').value==='2026-10' && document.getElementById('amount-columns').value==='amount' && !document.getElementById('save-review').checked")
            run("click", "#replay")
            run("wait", "--fn", "document.getElementById('replay-status').textContent.startsWith('Evidence reproduced')")
            time_to_reproduced = time.monotonic() - start
            actions_to_reproduced = interaction_count
            check("document.getElementById('download').disabled && document.getElementById('replay-status').textContent.includes('No authorship, current native schema or approval verified')")
            run("screenshot", str(tmp_path / "pilot-reproduced.png"), "--full")
            run("click", "#check")
            run("wait", "--fn", "!document.getElementById('download').disabled")
            check("document.querySelector('#results code').textContent==='1026' && document.querySelector('.result-title').textContent==='Reporting context needs review' && document.querySelector('.total small').textContent.includes('Partial total')")
            time_to_inspection = time.monotonic() - start
            run("download", "#download", str(tmp_path / "fresh-evidence.json"))
            fresh = json.loads((tmp_path / "fresh-evidence.json").read_text())
            assert fresh["review_state"] == "unreviewed" and fresh["workiva_requests"] == 0
            assert fresh["reporting_policy"] == policy and fresh["result"]["issue_count"] == 1
            assert fresh["reporting_context"]["issue_count"] == 3
            run("fill", "#csv", source.replace("1037", "1038"))
            check("document.getElementById('download').disabled && document.getElementById('replay-status').textContent===''")
            run("click", "#replay")
            run("wait", "--fn", "document.getElementById('replay-status').textContent.includes('Evidence mismatch')")
            run("set", "viewport", "390", "1000"); run("set", "media", "dark")
            check("document.documentElement.scrollWidth<=innerWidth")
            run("screenshot", str(tmp_path / "pilot-mismatch-narrow-dark.png"), "--full")
            # Bad JSON/journal handoff cannot replace declared controls or source.
            invalid = tmp_path / "invalid.json"; invalid.write_text('{"scope":{"workspace":"synthetic"},"history":[]}')
            run("upload", "#packet-file", str(invalid))
            run("wait", "--fn", "document.getElementById('message').textContent.includes('not journal handoff')")
            check("document.getElementById('columns').children.length===5 && document.getElementById('csv').value.includes('1038') && document.getElementById('replay').disabled")
            run("upload", "#packet-file", str(packet_path))
            run("wait", "--fn", "document.getElementById('message').textContent.includes('Packet policy loaded')")
            run("fill", "#csv", source)
            run("wait", "--fn", "!document.getElementById('replay').disabled")
            run("check", "#save-review")
            for selector, value in (("#scope-workspace", "synthetic pilot"), ("#scope-file", "copy A"), ("#scope-period", "2026-10")):
                run("fill", selector, value)
            run("click", "#check")
            run("wait", "--fn", "document.querySelectorAll('.decision-card').length===4")
            run("fill", ".decision-card:first-of-type input:not([type=checkbox])", "Pilot rehearsal reviewer")
            run("fill", ".decision-card:first-of-type textarea", "Synthetic issue remains for source-owner correction; not approval")
            run("check", ".decision-card:first-of-type input[type=checkbox]")
            run("click", ".decision-card:first-of-type button")
            run("wait", "--fn", "document.getElementById('message').textContent.includes('saved and read back')")
            run("download", "#review-journal > button", str(tmp_path / "journal-handoff.json"))
            assert json.loads((tmp_path / "journal-handoff.json").read_text())["history_count"] == 1
            assert not run("errors").strip()
            run("close")
        with service(private, runtime, runtime_env) as url:
            run("open", url)
            run("wait", "--fn", "!document.getElementById('durable-options').hidden")
            run("check", "#save-review")
            for selector, value in (("#scope-workspace", "synthetic pilot"), ("#scope-file", "copy A"), ("#scope-period", "2026-10")):
                run("fill", selector, value)
            run("click", "#load-review")
            run("wait", "--fn", "document.getElementById('review-journal').textContent.includes('Pilot rehearsal reviewer')")
            check("!document.querySelector('.decision-card form') && document.getElementById('download').disabled")
            run("click", "#clear")
            check("document.getElementById('csv').value==='' && document.getElementById('replay').disabled")
        assert time_to_inspection <= 600 and time_to_reproduced <= 600
        (tmp_path / "pilot-rehearsal.json").write_text(json.dumps({
            "status": "fresh_extracted_browser_rehearsal_passed", "time_to_reproduced_seconds": time_to_reproduced,
            "time_to_real_inspection_seconds": time_to_inspection, "actions_to_reproduced": actions_to_reproduced,
            "manual_schema_or_context_fields": 0, "total_seconds": time.monotonic() - start,
            "independent_human_verified": False, "clean_machine_verified": False, "native_import_verified": False,
            "workiva_requests": 0, "limits": "Automated builder rehearsal using shipped guide; no independent unaided-human claim."}, indent=2))
    finally:
        run("close")

"""Real process restart, HTTP confirmation and Chromium private-journal workflow."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
from test_csv_review import INPUT, request
from test_review_decisions import SCOPE, decision


@contextmanager
def service(folder, runtime=ROOT, env=None):
    folder.mkdir(mode=0o700, exist_ok=True)
    with (folder / "output.log").open("w+") as log:
        process = subprocess.Popen([sys.executable, "-S", str(runtime / "server/csv_review.py"), "--port", "0",
                                    "--review-db", str(folder / "review.db")], cwd=runtime, env=env, stdout=log, stderr=log)
        try:
            for _ in range(100):
                log.seek(0); text = log.read()
                assert process.poll() is None, text
                if "ready on port " in text:
                    yield "http://127.0.0.1:" + text.split("ready on port ")[1].split(";")[0]
                    return
                time.sleep(.05)
            raise AssertionError("Private review service did not start")
        finally:
            process.terminate(); process.wait(timeout=5)


def test_http_restart_double_confirm_and_lost_response_reconciliation(tmp_path):
    folder = tmp_path / "private"
    with service(folder) as url:
        assert json.loads(request(url, "/api/review-config", method="GET")[2])["durable_review_enabled"]
        status, _, raw = request(url, body={**INPUT, "review_scope": SCOPE})
        saved = json.loads(raw)
        assert status == 200 and saved["packet"]["review_state"] == "unreviewed"
        confirmation = decision(saved["saved_review"])
        assert request(url, "/api/review-decisions", body={**confirmation, "confirmed": False})[0] == 400
        with ThreadPoolExecutor(2) as pool:
            replies = list(pool.map(lambda _: request(url, "/api/review-decisions", body=confirmation)[0], range(2)))
        assert sorted(replies) == [200, 400]
        # Treat the success response as lost; reconcile history rather than retry.
    with service(folder) as url:
        history = json.loads(request(url, "/api/review-history", body={"scope": SCOPE})[2])
        assert history["history_count"] == 1 and history["history"][0]["decision"] == "accepted_exception"
        assert request(url, "/api/review-decisions", body=confirmation)[0] == 400
        assert request(url, "/api/review-history", body={"scope": SCOPE}, headers={"Origin": "https://foreign.invalid"})[0] == 403
        status, _, raw = request(url, body={**INPUT, "csv_text": INPUT["csv_text"].replace("bad", "changed"), "review_scope": SCOPE})
        assert status == 200
        assert next(f for f in json.loads(raw)["saved_review"]["findings"] if f["location"]["code"] == "invalid_value_type")["state"] == "open"


def test_browser_saved_review_accept_reopen_handoff_and_uncertain_response(tmp_path):
    executable = shutil.which("agent-browser"); assert executable
    session = "wingman-journal-" + uuid.uuid4().hex[:8]
    env = {**os.environ, "AGENT_BROWSER_ENGINE": "chrome"}
    def run(*args):
        result = subprocess.run([executable, "--session", session, *args], env=env,
                                capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout
    def check(expression):
        run("eval", "(() => { if (!(" + expression + ")) throw new Error('Journal assertion'); return true; })()")
    def confirm():
        run("fill", ".decision-card:first-of-type input:not([type=checkbox])", "Synthetic reviewer")
        run("fill", ".decision-card:first-of-type textarea", "Synthetic exception for calibration only")
        run("check", ".decision-card:first-of-type input[type=checkbox]")
        run("click", ".decision-card:first-of-type button")
    with service(tmp_path / "private") as url:
        try:
            run("open", url); run("click", "#sample")
            run("wait", "--fn", "!document.getElementById('durable-options').hidden")
            run("check", "#save-review")
            for selector, value in [("#scope-workspace", "synthetic"), ("#scope-file", "original"), ("#scope-period", "2026-10")]:
                run("fill", selector, value)
            run("click", "#check")
            run("wait", "--fn", "document.querySelectorAll('.decision-card').length === 2")
            check("[...document.querySelectorAll('.decision-state')].every(n=>n.textContent==='open')")
            confirm()
            run("wait", "--fn", "document.getElementById('message').textContent.includes('saved and read back')")
            check("document.querySelectorAll('.finding').length===2 && document.querySelector('.decision-state').textContent==='accepted exception'")
            run("screenshot", str(tmp_path / "journal-accepted-desktop.png"), "--full")
            run("download", "#review-journal > button", str(tmp_path / "handoff.json"))
            handoff = json.loads((tmp_path / "handoff.json").read_text())
            assert handoff["history_count"] == 1 and not handoff["approval_verified"]
            assert "Finance" not in json.dumps(handoff)
            confirm()
            run("wait", "--fn", "document.querySelector('.decision-state').textContent==='open'")
            # Commit succeeds but browser loses the response. UI must not claim success.
            run("eval", "window.originalFetch=fetch; window.fetch=async(...args)=>{const reply=await window.originalFetch(...args); if(args[0]==='/api/review-decisions') throw new TypeError('response lost'); return reply}")
            confirm()
            run("wait", "--fn", "document.getElementById('message').textContent.includes('uncertain confirmation')")
            run("eval", "window.fetch=window.originalFetch")
            run("click", "#load-review")
            run("wait", "--fn", "document.getElementById('message').textContent.includes('Saved review loaded')")
            check("document.querySelector('.decision-state').textContent==='accepted exception' && !document.querySelector('.decision-card form')")
            run("set", "viewport", "390", "1000"); run("set", "media", "dark")
            check("document.documentElement.scrollWidth <= innerWidth")
            run("screenshot", str(tmp_path / "journal-historical-narrow-dark.png"), "--full")
            run("fill", "#csv", "department,actual\nFinance,1250.25\nOperations,-50.10\nFinance,changed\n")
            check("!document.querySelector('.decision-card') && document.getElementById('download').disabled")
            run("click", "#check")
            run("wait", "--fn", "document.querySelectorAll('.decision-card').length === 2")
            check("[...document.querySelectorAll('.decision-state')].every(n=>n.textContent==='open')")
            run("screenshot", str(tmp_path / "journal-changed-narrow-dark.png"), "--full")
            run("fill", "#csv", "department\nFinance\n")
            run("click", "#check")
            run("wait", "--fn", "document.getElementById('review-journal').textContent.includes('Incomplete coverage')")
            check("document.getElementById('review-journal').textContent.includes('not revisited')")
            run("screenshot", str(tmp_path / "journal-partial-narrow-dark.png"), "--full")
            assert not run("errors").strip()
        finally:
            run("close")

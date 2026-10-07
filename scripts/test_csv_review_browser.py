"""Real Chromium UI/HTTP/download checks for the credential-free CSV workflow."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from test_csv_review import csv_url  # noqa: F401,E402


def test_csv_review_browser(csv_url, tmp_path):
    executable = shutil.which("agent-browser")
    assert executable
    session = "wingman-csv-" + uuid.uuid4().hex[:8]
    env = {**os.environ, "AGENT_BROWSER_ENGINE": "chrome"}

    def run(*args):
        result = subprocess.run([executable, "--session", session, *args], env=env,
                                capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    def check(expression):
        run("eval", "(() => { if (!(" + expression + ")) throw new Error('CSV browser assertion failed'); return true; })()")

    def submit():
        run("focus", "#check")
        run("press", "Enter")
        run("wait", "--fn", "!document.getElementById('download').disabled")

    try:
        run("open", csv_url)
        check("!navigator.userAgent.includes('Lightpanda') && document.styleSheets.length === 2")
        check("document.getElementById('download').disabled && localStorage.length === 0 && sessionStorage.length === 0")
        run("click", "#sample")
        submit()
        check("document.querySelector('#results code').textContent === '1200.15'")
        check("document.querySelectorAll('.finding').length === 2 && document.getElementById('results').textContent.includes('Partial total')")
        packet_path = tmp_path / "packet.json"
        run("download", "#download", str(packet_path))
        packet = json.loads(packet_path.read_text())
        assert packet["result"]["screen_status"] == "failed"
        assert packet["result"]["issue_count"] == 2
        assert packet["result"]["numeric_totals"]["actual"]["total"] == "1200.15"
        assert packet["review_state"] == "unreviewed"
        assert "Finance" not in packet_path.read_text()
        source_path = tmp_path / "input.csv"
        source_path.write_text("department,actual\nFinance,1250.25\nOperations,-50.10\nFinance,invalid\n")
        replay = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "server/csv_review.py"),
                                 "--verify-packet", str(packet_path), "--csv", str(source_path)],
                                capture_output=True, text=True, timeout=5)
        assert replay.returncode == 0 and json.loads(replay.stdout)["status"] == "reproduced"
        run("fill", "#csv", "department,actual\nFinance,0.10\nOperations,0.20\n")
        check("document.getElementById('download').disabled && !document.querySelector('#results code')")
        submit()
        check("document.querySelector('#results code').textContent === '0.30' && document.getElementById('results').textContent.includes('Supported checks passed')")
        # Hostile column labels must be text, never HTML.
        run("fill", "#columns .name", "<img src=x onerror=alert(1)>")
        submit()
        check("!document.querySelector('#results img') && document.getElementById('results').textContent.includes('<img src=x onerror=alert(1)>')")
        run("click", "#sample")
        run("fill", "#csv", 'department,actual\nFinance,"unterminated')
        run("click", "#check")
        run("wait", "--fn", "document.getElementById('message').textContent.includes('CSV structure is invalid')")
        check("document.getElementById('download').disabled && document.getElementById('message').textContent.includes('Re-export the CSV')")
        upload = tmp_path / "uploaded.csv"
        upload.write_bytes(b"department,actual\r\nFinance,4.10\r\nOperations,-0.30\r\n")
        run("upload", "#file", str(upload))
        run("wait", "--fn", "document.getElementById('message').textContent.includes('CSV loaded locally')")
        submit()
        check("document.querySelector('#results code').textContent === '3.80'")
        upload.write_bytes(b"\xff")
        run("eval", "document.getElementById('file').value=''")
        run("upload", "#file", str(upload))
        run("wait", "--fn", "document.getElementById('message').textContent.includes('not valid UTF-8')")
        check("document.getElementById('download').disabled")
        run("eval", "window.originalFetch=window.fetch; window.fetch=()=>Promise.reject(new TypeError('network down'))")
        run("click", "#sample")
        run("click", "#check")
        run("wait", "--fn", "document.getElementById('message').textContent.includes('Service unavailable')")
        check("document.getElementById('csv').value.includes('Finance') && document.getElementById('download').disabled")
        run("eval", "window.fetch=window.originalFetch")
        # A late response must not restore earlier evidence after an edit/cancel.
        run("eval", "window.originalFetch=window.fetch; window.fetch=()=>new Promise(resolve=>{window.lateReply=resolve})")
        run("click", "#sample")
        run("click", "#check")
        run("wait", "--fn", "!!window.lateReply")
        run("click", "#cancel")
        run("eval", "window.lateReply({ok:true,json:async()=>({result:{screen_status:'passed'}})}); window.fetch=window.originalFetch")
        check("document.getElementById('download').disabled && document.getElementById('message').textContent.includes('Stopped waiting')")
        run("click", "#sample")
        submit()
        for mode in ("light", "dark"):
            run("set", "media", mode)
            for width in (1440, 390):
                run("set", "viewport", str(width), "1000")
                check("document.documentElement.scrollWidth <= innerWidth")
                check("[...document.querySelectorAll('button')].filter(b=>!b.hidden).every(b=>b.getBoundingClientRect().height>=40)")
                run("screenshot", str(tmp_path / f"csv-{mode}-{width}.png"), "--full")
        run("click", "#clear")
        check("document.getElementById('csv').value === '' && document.getElementById('download').disabled")
        run("reload")
        check("document.getElementById('csv').value === '' && document.getElementById('columns').children.length===1")
        assert not run("errors").strip()
    finally:
        run("close")

"""Real loopback HTTP boundary and evidence tests; no Workiva calls or mocks."""
import copy
import hashlib
from http.client import HTTPConnection
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from csv_review import review, verify_packet
from csv_checks import ServiceError

ROOT = Path(__file__).resolve().parents[1]
INPUT = {"csv_text": "id,amount\n001,100.01\n1,-0.02\n001,bad\n",
         "columns": [{"name": "id", "type": "string", "required": True},
                     {"name": "amount", "type": "decimal", "required": True}],
         "key_columns": ["id"]}


@pytest.fixture(scope="module")
def csv_url(tmp_path_factory):
    folder = tmp_path_factory.mktemp("csv-service")
    with (folder / "output.log").open("w+") as log:
        process = subprocess.Popen([sys.executable, str(ROOT / "server/csv_review.py"), "--port", "0"],
                                   cwd=folder, stdout=log, stderr=log)
        try:
            for _ in range(100):
                log.seek(0)
                text = log.read()
                if "ready on port " in text:
                    yield "http://127.0.0.1:" + text.split("ready on port ")[1].split(";")[0]
                    return
                assert process.poll() is None, text
                time.sleep(.05)
            pytest.fail("CSV service did not start")
        finally:
            process.terminate()
            process.wait(timeout=5)
        # The service must not create logs, databases or uploaded files itself.
        assert sorted(p.name for p in folder.iterdir()) == ["output.log"]


def request(url, path="/api/review", *, body=None, method="POST", headers=None):
    connection = HTTPConnection("127.0.0.1", int(url.rsplit(":", 1)[1]), timeout=5)
    try:
        connection.request(method, path, body=json.dumps(INPUT if body is None else body),
                           headers={"Origin": url, "Content-Type": "application/json", "X-Wingman-Review": "1", **(headers or {})})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_packet_preserves_exact_evidence_and_unknowns_without_raw_records():
    packet = review(INPUT)
    result = packet["result"]
    assert result["row_count"] == 3
    assert result["issue_count"] == 2
    assert [(i["code"], i["row"]) for i in result["issues"]] == [("invalid_value_type", 4), ("duplicate_key", 4)]
    assert result["numeric_totals"]["amount"]["total"] == "99.99"
    assert result["numeric_totals"]["amount"]["complete"] is False
    assert packet["csv_sha256"] == hashlib.sha256(INPUT["csv_text"].encode()).hexdigest()
    assert packet["review_state"] == "unreviewed"
    assert packet["workiva_requests"] == 0
    assert packet["period_and_units_verified"] is False
    assert result["native_schema_verified"] is False
    assert result["native_import_verified"] is False
    assert result["accounting_correctness_verified"] is False
    # A numeric substring can occur in an unrelated UTC timestamp or hash.
    private = review({**INPUT, "csv_text": INPUT["csv_text"].replace("001", "private-key-do-not-export")})
    assert "private-key-do-not-export" not in json.dumps(private)
    assert "csv_text" not in packet


def test_fingerprints_change_for_different_csv_schema_and_key_policy():
    original = review(INPUT)
    changed = review({**INPUT, "csv_text": INPUT["csv_text"].replace("100.01", "100.02")})
    assert original["csv_sha256"] != changed["csv_sha256"]
    assert original["schema_sha256"] == changed["schema_sha256"]
    changed = review({**INPUT, "key_columns": []})
    assert original["schema_sha256"] != changed["schema_sha256"]
    assert changed["result"]["issue_count"] == 1


def test_http_uses_real_validator_and_does_not_cache(csv_url):
    status, headers, raw = request(csv_url)
    assert status == 200
    assert json.loads(raw)["result"]["numeric_totals"]["amount"]["total"] == "99.99"
    assert headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "Access-Control-Allow-Origin" not in headers


@pytest.mark.parametrize("headers", [{"Origin": "https://attacker.invalid"}, {"Host": "attacker.invalid"},
                                     {"Origin": "null"}, {"X-Wingman-Review": ""},
                                     {"Content-Type": "text/plain"}, {"Transfer-Encoding": "chunked"}])
def test_cross_origin_and_rebinding_denied_before_validation(csv_url, headers):
    assert request(csv_url, body={"csv_text": "sensitive"}, headers=headers)[0] == 403


def test_invalid_contract_size_and_path_do_not_return_partial_pass(csv_url):
    assert request(csv_url, body={**INPUT, "approved": True})[0] == 400
    assert request(csv_url, headers={"Content-Length": "2000001"})[0] == 413
    assert request(csv_url, path="/api/apply")[0] == 404
    assert request(csv_url, path="/../README.md", method="GET")[0] == 404
    status, _, raw = request(csv_url, body={**INPUT, "csv_text": "id,amount\na,\"unterminated"})
    assert status == 400 and json.loads(raw)["code"] == "invalid_csv"


@pytest.mark.parametrize("value", [None, [], "csv", {**INPUT, "server_path": "/etc/passwd"}])
def test_review_has_no_file_path_or_approval_authority(value):
    with pytest.raises(ServiceError):
        review(value)


def test_static_identity_and_scripts_are_served_with_correct_types(csv_url):
    for path, mime in [("/", "text/html"), ("/setup.css", "text/css"), ("/csv-review.js", "text/javascript"), ("/icon.png", "image/png")]:
        status, headers, body = request(csv_url, path=path, method="GET")
        assert status == 200 and headers["Content-Type"].startswith(mime)
        assert body


def test_replay_recomputes_findings_and_does_not_claim_approval_or_timestamp_proof():
    packet = review(INPUT)
    packet["generated_at"] = "2001-01-01T00:00:00+00:00"
    result = verify_packet(packet, INPUT["csv_text"])
    assert result == {"status": "reproduced", "mismatched_fields": [], "approval_verified": False,
                      "native_acceptance_verified": False, "authorship_and_timestamp_verified": False}
    changed = INPUT["csv_text"].replace("100.01", "100.02")
    assert verify_packet(packet, changed)["mismatched_fields"] == ["csv_sha256", "result"]


@pytest.mark.parametrize("field,value", [("review_state", "approved"), ("workiva_requests", False),
                                        ("validator_sha256", "different-build"), ("schema_origin", "native"),
                                        ("packet_version", 2), ("period_and_units_verified", True)])
def test_replay_detects_altered_trust_claims(field, value):
    packet = review(INPUT)
    packet[field] = value
    assert field in verify_packet(packet, INPUT["csv_text"])["mismatched_fields"]


def test_replay_rejects_edited_total_missing_finding_and_changed_schema():
    original = review(INPUT)
    packet = copy.deepcopy(original)
    packet["result"]["numeric_totals"]["amount"]["total"] = "0"
    assert verify_packet(packet, INPUT["csv_text"])["mismatched_fields"] == ["result"]
    packet = copy.deepcopy(original)
    packet["result"]["issues"].pop()
    assert verify_packet(packet, INPUT["csv_text"])["mismatched_fields"] == ["result"]
    packet = copy.deepcopy(original)
    packet["declared_schema"]["key_columns"] = []
    assert verify_packet(packet, INPUT["csv_text"])["mismatched_fields"] == ["result", "schema_sha256"]


def test_replay_cli_returns_machine_status_without_sensitive_values(tmp_path):
    packet = tmp_path / "packet.json"
    source = tmp_path / "input.csv"
    packet.write_text(json.dumps(review(INPUT)))
    source.write_text(INPUT["csv_text"])
    command = [sys.executable, str(ROOT / "server/csv_review.py"), "--verify-packet", str(packet), "--csv", str(source)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0 and json.loads(result.stdout)["status"] == "reproduced"
    assert "99.99" not in result.stdout and "001" not in result.stdout
    source.write_text(INPUT["csv_text"].replace("100.01", "100.02"))
    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    assert result.returncode == 1 and json.loads(result.stdout)["status"] == "mismatch"
    packet.write_text("not-json")
    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    assert result.returncode == 2 and json.loads(result.stdout)["status"] == "invalid_input"


def test_http_replay_reuses_offline_contract_without_import_storage_or_authority(csv_url):
    packet = review(INPUT)
    arguments = {"packet": packet, "csv_text": INPUT["csv_text"]}
    status, headers, raw = request(csv_url, path="/api/replay", body=arguments)
    assert status == 200 and headers["Cache-Control"] == "no-store"
    assert json.loads(raw) == verify_packet(packet, INPUT["csv_text"])
    assert "99.99" not in raw.decode() and "bad" not in raw.decode()
    changed = {**arguments, "csv_text": INPUT["csv_text"].replace("100.01", "100.03")}
    assert json.loads(request(csv_url, path="/api/replay", body=changed)[2])["mismatched_fields"] == ["csv_sha256", "result"]
    approved = copy.deepcopy(packet); approved["review_state"] = "approved"
    assert "review_state" in json.loads(request(csv_url, path="/api/replay", body={**arguments, "packet": approved})[2])["mismatched_fields"]
    for extra in ({"review_scope": {}}, {"native_schema_sha256": "anything"}, {"confirmed": True}):
        assert request(csv_url, path="/api/replay", body={**arguments, **extra})[0] == 400
    assert request(csv_url, path="/api/replay", body=arguments, headers={"Origin": "https://foreign.invalid"})[0] == 403
    assert request(csv_url, path="/api/replay", body={**arguments, "packet": {}})[0] == 400


def test_default_capabilities_are_explicit_not_access_or_mutation_authority(csv_url):
    status, headers, raw = request(csv_url, path="/api/review-config", method="GET")
    assert status == 200 and headers["Cache-Control"] == "no-store"
    assert json.loads(raw) == {"durable_review_enabled": False, "native_schema_configured": False,
                               "native_access_verified": False, "native_mutation_enabled": False}

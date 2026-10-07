#!/usr/bin/env python3
"""Opt-in real local HTTP → authorized native schema → offline packet acceptance.

The server owns exact LSL sandbox scope. This script never authenticates to Workiva
or writes there. All CSV values are fictional. Run with --port 8782 --out <folder>.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

CSV = "record_id,amount_cents,period,currency,_tags,_filename,_timestamp,_userid\n001,1001,2026-10,USD,,,,\n1,-2,2026-10,USD,,,,\n"
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    url = "http://127.0.0.1:" + str(args.port)
    def post(path, data, expected=200):
        request = urllib.request.Request(url + path, data=json.dumps(data).encode(),
                                         headers={"Origin": url, "Content-Type": "application/json", "X-Wingman-Review": "1"})
        try:
            response = urllib.request.urlopen(request, timeout=25)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            assert response.status == expected, f"Unexpected local HTTP status {response.status}"
            return json.load(response)
    schema = post("/api/schema", {})
    assert [x["name"] for x in schema["columns"]] == CSV.splitlines()[0].split(",")
    review = {"csv_text": CSV, "columns": schema["columns"], "key_columns": ["record_id"],
              "native_schema_sha256": schema["snapshot"]["schema_sha256"]}
    packet = post("/api/review", review)
    assert packet["native_schema_observed"] is True
    assert packet["native_schema"]["binding"] == schema["snapshot"]["binding"]
    assert packet["result"]["screen_status"] == "passed"
    assert packet["result"]["numeric_totals"]["amount_cents"]["total"] == "999"
    assert packet["result"]["numeric_totals"]["amount_cents"]["complete"] is True
    assert packet["result"]["native_import_verified"] is False and packet["period_and_units_verified"] is False
    assert post("/api/review", {**review, "native_schema_sha256": "0" * 64}, 400)["code"] == "native_schema_changed"
    assert post("/api/schema", {"table_id": "f" * 32}, 400)["code"] == "native_not_configured"
    failed = post("/api/review", {**review, "csv_text": CSV + "001,invalid,2026-10,USD,,,,\n"})
    assert {(x["code"], x.get("row")) for x in failed["result"]["issues"]} == {("duplicate_key", 4), ("invalid_value_type", 4)}
    source, saved = args.out / "synthetic.csv", args.out / "packet.json"
    source.write_text(CSV); saved.write_text(json.dumps(packet, indent=2))
    replay = subprocess.run([sys.executable, str(ROOT / "server/csv_review.py"), "--verify-packet", str(saved), "--csv", str(source)], capture_output=True, text=True, timeout=5)
    assert replay.returncode == 0 and json.loads(replay.stdout)["status"] == "reproduced"
    policy = {"period_column": "period", "expected_period": "2026-10", "currency_column": "currency",
              "expected_currency": "USD", "unit_column": "", "expected_unit": "cents",
              "amount_columns": ["amount_cents"], "accounting_basis": "modified_accrual"}
    context_packet = post("/api/review", {**review, "reporting_policy": policy})
    assert context_packet["native_schema_observed"] is True and context_packet["packet_version"] == 3
    assert context_packet["reporting_context"]["status"] == "incomplete"
    assert context_packet["reporting_context"]["issue_count"] == 0  # Matching labels, no row-unit column.
    assert context_packet["period_and_units_verified"] is False
    mismatch = post("/api/review", {**review, "reporting_policy": policy,
                                    "csv_text": CSV.replace("1,-2,2026-10,USD", "1,-2,2026-09,EUR")})
    assert mismatch["reporting_context"]["status"] == "failed"
    assert {(x["code"], x["row"]) for x in mismatch["reporting_context"]["issues"]} == {("period_mismatch", 3), ("currency_mismatch", 3)}
    context_path = args.out / "context-packet.json"
    context_path.write_text(json.dumps(context_packet, indent=2))
    replay = subprocess.run([sys.executable, str(ROOT / "server/csv_review.py"), "--verify-packet", str(context_path), "--csv", str(source)], capture_output=True, text=True, timeout=5)
    assert replay.returncode == 0 and json.loads(replay.stdout)["status"] == "reproduced"
    receipt = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "passed",
               "scope": "exact private synthetic LSL table, schema reads only",
               "schema_sha256": schema["snapshot"]["schema_sha256"],
               "native_binding": schema["snapshot"]["binding"],
               "checks": ["native schema identity/version/columns", "exact integer total", "stale fingerprint rejection",
                          "extra resource authority refusal", "row/type/key findings", "offline packet reproduction",
                          "native-bound period/currency mismatch", "undeclared row units incomplete", "context packet replay"],
               "native_import_verified": False, "accounting_correctness_verified": False,
               "request_count_verified": False}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps({"status": "passed", "receipt": str(args.out / "receipt.json"), "schema_sha256": receipt["schema_sha256"]}))


if __name__ == "__main__":
    main()

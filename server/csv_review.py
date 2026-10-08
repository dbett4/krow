#!/usr/bin/env python3
"""Private loopback CSV review, reusing the Lockfield Workiva Plugin validator.

Default mode has no outbound requests. Optional exact synthetic-table schema reads
use wk's existing grant, never credentials in this process or Workiva writes.
This is not the extension backend and must not replace the deployed service.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3

from csv_checks import MAX_CSV_BYTES, ServiceError, validate_csv_draft

ROOT = Path(__file__).resolve().parents[1]
MAX_BODY = 2_000_000  # JSON escaping can expand a bounded CSV by up to six times.
STATIC = {
    "/": ("extension/csv-review.html", "text/html; charset=utf-8"),
    "/csv-review.js": ("extension/csv-review.js", "text/javascript; charset=utf-8"),
    "/csv-review.css": ("extension/csv-review.css", "text/css; charset=utf-8"),
    "/setup.css": ("extension/setup.css", "text/css; charset=utf-8"),
    "/icon.png": ("extension/icons/icon128.png", "image/png"),
}


def review(arguments):
    if (not isinstance(arguments, dict)
            or set(arguments) not in ({"csv_text", "columns", "key_columns"},
                                     {"csv_text", "columns", "key_columns", "reporting_policy"})):
        raise ServiceError("invalid_arguments", "Supply CSV text, explicit columns and keys, with optional reporting policy only.")
    result = validate_csv_draft(**{key: arguments[key] for key in ("csv_text", "columns", "key_columns")}, max_issues=100)
    canonical_schema = json.dumps({"columns": arguments["columns"], "key_columns": arguments["key_columns"]},
                                  sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    packet = {
        "product": "Wingman", "packet_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validator": "lockfield-csv-v0.4.0",
        "validator_sha256": hashlib.sha256((ROOT / "server/csv_checks.py").read_bytes()).hexdigest(),
        "csv_sha256": hashlib.sha256(arguments["csv_text"].encode("utf-8")).hexdigest(),
        "schema_sha256": hashlib.sha256(canonical_schema.encode()).hexdigest(),
        "declared_schema": {"columns": arguments["columns"], "key_columns": arguments["key_columns"]},
        "schema_origin": "caller_supplied_not_native_verified",
        "period_and_units_verified": False, "workiva_requests": 0,
        "review_state": "unreviewed", "result": result,
    }
    if "reporting_policy" in arguments:
        from csv_context import check_context
        policy = arguments["reporting_policy"]
        packet.update({"packet_version": 3, "reporting_policy": policy,
                       "context_validator_sha256": hashlib.sha256((ROOT / "server/csv_context.py").read_bytes()).hexdigest(),
                       "reporting_context": check_context(arguments["csv_text"], arguments["columns"], policy)})
    return packet


def verify_packet(packet, csv_text):
    """Recompute observations, not authorship, approval or timestamp authenticity."""
    if not isinstance(packet, dict) or not isinstance(packet.get("declared_schema"), dict):
        raise ServiceError("invalid_packet", "Packet must include its explicit declared schema.")
    schema = packet["declared_schema"]
    if set(schema) != {"columns", "key_columns"}:
        raise ServiceError("invalid_packet", "Packet schema must include columns and key columns only.")
    generated = packet.get("generated_at")
    try:
        if not isinstance(generated, str) or datetime.fromisoformat(generated).utcoffset() is None:
            raise ValueError("Missing timestamp timezone")
    except ValueError:
        raise ServiceError("invalid_packet", "Packet needs an ISO timestamp with timezone.")
    expected = review({"csv_text": csv_text, **schema,
                       **({"reporting_policy": packet["reporting_policy"]} if "reporting_policy" in packet else {})})
    if packet.get("packet_version") in (2, 3) and "native_schema" in packet:
        from csv_native import bind_packet
        expected = bind_packet(expected, packet.get("native_schema"))
    # Strict JSON comparisons distinguish booleans from numeric zero/one.
    fields = (set(packet) | set(expected)) - {"generated_at"}
    mismatches = sorted(field for field in fields if field not in packet or field not in expected
                        or json.dumps(packet[field], sort_keys=True) != json.dumps(expected[field], sort_keys=True))
    return {"status": "mismatch" if mismatches else "reproduced", "mismatched_fields": mismatches,
            "approval_verified": False, "native_acceptance_verified": False,
            "authorship_and_timestamp_verified": False}


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *args):
        pass  # No request paths, payloads or financial values in logs.

    def reply(self, status, data, content_type="application/json"):
        body = json.dumps(data).encode() if content_type == "application/json" else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def local_request(self):
        authority = "127.0.0.1:" + str(self.server.server_port)
        # Exact authority rejects DNS rebinding; no proxy/forwarded-host trust.
        if self.headers.get("Host") != authority:
            self.reply(403, {"error": "Open this service through its exact loopback address."})
            return False
        if self.command == "POST" and (
            self.headers.get("Origin") != "http://" + authority
            or self.headers.get("Content-Type") != "application/json"
            or self.headers.get("X-Wingman-Review") != "1"
            or self.headers.get("Transfer-Encoding") is not None
        ):
            self.reply(403, {"error": "Only same-origin Wingman review requests are accepted."})
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        if self.path == "/api/review-config":
            self.reply(200, {"durable_review_enabled": getattr(self.server, "decision_store", None) is not None,
                             "native_schema_configured": getattr(self.server, "native_schema", None) is not None,
                             "native_access_verified": False, "native_mutation_enabled": False})
            return
        if self.path not in STATIC:
            self.reply(404, {"error": "Not found."})
            return
        path, content_type = STATIC[self.path]
        self.reply(200, (ROOT / path).read_bytes(), content_type)

    def do_POST(self):
        if not self.local_request():
            return
        if self.path not in {"/api/review", "/api/schema", "/api/replay", "/api/review-history", "/api/review-decisions"}:
            self.reply(404, {"error": "Not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                self.reply(413, {"error": "Request exceeds the bounded review size."})
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete request")
            arguments = json.loads(raw.decode("utf-8"))
            store = getattr(self.server, "decision_store", None)
            scope = None
            if self.path == "/api/replay":
                if not isinstance(arguments, dict) or set(arguments) != {"packet", "csv_text"}:
                    raise ServiceError("invalid_replay", "Supply the imported evidence packet and original CSV only; replay has no storage or native authority.")
                self.reply(200, verify_packet(arguments["packet"], arguments["csv_text"]))
                return
            if self.path in {"/api/review-history", "/api/review-decisions"}:
                if store is None:
                    raise ServiceError("review_not_configured", "Durable review is not configured. Default mode saves no review data.")
                if self.path == "/api/review-history":
                    if not isinstance(arguments, dict) or set(arguments) != {"scope"}:
                        raise ServiceError("invalid_review_scope", "Supply the exact declared review scope only.")
                    packet = store.read(arguments["scope"])
                else:
                    packet = store.decide(arguments)
                self.reply(200, packet)
                return
            if self.path == "/api/review" and isinstance(arguments, dict) and "review_scope" in arguments:
                if store is None:
                    raise ServiceError("review_not_configured", "Durable review is not configured. Check without saving, or ask the operator to configure a private review database.")
                from review_decisions import scope_key
                arguments = dict(arguments)
                scope = arguments.pop("review_scope")
                scope_key(scope)
            if self.path == "/api/schema":
                if arguments != {} or self.server.native_schema is None:
                    raise ServiceError("native_not_configured", "No native sandbox binding is configured. Use your declared schema or start with --sandbox-table and the approved LSL read grant.")
                from csv_native import project
                snapshot = self.server.native_schema.read()
                packet = {"snapshot": snapshot, "columns": project(snapshot)}
            elif isinstance(arguments, dict) and "native_schema_sha256" in arguments:
                if self.server.native_schema is None:
                    raise ServiceError("native_not_configured", "No native sandbox binding is configured.")
                from csv_native import bind_packet
                arguments = dict(arguments)
                expected_hash = arguments.pop("native_schema_sha256")
                packet = review(arguments)  # Reject extra authority before any live read.
                snapshot = self.server.native_schema.read()
                if expected_hash != snapshot["schema_sha256"]:
                    raise ServiceError("native_schema_changed", "The native schema/version changed. Reload it and run a new check; earlier evidence is not current.")
                packet = bind_packet(packet, snapshot)
            else:
                packet = review(arguments)
            if scope is not None:
                packet = {"packet": packet, "saved_review": store.observe(scope, packet, arguments["csv_text"])}
        except ServiceError as error:
            self.reply(400, {"error": str(error), "code": error.code})
            return
        except (ValueError, UnicodeError, TimeoutError):
            self.reply(400, {"error": "Supply valid UTF-8 JSON with a complete request body."})
            return
        except sqlite3.Error:
            self.reply(503, {"code": "review_store_unavailable", "error": "Private review storage is unavailable or busy. No success is claimed. Reload saved review to reconcile an uncertain response; do not blindly repeat confirmation."})
            return
        self.reply(200, packet)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8781)
    parser.add_argument("--sandbox-table", help="One exact private synthetic Wdata table in the authorized LSL account. Read-only via wk.")
    parser.add_argument("--review-db", type=Path, help="Opt-in private SQLite decision journal in an existing owner-only directory. No raw CSV retained.")
    parser.add_argument("--verify-packet", type=Path, help="Recompute a downloaded JSON packet; does not start a service.")
    parser.add_argument("--csv", type=Path, help="Original UTF-8 CSV for packet replay; explicit local file read.")
    args = parser.parse_args()
    if args.verify_packet and (args.sandbox_table or args.review_db):
        parser.error("Offline replay does not use a live sandbox binding or decision database")
    if bool(args.verify_packet) != bool(args.csv):
        parser.error("--verify-packet and --csv must be supplied together")
    if args.verify_packet:
        try:
            with args.verify_packet.open("rb") as file:
                raw_packet = file.read(MAX_BODY + 1)
            with args.csv.open("rb") as file:
                raw_csv = file.read(MAX_CSV_BYTES + 1)
            if len(raw_packet) > MAX_BODY or len(raw_csv) > MAX_CSV_BYTES:
                raise ValueError("Replay input too large")
            result = verify_packet(json.loads(raw_packet.decode("utf-8")), raw_csv.decode("utf-8"))
        except (OSError, ValueError, UnicodeError):
            print(json.dumps({"status": "invalid_input", "error": "Supply a supported Wingman packet and bounded original UTF-8 CSV."}))
            return 2
        print(json.dumps(result))
        return 0 if result["status"] == "reproduced" else 1
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    from csv_native import NativeSchema
    server.native_schema = NativeSchema(args.sandbox_table) if args.sandbox_table else None
    if args.review_db:
        from review_decisions import DecisionStore
        try:
            server.decision_store = DecisionStore(args.review_db)
        except (OSError, ValueError, sqlite3.Error):
            server.server_close()
            parser.error("Review database unavailable. Use an existing private owner-only directory and a regular owner-only database, or omit --review-db. No recovery overwrite is performed.")
    else:
        server.decision_store = None
    print(f"Wingman CSV review ready on port {server.server_port}; loopback only, no stored inputs.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())

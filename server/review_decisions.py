"""Opt-in private CSV review journal. Acceptance is never remediation or approval."""
import csv
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid

from csv_checks import ServiceError


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def scope_key(scope):
    if (not isinstance(scope, dict) or set(scope) != {"workspace", "file_copy", "period"}
            or any(not isinstance(value, str) or not value.strip() or len(value) > 128 for value in scope.values())):
        raise ServiceError("invalid_review_scope", "Declare separate workspace, file-copy and reporting-period labels (1–128 characters). These are not authenticated Workiva identities.")
    return digest(scope)


def observations(packet, csv_text):
    rows = list(csv.reader(io.StringIO(csv_text.removeprefix("\ufeff"), newline=""), strict=True))
    header = rows[0]
    policy = {"schema": packet["schema_sha256"], "keys": packet["declared_schema"]["key_columns"],
              "reporting": packet.get("reporting_policy"), "validator": packet["validator_sha256"],
              "context_validator": packet.get("context_validator_sha256"),
              "native": packet.get("native_schema", {}).get("binding")}
    found = []
    for origin, issues in [("csv", packet["result"]["issues"]),
                           ("context", packet.get("reporting_context", {}).get("issues", []))]:
        for issue in issues:
            identity = {"origin": origin, "code": issue["code"], "row": issue.get("row"), "column": issue.get("column")}
            row_number, name = issue.get("row"), issue.get("column")
            row = rows[row_number - 1] if row_number and row_number <= len(rows) else header
            evidence = row
            if row_number and row_number > 1 and name and header.count(name) == 1 and len(row) == len(header):
                evidence = row[header.index(name)]
            if issue["code"] == "duplicate_key":
                keys = policy["keys"]
                evidence = [(index + 1, [row[header.index(key)] for key in keys])
                            for index, row in enumerate(rows[1:], start=1)
                            if len(row) == len(header) and all(header.count(key) == 1 for key in keys)
                            and [row[header.index(key)] for key in keys] == [rows[row_number - 1][header.index(key)] for key in keys]]
            # Physical line-end movement is not changed evidence for the same record.
            details = {key: value for key, value in issue.items() if key != "csv_line_end"}
            found.append({"id": digest(identity), "location": identity,
                          "evidence_sha256": digest({"policy": policy, "finding": details, "observed": evidence})})
    return found


class DecisionStore:
    def __init__(self, path):
        self.path = Path(path)
        parent = self.path.parent.stat()
        if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) & 0o077:
            raise ValueError("Review database needs an existing owner-only directory (mode 700).")
        if self.path.exists() or self.path.is_symlink():
            info = self.path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError("Existing review database must be an owner-only regular file (mode 600).")
        else:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        with self.connect() as db:
            if self.path.stat().st_size:
                tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if tables != {"scopes", "runs", "findings", "events"}:
                    raise ValueError("Not a Wingman review journal; unrelated databases are never adopted.")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS scopes (id TEXT PRIMARY KEY, labels TEXT NOT NULL, latest_run TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, scope TEXT NOT NULL, observed_at TEXT NOT NULL, complete INTEGER NOT NULL, source_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS findings (scope TEXT NOT NULL, id TEXT NOT NULL, evidence TEXT NOT NULL, location TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL, seen_run TEXT NOT NULL, PRIMARY KEY(scope,id));
                CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY, scope TEXT NOT NULL, finding TEXT NOT NULL, evidence TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT NOT NULL, reviewer TEXT NOT NULL, at TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=3)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def observe(self, scope, packet, csv_text):
        key, run = scope_key(scope), uuid.uuid4().hex
        found = observations(packet, csv_text)
        result = packet["result"]
        complete = (result["header_matches_schema_order"] and result["schema_types_supported"]
                    and not result["issues_truncated"] and not packet.get("reporting_context", {}).get("issues_truncated", False)
                    and not packet.get("reporting_context", {}).get("unknowns")
                    and not any(item["code"] in {"row_width_mismatch", "no_data_rows"} for item in result["issues"]))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO scopes VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET latest_run=excluded.latest_run", (key, json.dumps(scope), run))
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?)", (run, key, packet["generated_at"], complete, packet["csv_sha256"]))
            for item in found:
                old = db.execute("SELECT * FROM findings WHERE scope=? AND id=?", (key, item["id"])).fetchone()
                state = "accepted_exception" if old and old["state"] == "accepted_exception" and old["evidence"] == item["evidence_sha256"] else "open"
                db.execute("INSERT OR REPLACE INTO findings VALUES(?,?,?,?,?,?,?)", (key, item["id"], item["evidence_sha256"], json.dumps(item["location"]), state, old["revision"] + 1 if old else 1, run))
            if complete:
                db.execute("UPDATE findings SET state='resolved_by_complete_check', revision=revision+1 WHERE scope=? AND seen_run<>?", (key, run))
            snapshot = self.read(scope, db)
        return snapshot

    def read(self, scope, db=None):
        key = scope_key(scope)
        if db is None:
            with self.connect() as connection:
                connection.execute("BEGIN")
                return self.read(scope, connection)
        latest = db.execute("SELECT runs.* FROM runs JOIN scopes ON runs.id=scopes.latest_run WHERE scopes.id=?", (key,)).fetchone()
        if not latest:
            return {"scope": scope, "run_id": None, "findings": [], "history": [], "complete": False}
        found = []
        for row in db.execute("SELECT * FROM findings WHERE scope=? ORDER BY id", (key,)):
            current = row["seen_run"] == latest["id"]
            found.append({"id": row["id"], "location": json.loads(row["location"]), "evidence_sha256": row["evidence"],
                          "state": row["state"] if current or latest["complete"] else "not_revisited",
                          "retained_decision": row["state"], "revision": row["revision"], "current": current})
        history = [dict(row) for row in db.execute("SELECT sequence,finding,evidence,decision,reason,reviewer,at FROM events WHERE scope=? ORDER BY sequence DESC LIMIT 200", (key,))]
        history_count = db.execute("SELECT COUNT(*) FROM events WHERE scope=?", (key,)).fetchone()[0]
        return {"scope": scope, "run_id": latest["id"], "observed_at": latest["observed_at"], "complete": bool(latest["complete"]),
                "source_sha256": latest["source_hash"], "findings": found, "history": history, "history_count": history_count,
                "history_truncated": history_count > len(history),
                "approval_verified": False, "reviewer_identity_verified": False,
                "limits": "Local declared scope/identity; accepted exceptions remain findings, not accounting approval or permission to write. Record-ordinal identities reopen on row movement. Unvisited/truncated findings are never resolved."}

    def decide(self, arguments):
        if not isinstance(arguments, dict) or set(arguments) != {"scope", "run_id", "finding_id", "revision", "evidence_sha256", "decision", "reason", "reviewer", "confirmed"}:
            raise ServiceError("invalid_decision", "Supply the exact current finding, reason, reviewer label and explicit confirmation.")
        key = scope_key(arguments["scope"])
        if (arguments["confirmed"] is not True or arguments["decision"] not in ("accepted_exception", "open")
                or type(arguments["revision"]) is not int
                or any(not isinstance(arguments[field], str) or not arguments[field].strip() or len(arguments[field]) > limit
                       for field, limit in [("reason", 1000), ("reviewer", 100), ("run_id", 64), ("finding_id", 64), ("evidence_sha256", 64)])):
            raise ServiceError("invalid_decision", "Confirm a reason (1–1000 characters) and reviewer label. Only accept exception or reopen is supported; no approval or repair.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            latest = db.execute("SELECT scopes.latest_run,runs.observed_at FROM scopes JOIN runs ON runs.id=scopes.latest_run WHERE scopes.id=?", (key,)).fetchone()
            row = db.execute("SELECT * FROM findings WHERE scope=? AND id=?", (key, arguments["finding_id"])).fetchone()
            if (not latest or latest[0] != arguments["run_id"] or not row or row["seen_run"] != arguments["run_id"]
                    or row["revision"] != arguments["revision"] or row["evidence"] != arguments["evidence_sha256"]
                    or (datetime.now(timezone.utc) - datetime.fromisoformat(latest["observed_at"])).total_seconds() > 600):
                raise ServiceError("stale_decision", "The review or decision changed. Reload saved review or recheck current inputs; nothing was accepted.")
            db.execute("UPDATE findings SET state=?,revision=revision+1 WHERE scope=? AND id=?", (arguments["decision"], key, row["id"]))
            db.execute("INSERT INTO events(scope,finding,evidence,decision,reason,reviewer,at) VALUES(?,?,?,?,?,?,?)", (key, row["id"], row["evidence"], arguments["decision"], arguments["reason"], arguments["reviewer"], datetime.now(timezone.utc).isoformat()))
            readback = db.execute("SELECT state,revision FROM findings WHERE scope=? AND id=?", (key, row["id"])).fetchone()
            if readback[0] != arguments["decision"] or readback[1] != arguments["revision"] + 1:
                raise ServiceError("decision_unverified", "Local readback failed; the decision transaction was reversed.")
            snapshot = self.read(arguments["scope"], db)
        return snapshot

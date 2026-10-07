"""Exact synthetic-table schema reads through the adopted wk credential route.

No credentials, token handling, HTTP implementation, list calls or write path.
Projection follows Lockfield Workiva Plugin adapter.py's validate_csv_draft path;
native nullable/required modes add explicit requiredness without guessing.
"""
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess

from csv_checks import ServiceError, _columns

LSL_ACCOUNT = "QWNjb3VudB8xMTQ4MjM2MTkwMA"


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def run_wk(*arguments):
    try:
        response = subprocess.run(["wk", "-w", "lsl-account", *arguments],
                                  capture_output=True, text=True, timeout=8)
        if response.returncode != 0:
            raise ValueError("Unavailable")
        value = json.loads(response.stdout)
        if not isinstance(value, dict):
            raise ValueError("Invalid response")
        return value
    except (OSError, ValueError, subprocess.TimeoutExpired):
        # Never echo argv, credential source, upstream diagnostics or stderr.
        raise ServiceError("native_unavailable", "Sandbox schema is unavailable. Confirm the wk LSL read grant, then reload the schema.") from None


def project(snapshot):
    """Validate exported snapshot shape too; replay cannot authenticate it."""
    try:
        binding = snapshot["binding"]
        if (binding["account_id"] != LSL_ACCOUNT
                or not re.fullmatch(r"[a-f0-9]{32}", binding["table_id"])
                or not binding["table_name"].startswith("zz Wingman Synthetic ")
                or type(binding["version"]) is not int):
            raise ValueError("Scope")
        raw = binding["table_schema"]["columns"]
        columns = []
        for item in raw:
            column = {"name": item["name"], "type": item["type"]}
            mode = item.get("mode")
            if mode in {"nullable", "required"}:
                column["required"] = mode == "required"
            elif mode:
                # Repeated/nested data cannot be screened as a scalar CSV type.
                column["type"] = "unsupported_mode_" + str(mode)
            columns.append(column)
        if (snapshot["schema_sha256"] != fingerprint(binding)
                or snapshot["evidence"] != "workiva_api_response"):
            raise ValueError("Evidence")
        # Reuse the checker contract rather than a competing schema validator.
        _columns(columns)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ServiceError("native_schema_invalid", "The sandbox schema binding is incomplete or inconsistent. Reload it.") from None
    return columns


class NativeSchema:
    def __init__(self, table_id):
        if not re.fullmatch(r"[a-f0-9]{32}", table_id):
            raise ValueError("Supply one exact synthetic Wdata table ID.")
        self.table_id = table_id

    def read(self):
        identity = run_wk("whoami")
        if identity.get("arid") != LSL_ACCOUNT or identity.get("workspace") != "lsl-account":
            raise ServiceError("native_scope_denied", "This process is not bound to the authorized LSL account.")
        response = run_wk("raw", "GET", "/table/" + self.table_id, "--surface", "wdata")
        body = response.get("body")
        table = body.get("body") if isinstance(body, dict) else None
        if (not isinstance(table, dict) or response.get("status") != 200 or table.get("id") != self.table_id
                or table.get("databaseId") != LSL_ACCOUNT
                or not str(table.get("name", "")).startswith("zz Wingman Synthetic ")
                or table.get("isShared") is not False):
            raise ServiceError("native_scope_denied", "The exact private synthetic table/account binding was not verified.")
        binding = {"account_id": LSL_ACCOUNT, "table_id": self.table_id,
                   "table_name": table["name"], "version": table.get("version"),
                   "updated": table.get("updated"), "table_schema": table.get("tableSchema")}
        snapshot = {"binding": binding, "schema_sha256": fingerprint(binding),
                    "observed_at": datetime.now(timezone.utc).isoformat(), "evidence": "workiva_api_response"}
        project(snapshot)
        return snapshot


def bind_packet(packet, snapshot):
    if packet["declared_schema"]["columns"] != project(snapshot):
        raise ServiceError("native_schema_changed", "Schema no longer matches this review. Reload the native schema and recheck.")
    return {**packet, "packet_version": 2, "schema_origin": "native_table_schema",
            "native_schema": snapshot, "native_schema_observed": True,
            "workiva_requests": None, "workiva_request_count_verified": False}

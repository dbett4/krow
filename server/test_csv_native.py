"""Native binding regression tests; scripted wk answers are not live acceptance."""
import copy
from http.server import ThreadingHTTPServer
import threading

import pytest

import csv_native
from csv_native import LSL_ACCOUNT, NativeSchema, bind_packet, fingerprint, project
from csv_review import Handler, review, verify_packet
from csv_checks import ServiceError
from test_csv_review import request

TABLE = "a" * 32
COLUMNS = [{"name": "id", "type": "string", "mode": "required"},
           {"name": "amount", "type": "integer", "mode": "nullable"}]


def table():
    return {"id": TABLE, "databaseId": LSL_ACCOUNT, "name": "zz Wingman Synthetic Test",
            "isShared": False, "version": 3, "updated": "2026-10-07T00:00:00Z",
            "tableSchema": {"columns": copy.deepcopy(COLUMNS)}}


@pytest.fixture
def native(monkeypatch):
    state = {"table": table(), "identity": {"arid": LSL_ACCOUNT, "workspace": "lsl-account"}, "calls": []}
    def wk(*args):
        state["calls"].append(args)
        return state["identity"] if args == ("whoami",) else {"status": 200, "body": {"body": state["table"]}}
    monkeypatch.setattr(csv_native, "run_wk", wk)
    state["provider"] = NativeSchema(TABLE)
    return state


def test_scope_denial_before_table_http(native):
    native["identity"]["arid"] = "other-account"
    with pytest.raises(ServiceError, match="authorized LSL"):
        native["provider"].read()
    assert native["calls"] == [("whoami",)]
    with pytest.raises(ValueError):
        NativeSchema(TABLE + "/../other")


@pytest.mark.parametrize("key,value", [("id", "b" * 32), ("databaseId", "other"),
                                      ("name", "Client workbook"), ("isShared", True)])
def test_wrong_native_binding_cannot_be_used(native, key, value):
    native["table"][key] = value
    with pytest.raises(ServiceError, match="binding was not verified"):
        native["provider"].read()


def test_native_requiredness_unknown_modes_and_exact_integer_policy(native):
    snapshot = native["provider"].read()
    assert project(snapshot) == [{"name": "id", "type": "string", "required": True},
                                 {"name": "amount", "type": "integer", "required": False}]
    args = {"csv_text": "id,amount\n001,1001\n1,-2\n", "columns": project(snapshot), "key_columns": ["id"]}
    packet = bind_packet(review(args), snapshot)
    assert packet["result"]["numeric_totals"]["amount"]["total"] == "999"
    assert packet["result"]["native_import_verified"] is False
    assert packet["period_and_units_verified"] is False
    assert verify_packet(packet, args["csv_text"])["status"] == "reproduced"
    changed = copy.deepcopy(packet)
    changed["native_schema"]["binding"]["version"] += 1
    with pytest.raises(ServiceError):
        verify_packet(changed, args["csv_text"])
    native["table"]["tableSchema"]["columns"][1]["mode"] = "repeated"
    snapshot = native["provider"].read()
    packet = review({**args, "columns": project(snapshot)})
    assert packet["result"]["screen_status"] == "incomplete"


def test_malformed_schema_and_forged_fingerprint_are_rejected(native):
    snapshot = native["provider"].read()
    snapshot["schema_sha256"] = "0" * 64
    with pytest.raises(ServiceError):
        project(snapshot)
    native["table"]["tableSchema"] = {"columns": []}
    with pytest.raises(ServiceError):
        native["provider"].read()


def test_real_http_rechecks_staleness_and_denies_extra_authority(native):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.native_schema = native["provider"]
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = "http://127.0.0.1:" + str(server.server_port)
    try:
        snapshot = native["provider"].read()
        args = {"csv_text": "id,amount\n001,1001\n1,-2\n", "columns": project(snapshot),
                "key_columns": ["id"], "native_schema_sha256": snapshot["schema_sha256"]}
        import json
        status, _, raw = request(url, body=args)
        assert status == 200 and json.loads(raw)["native_schema_observed"] is True
        native["calls"].clear()
        assert request(url, body={**args, "table_id": "b" * 32})[0] == 400
        assert native["calls"] == []
        assert request(url, path="/api/schema", body={"table_id": "b" * 32})[0] == 400
        assert native["calls"] == []
        native["table"]["version"] += 1
        status, _, raw = request(url, body=args)
        assert status == 400 and json.loads(raw)["code"] == "native_schema_changed"
        snapshot = native["provider"].read()
        status, _, raw = request(url, body={**args, "native_schema_sha256": snapshot["schema_sha256"]})
        assert status == 200 and json.loads(raw)["result"]["numeric_totals"]["amount"]["total"] == "999"
    finally:
        server.shutdown(); server.server_close(); worker.join(timeout=5)

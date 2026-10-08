"""Real SQLite durability, concurrency and incomplete-evidence safeguards."""
import copy
from concurrent.futures import ThreadPoolExecutor
import os
import sqlite3

import pytest

from csv_checks import ServiceError
from csv_review import review
from review_decisions import DecisionStore
from test_csv_review import INPUT

SCOPE = {"workspace": "synthetic", "file_copy": "original", "period": "2026-10"}


def decision(snapshot, code="invalid_value_type"):
    item = next(f for f in snapshot["findings"] if f["location"]["code"] == code and f["current"])
    return {"scope": snapshot["scope"], "run_id": snapshot["run_id"], "finding_id": item["id"],
            "revision": item["revision"], "evidence_sha256": item["evidence_sha256"],
            "decision": "accepted_exception", "reason": "Synthetic calibration exception; source correction remains required.",
            "reviewer": "Test reviewer", "confirmed": True}


def observe(store, source=INPUT, scope=SCOPE):
    return store.observe(scope, review(source), source["csv_text"])


def test_restart_preserves_decisions_but_relevant_change_reopens_only_affected(tmp_path):
    path = tmp_path / "review.db"
    store = DecisionStore(path)
    snapshot = observe(store)
    store.decide(decision(snapshot))
    store.decide(decision(store.read(SCOPE), "duplicate_key"))
    reopened = DecisionStore(path)
    assert {f["state"] for f in reopened.read(SCOPE)["findings"]} == {"accepted_exception"}
    changed = {**INPUT, "csv_text": INPUT["csv_text"].replace("bad", "different-private-sentinel")}
    snapshot = observe(reopened, changed)
    assert {f["location"]["code"]: f["state"] for f in snapshot["findings"]} == {"duplicate_key": "accepted_exception", "invalid_value_type": "open"}
    assert len(snapshot["history"]) == 2
    assert b"different-private-sentinel" not in path.read_bytes()
    assert os.stat(path).st_mode & 0o777 == 0o600


@pytest.mark.parametrize("field", ["workspace", "file_copy", "period"])
def test_declared_scope_boundaries_never_inherit_an_exception(tmp_path, field):
    store = DecisionStore(tmp_path / "review.db")
    store.decide(decision(observe(store)))
    assert all(f["state"] == "open" for f in observe(store, scope={**SCOPE, field: "different"})["findings"])


def test_partial_header_ragged_unknown_and_truncated_checks_do_not_resolve_unvisited(tmp_path):
    for index, arguments in enumerate([
        {**INPUT, "csv_text": "id\nx\n"},
        {**INPUT, "csv_text": "id,amount\nx\n"},
        {**INPUT, "columns": [{"name": "id", "type": "string"}, {"name": "amount", "type": "unknown"}]},
        {**INPUT, "csv_text": "id,amount\n" + "x,invalid\n" * 100},
    ]):
        store = DecisionStore(tmp_path / f"review-{index}.db")
        initial = observe(store)
        request = decision(initial)
        store.decide(request)
        snapshot = observe(store, arguments)
        assert snapshot["complete"] is False
        retained = next(f for f in snapshot["findings"] if f["id"] == request["finding_id"])
        # Same address can be revisited with changed evidence, but never falsely resolved.
        assert retained["state"] in {"not_revisited", "open"}


def test_complete_fix_resolves_but_recurrence_does_not_inherit_old_acceptance(tmp_path):
    store = DecisionStore(tmp_path / "review.db")
    store.decide(decision(observe(store)))
    fixed = {**INPUT, "csv_text": "id,amount\n001,100.01\n1,-0.02\n2,1.00\n"}
    assert all(f["state"] == "resolved_by_complete_check" for f in observe(store, fixed)["findings"])
    assert all(f["state"] == "open" for f in observe(store)["findings"])


def test_unknown_reporting_units_never_resolve_unvisited_context(tmp_path):
    from test_csv_context import INPUT as context_input, POLICY
    store = DecisionStore(tmp_path / "review.db")
    wrong = {**context_input, "csv_text": context_input["csv_text"].replace("cents", "units")}
    store.decide(decision(observe(store, wrong), "unit_mismatch"))
    for source in (context_input["csv_text"], context_input["csv_text"].replace("USD", "EUR")):
        incomplete = {**context_input, "csv_text": source, "reporting_policy": {**POLICY, "unit_column": ""}}
        snapshot = observe(store, incomplete)
        assert not snapshot["complete"]
        assert next(f for f in snapshot["findings"] if f["location"]["code"] == "unit_mismatch")["state"] == "not_revisited"


def test_policy_change_and_expired_confirmation_cannot_inherit(tmp_path):
    store = DecisionStore(tmp_path / "review.db")
    snapshot = observe(store)
    store.decide(decision(snapshot))
    changed = copy.deepcopy(INPUT); changed["columns"][1]["required"] = False
    snapshot = observe(store, changed)
    assert next(f for f in snapshot["findings"] if f["location"]["code"] == "invalid_value_type")["state"] == "open"
    with store.connect() as db:
        db.execute("UPDATE runs SET observed_at='2000-01-01T00:00:00+00:00'")
    with pytest.raises(ServiceError, match="changed"):
        store.decide(decision(snapshot))


def test_native_revision_is_bound_but_unrelated_cell_edit_preserves_exception(tmp_path):
    store = DecisionStore(tmp_path / "review.db")
    packet = review(INPUT)
    packet["native_schema"] = {"binding": {"table_id": "synthetic", "updated": "first"}}
    store.decide(decision(store.observe(SCOPE, packet, INPUT["csv_text"])))
    edited = {**INPUT, "csv_text": INPUT["csv_text"].replace("100.01", "101.02")}
    unchanged = review(edited); unchanged["native_schema"] = packet["native_schema"]
    assert next(f for f in store.observe(SCOPE, unchanged, edited["csv_text"])["findings"]
                if f["location"]["code"] == "invalid_value_type")["state"] == "accepted_exception"
    changed = copy.deepcopy(unchanged); changed["native_schema"]["binding"]["updated"] = "second"
    assert all(f["state"] == "open" for f in store.observe(SCOPE, changed, edited["csv_text"])["findings"])


def test_stale_and_simultaneous_decisions_have_one_committed_receipt(tmp_path):
    store = DecisionStore(tmp_path / "review.db")
    request = decision(observe(store))
    def apply():
        try:
            store.decide(request)
            return "committed"
        except ServiceError as error:
            return error.code
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(lambda _: apply(), range(2))) == ["committed", "stale_decision"]
    assert store.read(SCOPE)["history_count"] == 1
    observe(store)
    assert apply() == "stale_decision"


def test_confirmation_and_private_storage_fail_closed_without_overwrite(tmp_path):
    store = DecisionStore(tmp_path / "review.db")
    request = decision(observe(store))
    for change in [{"confirmed": False}, {"reason": " "}, {"reviewer": ""}, {"decision": "approved"}, {"revision": True}]:
        with pytest.raises(ServiceError):
            store.decide({**request, **change})
    assert store.read(SCOPE)["history"] == []
    public = tmp_path / "public"; public.mkdir(mode=0o755)
    with pytest.raises(ValueError):
        DecisionStore(public / "new.db")
    assert not (public / "new.db").exists()
    corrupt = tmp_path / "corrupt.db"; corrupt.write_bytes(b"keep-this-unrelated-private-file"); corrupt.chmod(0o600)
    with pytest.raises(sqlite3.DatabaseError):
        DecisionStore(corrupt)
    assert corrupt.read_bytes() == b"keep-this-unrelated-private-file"
    foreign = tmp_path / "foreign.db"
    with sqlite3.connect(foreign) as db:
        db.execute("CREATE TABLE unrelated (value TEXT)")
    foreign.chmod(0o600)
    before = foreign.read_bytes()
    with pytest.raises(ValueError, match="unrelated"):
        DecisionStore(foreign)
    assert foreign.read_bytes() == before

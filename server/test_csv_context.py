"""Adversarial declared-policy cases; labels are not independent accounting truth."""
import copy
import json

import pytest

from csv_checks import ServiceError
from csv_review import review, verify_packet
from test_csv_review import csv_url, request  # noqa: F401

POLICY = {"period_column": "period", "expected_period": "2026-10",
          "currency_column": "currency", "expected_currency": "USD",
          "unit_column": "unit", "expected_unit": "cents",
          "amount_columns": ["amount"], "accounting_basis": "modified_accrual"}
INPUT = {"columns": [{"name": name, "type": "integer" if name == "amount" else "string"}
                     for name in ["id", "period", "currency", "unit", "amount"]],
         "key_columns": ["id"], "reporting_policy": POLICY,
         "csv_text": "id,period,currency,unit,amount\n001,2026-10,USD,cents,1001\n1,2026-10,USD,cents,-2\n"}


def test_matched_policy_is_not_accounting_acceptance_or_scaling(csv_url):
    status, _, raw = request(csv_url, body=INPUT)
    assert status == 200
    packet = json.loads(raw)
    assert packet["reporting_context"]["status"] == "matched"
    assert packet["reporting_context"]["records_checked"] == 2
    assert packet["result"]["numeric_totals"]["amount"]["total"] == "999"
    assert packet["period_and_units_verified"] is False
    assert packet["reporting_context"]["accounting_correctness_verified"] is False
    assert verify_packet(packet, INPUT["csv_text"])["status"] == "reproduced"


def test_arithmetic_green_cannot_hide_wrong_period_currency_or_units():
    source = INPUT["csv_text"].replace("1,2026-10,USD,cents,-2", "1,2026-09,EUR,units,-2")
    packet = review({**INPUT, "csv_text": source})
    assert packet["result"]["screen_status"] == "passed"
    assert packet["result"]["numeric_totals"]["amount"]["total"] == "999"
    context = packet["reporting_context"]
    assert context["status"] == "failed"
    assert [(i["code"], i["row"], i["column"]) for i in context["issues"]] == [
        ("period_mismatch", 3, "period"), ("currency_mismatch", 3, "currency"), ("unit_mismatch", 3, "unit")]
    assert "EUR" not in json.dumps(packet)  # No observed row values exported.


def test_exact_labels_no_trimming_and_unknowns_never_match():
    packet = review({**INPUT, "csv_text": INPUT["csv_text"].replace("2026-10,USD,cents", "2026-10,USD ,cents", 1)})
    assert packet["reporting_context"]["issues"] == [{"code": "currency_mismatch", "row": 2, "column": "currency"}]
    packet = review({**INPUT, "reporting_policy": {**POLICY, "unit_column": "", "accounting_basis": "unknown"}})
    assert packet["reporting_context"]["status"] == "incomplete"
    assert len(packet["reporting_context"]["unknowns"]) == 2


@pytest.mark.parametrize("change", [{"expected_period": "2026-13"}, {"expected_period": "0000-10"},
                                    {"expected_currency": "usd"}, {"expected_unit": "dollars"},
                                    {"accounting_basis": "approved"}, {"amount_columns": ["period"]},
                                    {"amount_columns": []}, {"amount_columns": ["amount", "amount"]},
                                    {"unit_column": "missing"}, {"period_column": "currency"},
                                    {"approved": True}, {"amount_columns": [False]}])
def test_policy_contract_rejects_guessing_or_authority(change):
    with pytest.raises(ServiceError):
        review({**INPUT, "reporting_policy": {**POLICY, **change}})


def test_headers_ragged_records_and_issue_cap_never_produce_context_match():
    for source in ["id,period,currency,amount\na,2026-10,USD,1\n",
                   "id,period,currency,unit,amount,unit\na,2026-10,USD,cents,1,cents\n",
                   "id,period,currency,unit,amount\na,2026-10,USD,cents\n",
                   "id,period,currency,unit,amount\n"]:
        assert review({**INPUT, "csv_text": source})["reporting_context"]["status"] == "failed"
    source = "id,period,currency,unit,amount\n" + "a,2026-09,EUR,units,1\n" * 40
    context = review({**INPUT, "csv_text": source})["reporting_context"]
    assert context["issue_count"] == 120 and len(context["issues"]) == 100 and context["issues_truncated"]


def test_replay_binds_policy_code_results_and_native_context():
    packet = review(INPUT)
    changed = copy.deepcopy(packet)
    changed["reporting_policy"]["expected_currency"] = "EUR"
    assert "reporting_context" in verify_packet(changed, INPUT["csv_text"])["mismatched_fields"]
    changed = copy.deepcopy(packet)
    changed["context_validator_sha256"] = "different-build"
    assert verify_packet(changed, INPUT["csv_text"])["mismatched_fields"] == ["context_validator_sha256"]
    from csv_native import LSL_ACCOUNT, bind_packet, fingerprint
    binding = {"account_id": LSL_ACCOUNT, "table_id": "a" * 32, "table_name": "zz Krow Synthetic Context",
               "version": 3, "updated": "2026-10-07T00:00:00Z",
               "table_schema": {"columns": INPUT["columns"]}}
    native = bind_packet(packet, {"binding": binding, "schema_sha256": fingerprint(binding), "evidence": "workiva_api_response"})
    assert native["packet_version"] == 3
    assert verify_packet(native, INPUT["csv_text"])["status"] == "reproduced"

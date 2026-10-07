from decimal import Decimal

import pytest

from csv_checks import ServiceError, validate_csv_draft


SCHEMA = [{"name": "id", "type": "string", "required": True}, {"name": "amount", "type": "decimal"}]


def codes(result):
    return [issue["code"] for issue in result["issues"]]


def test_valid_csv_checks_all_rows_and_keeps_exact_numeric_totals():
    result = validate_csv_draft("id,amount\n001,999999999999999999999999999999.123456789\n1,0.000000000000000000000000001\n", SCHEMA, ["id"])
    assert result["screen_status"] == "passed"
    assert result["row_count"] == 2
    assert result["duplicate_key_count"] == 0
    assert result["numeric_totals"]["amount"]["total"] == "999999999999999999999999999999.123456789000000000000000001"
    assert result["numeric_totals"]["amount"]["complete"] is True
    assert "id" not in result["numeric_totals"]
    assert result["native_import_verified"] is False
    assert result["native_schema_verified"] is False
    assert result["accounting_correctness_verified"] is False


def test_decimal_sum_preserves_wide_precision_and_cancellation():
    big = "9" * 512
    tiny = "0." + "0" * 511 + "1"
    result = validate_csv_draft(f"id,amount\na,{big}\nb,{tiny}\nc,-{big}\n", SCHEMA)
    assert result["numeric_totals"]["amount"]["total"] == tiny
    assert result["screen_status"] == "passed"


def test_duplicates_report_both_source_rows_without_collapsing_values():
    result = validate_csv_draft("id,amount\n001,0.1\n001,0.2\n1,0.3\n001,0.4\n", SCHEMA, ["id"])
    duplicates = [issue for issue in result["issues"] if issue["code"] == "duplicate_key"]
    assert [(issue["first_row"], issue["row"]) for issue in duplicates] == [(2, 3), (2, 5)]
    assert result["row_count"] == 4
    assert result["duplicate_key_count"] == 2
    assert Decimal(result["numeric_totals"]["amount"]["total"]) == Decimal("1.0")


def test_composite_keys_preserve_text_and_quoted_crlf_fields():
    schema = [{"name": "id", "type": "text"}, {"name": "label", "type": "string"}, {"name": "amount", "type": "INTEGER"}]
    result = validate_csv_draft('\ufeffid,label,amount\r\n001,"a,b",2\r\n001,"two\r\nlines",3\r\n', schema, ["id", "label"])
    assert result["screen_status"] == "passed"
    assert result["row_count"] == 2
    assert result["numeric_totals"]["amount"]["total"] == "5"


@pytest.mark.parametrize("value", ["NaN", "nan", "Infinity", "-inf", "1,234", "$2", " 2 ", "1e999999", "0x10"])
def test_invalid_numeric_values_fail_without_coercion(value):
    result = validate_csv_draft(f'id,amount\na,"{value}"\n', SCHEMA)
    assert result["screen_status"] == "failed"
    assert codes(result) == ["invalid_value_type"]
    assert result["numeric_totals"]["amount"]["complete"] is False
    assert result["numeric_totals"]["amount"]["validated_nonempty_values"] == 0


def test_partial_total_is_explicit_and_preserves_valid_values():
    result = validate_csv_draft("id,amount\na,1.001\nb,unknown\nc,-0.001\n", SCHEMA)
    total = result["numeric_totals"]["amount"]
    assert total["total"] == "1.000"
    assert total["invalid_values"] == 1
    assert total["complete"] is False
    assert total["source_units"] == "unscaled"


def test_required_and_key_missing_values_are_retained():
    result = validate_csv_draft("id,amount\n,1\na,\n", SCHEMA, ["id"])
    assert result["row_count"] == 2
    assert "required_value_missing" in codes(result)
    assert "key_value_missing" in codes(result)
    assert result["missing_key_count"] == 1


def test_header_failures_do_not_pick_one_duplicate_column():
    result = validate_csv_draft("id,id,extra\na,b,1\n", SCHEMA, ["id"])
    assert {"duplicate_header", "unexpected_column", "missing_column", "key_value_missing"} <= set(codes(result))
    assert result["numeric_totals"]["amount"]["complete"] is False
    assert result["numeric_totals"]["amount"]["validated_nonempty_values"] == 0


def test_reordered_header_is_an_explicit_local_mismatch():
    result = validate_csv_draft("amount,id\n1,a\n", SCHEMA)
    assert result["header_matches_schema_order"] is False
    assert codes(result) == ["column_order_mismatch"]
    assert result["numeric_totals"]["amount"]["total"] == "1"


def test_row_width_failures_and_blank_records_are_not_silently_dropped():
    result = validate_csv_draft("id,amount\na\n\nb,1,extra\nc,2\n", SCHEMA)
    assert result["row_count"] == 4
    assert codes(result) == ["row_width_mismatch"] * 3
    assert result["numeric_totals"]["amount"]["complete"] is False
    assert result["numeric_totals"]["amount"]["total"] == "2"


def test_unknown_schema_type_stays_incomplete_while_other_checks_run():
    schema = [{"name": "id", "type": "uuid", "required": True}, {"name": "amount", "type": "decimal"}]
    result = validate_csv_draft("id,amount\na,2\n", schema)
    assert result["screen_status"] == "incomplete"
    assert result["valid_local_screen"] is False
    assert result["schema_types_supported"] is False
    assert codes(result) == ["unsupported_column_type"]
    assert result["numeric_totals"]["amount"]["total"] == "2"


@pytest.mark.parametrize("kind, good, bad", [
    ("integer", "001", "1.0"),
    ("boolean", "true", "TRUE"),
    ("date", "2024-02-29", "2025-02-29"),
    ("timestamp", "2026-10-02T01:02:03Z", "2026-10-02T01:02:03"),
])
def test_types_are_conservative(kind, good, bad):
    schema = [{"name": "value", "type": kind}]
    assert validate_csv_draft(f"value\n{good}\n", schema)["screen_status"] == "passed"
    assert validate_csv_draft(f"value\n{bad}\n", schema)["screen_status"] == "failed"


def test_issue_truncation_does_not_truncate_validation_or_issue_count():
    result = validate_csv_draft("id,amount\n" + "a,bad\n" * 100, SCHEMA, ["id"], max_issues=2)
    assert result["row_count"] == 100
    assert result["issue_count"] == 199
    assert len(result["issues"]) == 2
    assert result["issues_truncated"] is True
    assert result["numeric_totals"]["amount"]["invalid_values"] == 100


def test_empty_dataset_is_not_a_zero_row_pass():
    result = validate_csv_draft("id,amount\n", SCHEMA)
    assert codes(result) == ["no_data_rows"]
    assert result["screen_status"] == "failed"


@pytest.mark.parametrize("csv_text", ['id,amount\na,"unterminated', 'id,amount\na,"closed"junk\n'])
def test_malformed_csv_is_rejected(csv_text):
    with pytest.raises(ServiceError) as caught:
        validate_csv_draft(csv_text, SCHEMA)
    assert caught.value.code == "invalid_csv"


@pytest.mark.parametrize("arguments", [
    {"csv_text": "id,amount\n" + "a,1\n" * 1001},
    {"csv_text": "id,amount\na," + "x" * 8193},
    {"csv_text": "id,amount\n" + "x" * 262145},
    {"csv_text": "id,amount\na,\x00"},
    {"csv_text": "id,amount\na,\ud800"},
    {"max_issues": True},
    {"max_issues": 101},
    {"key_columns": ["absent"]},
    {"key_columns": ["id", "id"]},
    {"columns": []},
    {"columns": [{"name": "id", "type": "string", "required": "true"}]},
    {"columns": [{"name": "id", "type": "string"}, {"name": "id", "type": "string"}]},
    {"columns": [{"name": "id", "type": "string", "server_path": "/etc/passwd"}]},
])
def test_bounds_and_invalid_contracts_reject_without_partial_success(arguments):
    defaults = {"csv_text": "id,amount\na,1\n", "columns": SCHEMA}
    with pytest.raises(ServiceError):
        validate_csv_draft(**{**defaults, **arguments})

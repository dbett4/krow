"""CSV checks reused from Lockfield Workiva Plugin v0.4.0; see docs/csv-review.md.

Deterministic checks of explicit input; never opens files or imports data.
"""

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
import io
import re


class ServiceError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


MAX_CSV_BYTES = 262144
MAX_ROWS = 1000
MAX_COLUMNS = 64
MAX_FIELD_CHARS = 8192
TYPE_ALIASES = {"text": "string"}
SUPPORTED_TYPES = frozenset({"string", "integer", "decimal", "boolean", "date", "timestamp"})
INTEGER = re.compile(r"^[+-]?[0-9]+$")
DECIMAL = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")
TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})$")


def _invalid(message: str, code: str = "invalid_argument") -> None:
    raise ServiceError(code, message)


def _columns(columns):
    if not isinstance(columns, list) or not 1 <= len(columns) <= MAX_COLUMNS:
        _invalid("Supply between 1 and 64 explicit schema columns.")
    result = []
    seen = set()
    for column in columns:
        if not isinstance(column, dict) or set(column) - {"name", "type", "required"}:
            _invalid("Schema columns accept only name, type and required.")
        name, kind = column.get("name"), column.get("type")
        if not isinstance(name, str) or not name.strip() or len(name) > 128 or any(c in name for c in "\x00\r\n"):
            _invalid("Schema column names must be nonempty bounded single-line strings.")
        if name in seen:
            _invalid("Schema column names must be unique.")
        if not isinstance(kind, str) or not kind.strip() or len(kind) > 64:
            _invalid("Each schema column needs an explicit bounded type.")
        if type(column.get("required", False)) is not bool:
            _invalid("Schema required flags must be booleans.")
        seen.add(name)
        kind = kind.strip().lower()
        result.append({"name": name, "type": TYPE_ALIASES.get(kind, kind), "required": column.get("required", False)})
    return result


def _number(value, kind):
    expression = INTEGER if kind == "integer" else DECIMAL
    if not expression.fullmatch(value) or len(value) > 1024:
        return None
    try:
        number = Decimal(value)
        parts = number.as_tuple()
        # Bound both precision and expansion without converting through float.
        if not number.is_finite() or len(parts.digits) > 512 or abs(parts.exponent) > 512:
            return None
        return number
    except (InvalidOperation, ValueError):
        return None


def _valid(value, kind):
    if kind == "string":
        return True
    if kind in {"integer", "decimal"}:
        return _number(value, kind) is not None
    if kind == "boolean":
        return value in {"true", "false"}
    if kind == "date":
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return False
        try:
            date.fromisoformat(value)
            return True
        except ValueError:
            return False
    if kind == "timestamp":
        if not TIMESTAMP.fullmatch(value):
            return False
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False
    return None


def validate_csv_draft(csv_text, columns, key_columns=None, max_issues=50):
    """Screen an entire bounded CSV against the caller's explicit schema.

    Numeric totals include only valid nonempty values and preserve source units.
    Key comparison is exact text: numeric-looking IDs and leading zeros survive.
    A local pass never attests to native import, schema authority or accounting.
    """
    if not isinstance(csv_text, str) or not csv_text or "\x00" in csv_text:
        _invalid("Supply nonempty CSV text without NUL characters.")
    try:
        size = len(csv_text.encode("utf-8"))
    except UnicodeError:
        _invalid("CSV text must be valid UTF-8.")
    if size > MAX_CSV_BYTES:
        _invalid("CSV input exceeds 262144 UTF-8 bytes.")
    if type(max_issues) is not int or not 1 <= max_issues <= 100:
        _invalid("max_issues must be an integer between 1 and 100.")
    schema = _columns(columns)
    names = [column["name"] for column in schema]
    keys = [] if key_columns is None else key_columns
    if (not isinstance(keys, list) or len(keys) > 8
            or any(not isinstance(key, str) or key not in names for key in keys)
            or len(set(keys)) != len(keys)):
        _invalid("Key columns must be at most 8 distinct schema column names.")

    issues = []
    issue_count = 0
    error_count = 0
    unknown_count = 0

    def issue(code, *, row=None, column=None, severity="error", **details):
        nonlocal issue_count, error_count, unknown_count
        issue_count += 1
        error_count += severity == "error"
        unknown_count += severity == "unknown"
        if len(issues) < max_issues:
            item = {"code": code, "severity": severity, **details}
            if row is not None:
                item["row"] = row
            if column is not None:
                item["column"] = column
            issues.append(item)

    reader = csv.reader(io.StringIO(csv_text.removeprefix("\ufeff"), newline=""), strict=True)
    try:
        header = next(reader)
        if not 1 <= len(header) <= MAX_COLUMNS or any(len(name) > 128 for name in header):
            _invalid("CSV header must contain between 1 and 64 bounded column names.")
        positions = {}
        for index, name in enumerate(header):
            positions.setdefault(name, []).append(index)
        for name, indexes in positions.items():
            if len(indexes) > 1:
                issue("duplicate_header", row=1, column=name, occurrences=len(indexes))
            if name not in names:
                issue("unexpected_column", row=1, column=name)
        for name in names:
            if name not in positions:
                issue("missing_column", row=1, column=name)
        order_matches = header == names
        if not order_matches and len(header) == len(names) and set(header) == set(names):
            issue("column_order_mismatch", row=1)
        for column in schema:
            if column["type"] not in SUPPORTED_TYPES:
                issue("unsupported_column_type", column=column["name"], severity="unknown", declared_type=column["type"])

        totals = {column["name"]: {"total": Decimal(0), "validated_nonempty_values": 0, "invalid_values": 0}
                  for column in schema if column["type"] in {"integer", "decimal"}}
        seen_keys = {}
        row_count = 0
        invalid_width_rows = 0
        duplicate_key_count = 0
        missing_key_count = 0
        for row in reader:
            row_count += 1
            source_row = row_count + 1
            if row_count > MAX_ROWS:
                _invalid("CSV input exceeds 1000 data rows; no partial pass is returned.")
            if any(len(value) > MAX_FIELD_CHARS for value in row):
                _invalid("CSV fields must contain at most 8192 characters.")
            if len(row) != len(header):
                invalid_width_rows += 1
                issue("row_width_mismatch", row=source_row, csv_line_end=reader.line_num,
                      expected_columns=len(header), actual_columns=len(row))
                continue
            values = {name: row[indexes[0]] for name, indexes in positions.items() if len(indexes) == 1}
            for column in schema:
                name, kind = column["name"], column["type"]
                if name not in values:
                    continue
                raw = values[name]
                if raw == "":
                    if column["required"]:
                        issue("required_value_missing", row=source_row, column=name, csv_line_end=reader.line_num)
                        if name in totals:
                            totals[name]["invalid_values"] += 1
                    continue
                valid = _valid(raw, kind)
                if valid is False:
                    issue("invalid_value_type", row=source_row, column=name, expected_type=kind, csv_line_end=reader.line_num)
                    if name in totals:
                        totals[name]["invalid_values"] += 1
                elif valid and name in totals:
                    with localcontext() as context:
                        # 512 significant digits + 512 places on either side,
                        # plus carries across at most 1000 rows.
                        context.prec = 1600
                        totals[name]["total"] += _number(raw, kind)
                    totals[name]["validated_nonempty_values"] += 1
            if keys:
                if any(key not in values or values[key] == "" for key in keys):
                    missing_key_count += 1
                    issue("key_value_missing", row=source_row, csv_line_end=reader.line_num)
                else:
                    key = tuple(values[name] for name in keys)
                    if key in seen_keys:
                        duplicate_key_count += 1
                        issue("duplicate_key", row=source_row, first_row=seen_keys[key], csv_line_end=reader.line_num)
                    else:
                        seen_keys[key] = source_row
        if row_count == 0:
            issue("no_data_rows")
    except (csv.Error, StopIteration):
        _invalid("CSV structure is invalid or its header is missing.", "invalid_csv")

    numeric_totals = {}
    for name, value in totals.items():
        numeric_totals[name] = {
            **value,
            "total": format(value["total"], "f"),
            "source_units": "unscaled",
            "complete": value["invalid_values"] == 0 and invalid_width_rows == 0 and len(positions.get(name, [])) == 1,
        }
    status = "failed" if error_count else ("incomplete" if unknown_count else "passed")
    return {
        "screen_status": status,
        "valid_local_screen": status == "passed",
        "native_import_verified": False,
        "native_schema_verified": False,
        "accounting_correctness_verified": False,
        "source_kind": "user_supplied_csv",
        "schema_origin": "caller_supplied",
        "schema_types_supported": unknown_count == 0,
        "complete_input": True,
        "csv_bytes": size,
        "row_count": row_count,
        "header_columns": header,
        "header_matches_schema_order": order_matches,
        "key_columns": list(keys),
        "key_comparison": "exact_text",
        "duplicate_key_count": duplicate_key_count,
        "missing_key_count": missing_key_count,
        "issue_count": issue_count,
        "issues": issues,
        "issues_truncated": issue_count > len(issues),
        "numeric_totals": numeric_totals,
        "limitations": "Local checks only. Empty fields are treated as missing; other text is preserved without trimming or coercion. Dates require YYYY-MM-DD, booleans require true/false, timestamps require ISO seconds and an explicit timezone. Totals include valid numeric values only, preserve source units, and never establish native import success or accounting correctness.",
    }

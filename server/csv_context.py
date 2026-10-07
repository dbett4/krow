"""Declared reporting-policy checks, not inferred units or accounting approval."""
import csv
import io
import re

from csv_checks import ServiceError, _columns


def check_context(csv_text, columns, policy):
    fields = {"period_column", "expected_period", "currency_column", "expected_currency",
              "unit_column", "expected_unit", "amount_columns", "accounting_basis"}
    names = {item["name"]: item["type"] for item in _columns(columns)}
    if (not isinstance(policy, dict) or set(policy) != fields
            or any(not isinstance(policy[key], str) for key in fields - {"amount_columns"})
            or not re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", policy["expected_period"])
            or policy["expected_period"].startswith("0000")
            or not re.fullmatch(r"[A-Z]{3}", policy["expected_currency"])
            or policy["expected_unit"] not in {"units", "cents", "thousands", "millions"}
            or policy["accounting_basis"] not in {"unknown", "cash", "accrual", "modified_accrual"}):
        raise ServiceError("invalid_context", "Declare a YYYY-MM period, three-letter uppercase currency label, supported amount unit and accounting basis. Nothing is inferred.")
    bindings = [policy["period_column"], policy["currency_column"]]
    if policy["unit_column"]:
        bindings.append(policy["unit_column"])
    amounts = policy["amount_columns"]
    if (any(names.get(name) not in {"string", "text"} for name in bindings)
            or len(set(bindings)) != len(bindings)
            or not isinstance(amounts, list) or not amounts or len(amounts) > 64
            or any(not isinstance(name, str) or names.get(name) not in {"integer", "decimal"} for name in amounts)
            or len(set(amounts)) != len(amounts)):
        raise ServiceError("invalid_context", "Bind separate text period/currency/unit columns and at least one unique numeric amount column from the declared schema. Leave unit column empty only when row units cannot be checked.")
    reader = csv.reader(io.StringIO(csv_text, newline=""), strict=True)
    header = next(reader)
    positions = {name: header.index(name) for name in bindings if header.count(name) == 1}
    issues, issue_count, checked = [], 0, 0
    def issue(code, row=None, column=None):
        nonlocal issue_count
        issue_count += 1
        if len(issues) < 100:
            issues.append({"code": code, **({"row": row} if row else {}),
                           **({"column": column} if column else {})})
    if any(header.count(name) != 1 for name in bindings + amounts):
        issue("context_header_unusable")
    for row_number, row in enumerate(reader, start=2):
        if len(row) != len(header):
            issue("context_row_unusable", row_number)
            continue
        checked += 1
        for field, expected, code in [("period_column", "expected_period", "period_mismatch"),
                                     ("currency_column", "expected_currency", "currency_mismatch"),
                                     ("unit_column", "expected_unit", "unit_mismatch")]:
            name = policy[field]
            if name in positions and row[positions[name]] != policy[expected]:
                issue(code, row_number, name)
    if not checked:
        issue("context_no_data")
    unknowns = []
    if not policy["unit_column"]:
        unknowns.append("Row units are not checked; amount units are a declaration only.")
    if policy["accounting_basis"] == "unknown":
        unknowns.append("Accounting basis has not been declared.")
    return {"status": "failed" if issue_count else "incomplete" if unknowns else "matched",
            "issue_count": issue_count, "issues": issues, "issues_truncated": issue_count > len(issues),
            "records_checked": checked, "unknowns": unknowns, "amount_units": "unscaled",
            "policy_source": "reviewer_declared_not_independently_verified",
            "accounting_correctness_verified": False,
            "limitations": "Exact row labels only, not fiscal calendar, FX, unit conversion, sign convention, account mapping or accounting-basis correctness. Currency labels are not a verified currency registry. Mixed labels make combined totals unsuitable for reporting."}

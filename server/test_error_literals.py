"""Explicit literal evidence must not erase genuine or contradictory errors."""
import pytest

from detectors import ERROR_PREFIXES, detect_broken_ref, scan_cells


@pytest.mark.parametrize("literal", ["#REF!note", "#REF!", "#NAME?", '#REF! "note"'])
def test_literal_text_is_not_a_formula_error(literal):
    formula = '= "' + literal.replace('"', '""') + '" '
    cell = {"addr": "B7", "formula": formula, "calculatedValue": literal, "value": literal}
    assert detect_broken_ref(cell) is None
    assert not any(f["kind"] == "broken-ref" for f in scan_cells([cell]))


@pytest.mark.parametrize("token", ERROR_PREFIXES)
def test_real_error_tokens_remain_surfaced(token):
    result = detect_broken_ref({"addr": "C9", "formula": "=A1/B1", "calculatedValue": token})
    assert result["kind"] == "broken-ref" and result["fixable"] is False


@pytest.mark.parametrize("formula", [None, "=A1", '=IF(A1,"#REF!note",B1)', '= "note"', '= "#REF!note"&A1'])
def test_unknown_nonliteral_or_contradictory_formula_cannot_hide_error(formula):
    assert detect_broken_ref({"addr": "D3", "formula": formula, "calculatedValue": "#REF!"}) is not None

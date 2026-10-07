"""Measurement arithmetic and integrity tests; do not tune detector outputs here."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from evaluate_detectors import evaluate

FIXTURE = Path(__file__).parent / "fixtures/detector-calibration.json"


def test_actual_detector_scores_and_literal_text_guard():
    report = evaluate(json.loads(FIXTURE.read_text()))
    assert report["case_count"] == 6 and report["cell_count"] == 18
    count = report["metrics"]["broken-ref"]
    assert (count["tp"], count["fp"], count["fn"], count["tn"]) == (2, 0, 0, 16)
    assert count["precision"] == 1 and count["recall"] == 1 and count["targets_met_on_sample"] is True
    for kind in ("blank-linked-cell", "low-contrast"):
        assert report["metrics"][kind]["tp"] == 2 and report["metrics"][kind]["fp"] == 0
    assert report["errors"] == []
    assert report["independence_verified"] is False and report["release_acceptance_verified"] is False
    assert report["workiva_requests"] == 0 and "#REF!note" not in json.dumps(report)


def test_scorer_does_not_swap_precision_recall_or_hide_misses():
    corpus = json.loads(FIXTURE.read_text())
    # Deliberately competing labels exercise FP and FN independently of prediction.
    corpus["cases"][0]["expected"] = [{"kind": "broken-ref", "addr": "A1"},
                                        {"kind": "broken-ref", "addr": "A3"}]
    corpus["cases"][-1]["expected"] = [{"kind": "broken-ref", "addr": "F2"}]
    count = evaluate(corpus)["metrics"]["broken-ref"]
    assert (count["tp"], count["fp"], count["fn"], count["tn"]) == (1, 1, 2, 14)
    assert count["precision"] == .5 and count["recall"] == 1 / 3


def test_no_positive_or_no_predictions_is_not_a_pass():
    corpus = json.loads(FIXTURE.read_text())
    corpus["cases"] = [corpus["cases"][-1]]
    for count in evaluate(corpus)["metrics"].values():
        assert count["precision"] is None and count["recall"] is None
        assert count["targets_met_on_sample"] is False
    corpus["cases"][0]["expected"] = [{"kind": "broken-ref", "addr": "F2"}]
    count = evaluate(corpus)["metrics"]["broken-ref"]
    assert count["recall"] == 0 and count["targets_met_on_sample"] is False


def test_duplicate_identity_labels_and_split_leakage_fail():
    original = json.loads(FIXTURE.read_text())
    for variant in ("id", "address", "label", "split"):
        corpus = copy.deepcopy(original)
        if variant == "id":
            corpus["cases"].append(copy.deepcopy(corpus["cases"][0]))
        elif variant == "address":
            corpus["cases"][0]["cells"].append(copy.deepcopy(corpus["cases"][0]["cells"][0]))
        elif variant == "label":
            corpus["cases"][0]["expected"].append(copy.deepcopy(corpus["cases"][0]["expected"][0]))
        else:
            leaked = copy.deepcopy(corpus["cases"][0]); leaked.update(id="leaked", split="held_out")
            corpus["cases"].append(leaked)
        with pytest.raises(ValueError):
            evaluate(corpus)
    with pytest.raises(ValueError):
        evaluate(original, "held_out")


def test_claimed_independence_never_becomes_release_authority():
    corpus = json.loads(FIXTURE.read_text())
    corpus["label_provenance"]["independent"] = True
    report = evaluate(corpus)
    assert report["label_provenance"]["independent"] is True
    assert report["independence_verified"] is False and report["release_acceptance_verified"] is False


def test_cli_measurement_and_invalid_split_have_honest_exit_status():
    command = [sys.executable, str(Path(__file__).parent / "evaluate_detectors.py"), str(FIXTURE)]
    success = subprocess.run(command, capture_output=True, text=True, timeout=5)
    assert success.returncode == 0 and json.loads(success.stdout)["metrics"]["broken-ref"]["fp"] == 0
    failed = subprocess.run(command + ["--split", "held_out"], capture_output=True, text=True, timeout=5)
    assert failed.returncode == 2 and json.loads(failed.stdout)["status"] == "invalid"

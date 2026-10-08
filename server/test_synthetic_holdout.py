"""One-use temporal holdout integrity and independent reference truth, not tuned scores."""
from concurrent.futures import ThreadPoolExecutor
import json
import os

import pytest

import synthetic_holdout as holdout


def test_reference_truth_has_both_sides_of_aa_and_exact_extremes():
    assert holdout.contrast("#000000", "#FFFFFF") == 21
    assert holdout.contrast("#ABCDEF", "#ABCDEF") == 1
    assert holdout.contrast("#777777", "#FFFFFF") < 4.5
    assert holdout.contrast("#767676", "#FFFFFF") > 4.5
    assert holdout.contrast("#FFFFFF", "#777777") == holdout.contrast("#777777", "#FFFFFF")


def test_generation_never_copies_tuning_labels_and_has_positive_and_negative_boundaries():
    first, second = holdout.generate("12"), holdout.generate("13")
    assert first != second and first == holdout.generate("12")
    assert len(first["cases"]) == 48 and all(c["split"] == "held_out" for c in first["cases"])
    for case in first["cases"]:
        labels = {(label["kind"], label["addr"]) for label in case["expected"]}
        cells = case["cells"]
        assert ("broken-ref", cells[0]["addr"]) in labels
        assert ("broken-ref", cells[1]["addr"]) not in labels
        assert ("blank-linked-cell", cells[3]["addr"]) in labels
        assert ("blank-linked-cell", cells[4]["addr"]) not in labels
        assert ("low-contrast", cells[6]["addr"]) not in labels
        assert ("low-contrast", cells[7]["addr"]) in labels
    assert first["label_provenance"]["independent"] is False


def test_freeze_precedes_new_corpus_and_one_consumption_survives_reopen(tmp_path):
    folder = tmp_path / "run"
    plan = holdout.prepare(folder)
    assert sorted(p.name for p in folder.iterdir()) == ["plan.json"]
    assert plan["build_sha256"] == holdout.build()
    report = holdout.run(folder)
    assert report["case_count"] == 48 and report["cell_count"] == 624
    assert report["tuning_labels_reused"] is False and report["workiva_requests"] == 0
    assert not report["independence_verified"] and not report["release_acceptance_verified"]
    original = (folder / "result.json").read_bytes()
    with pytest.raises(FileExistsError):
        holdout.run(folder)
    with pytest.raises(FileExistsError):
        holdout.prepare(folder)
    assert (folder / "result.json").read_bytes() == original
    assert os.stat(folder).st_mode & 0o777 == 0o700
    assert all(os.stat(p).st_mode & 0o777 == 0o600 for p in folder.iterdir())


def test_changed_build_or_threshold_cannot_score_a_frozen_run(tmp_path, monkeypatch):
    folder = tmp_path / "run"; holdout.prepare(folder)
    with monkeypatch.context() as patch:
        patch.setattr(holdout, "build", lambda: {"detectors": "different"})
        with pytest.raises(ValueError, match="changed"):
            holdout.run(folder)
    assert not (folder / "consumed.json").exists()
    plan = json.loads((folder / "plan.json").read_text())
    plan["policy"]["precision"] = .1
    (folder / "plan.json").write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="changed"):
        holdout.run(folder)
    assert not (folder / "result.json").exists()


def test_simultaneous_run_has_exactly_one_consumption(tmp_path):
    folder = tmp_path / "run"; holdout.prepare(folder)
    def attempt():
        try:
            holdout.run(folder)
            return "scored"
        except FileExistsError:
            return "consumed"
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(lambda _: attempt(), range(2))) == ["consumed", "scored"]


def test_interrupted_run_is_not_automatically_retried(tmp_path, monkeypatch):
    folder = tmp_path / "run"; holdout.prepare(folder)
    with monkeypatch.context() as patch:
        def interrupt(*args):
            raise ValueError("interrupted")
        patch.setattr(holdout, "evaluate", interrupt)
        with pytest.raises(ValueError, match="interrupted"):
            holdout.run(folder)
    assert (folder / "consumed.json").exists() and not (folder / "result.json").exists()
    with pytest.raises(FileExistsError):
        holdout.run(folder)

#!/usr/bin/env python3
"""Offline normalized-cell accuracy measurement; never claims independent release proof."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import re
import statistics
import time

from detectors import scan_cells

ROOT = Path(__file__).resolve().parent
MODULES = ("detectors", "display_wrapper", "junk_decimal", "format_lane", "hardcoded_value", "formula_hygiene")


def evaluate(corpus, split="calibration"):
    if (not isinstance(corpus, dict) or set(corpus) != {"corpus_version", "label_provenance", "detector_kinds", "cases"}
            or type(corpus["corpus_version"]) is not int or corpus["corpus_version"] != 1):
        raise ValueError("Supply a version 1 labeled corpus with provenance, kinds and cases.")
    provenance, kinds, cases = corpus["label_provenance"], corpus["detector_kinds"], corpus["cases"]
    if (not isinstance(provenance, dict) or set(provenance) != {"author", "method", "independent"}
            or any(not isinstance(provenance[k], str) or not 1 <= len(provenance[k]) <= 500 for k in ("author", "method"))
            or type(provenance["independent"]) is not bool
            or not isinstance(kinds, list) or not 1 <= len(kinds) <= 32
            or any(not isinstance(k, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", k) for k in kinds)
            or len(set(kinds)) != len(kinds) or not isinstance(cases, list) or not 1 <= len(cases) <= 1000
            or split not in {"calibration", "held_out"}):
        raise ValueError("Invalid provenance, detector scope, case count or split.")
    # scan_cells historically skips optional API modules. Evaluation must not.
    for module in MODULES:
        importlib.import_module(module)
    seen, content_splits, selected = set(), {}, []
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"id", "split", "cells", "expected"}:
            raise ValueError("Every case needs id, split, cells and complete scoped expected labels.")
        cid, cells, expected = case["id"], case["cells"], case["expected"]
        if (not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", cid) or cid in seen
                or case["split"] not in {"calibration", "held_out"}
                or not isinstance(cells, list) or not 1 <= len(cells) <= 1000
                or any(not isinstance(c, dict) or not isinstance(c.get("addr"), str)
                       or not re.fullmatch(r"[A-Z]{1,4}[1-9][0-9]{0,6}", c["addr"]) for c in cells)
                or len({c["addr"] for c in cells}) != len(cells) or not isinstance(expected, list)):
            raise ValueError("Invalid or duplicate case/address, split or labels.")
        addresses = {c["addr"] for c in cells}
        labels = set()
        for label in expected:
            if not isinstance(label, dict) or set(label) != {"kind", "addr"} or label.get("kind") not in kinds or label.get("addr") not in addresses:
                raise ValueError("Expected labels must reference this case's scoped kind and cell.")
            pair = (label["kind"], label["addr"])
            if pair in labels:
                raise ValueError("Duplicate expected finding.")
            labels.add(pair)
        # Exact same inputs cannot masquerade as held-out cases, even with new IDs/labels.
        digest = hashlib.sha256(json.dumps(sorted(cells, key=lambda c: c["addr"]), sort_keys=True).encode()).hexdigest()
        if digest in content_splits and content_splits[digest] != case["split"]:
            raise ValueError("Identical inputs leak across calibration/held-out splits.")
        content_splits[digest] = case["split"]
        seen.add(cid)
        if case["split"] == split:
            selected.append((cid, cells, labels))
    if not selected:
        raise ValueError("Selected split has no cases; an empty benchmark is not success.")
    counts = {kind: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for kind in kinds}
    errors, excluded, latencies = [], {}, []
    for cid, cells, expected in selected:
        start = time.perf_counter()
        findings = scan_cells(cells)
        latencies.append((time.perf_counter() - start) * 1000)
        predicted = {(f["kind"], f["addr"]) for f in findings if f["kind"] in kinds}
        if any(addr not in {c["addr"] for c in cells} for _, addr in predicted):
            raise ValueError("Detector emitted a location outside this case.")
        for finding in findings:
            if finding["kind"] not in kinds:
                excluded[finding["kind"]] = excluded.get(finding["kind"], 0) + 1
        for kind in kinds:
            actual = {addr for k, addr in expected if k == kind}
            emitted = {addr for k, addr in predicted if k == kind}
            counts[kind]["tp"] += len(actual & emitted)
            counts[kind]["fp"] += len(emitted - actual)
            counts[kind]["fn"] += len(actual - emitted)
            counts[kind]["tn"] += len(cells) - len(actual | emitted)
        errors.extend({"case_id": cid, "kind": kind, "addr": addr, "error": code}
                      for pairs, code in [(predicted - expected, "false_positive"), (expected - predicted, "false_negative")]
                      for kind, addr in sorted(pairs))
    for count in counts.values():
        tp, fp, fn, tn = (count[k] for k in ("tp", "fp", "fn", "tn"))
        count["precision"] = tp / (tp + fp) if tp + fp else None
        count["recall"] = tp / (tp + fn) if tp + fn else None
        count["targets_met_on_sample"] = (tp + fn > 0 and tn + fp > 0 and count["precision"] is not None
                                          and count["precision"] >= .95 and count["recall"] >= .90)
    return {"product": "Krow", "generated_at": datetime.now(timezone.utc).isoformat(),
            "split": split, "case_count": len(selected), "cell_count": sum(len(cells) for _, cells, _ in selected),
            "label_provenance": provenance, "independence_verified": False, "release_acceptance_verified": False,
            "metrics": counts, "errors": errors, "excluded_findings_by_kind": excluded,
            "latency_ms": {"p50": statistics.median(latencies), "p95": sorted(latencies)[max(0, (95 * len(latencies) + 99) // 100 - 1)]},
            "workiva_requests": 0, "corpus_sha256": hashlib.sha256(json.dumps(corpus, sort_keys=True).encode()).hexdigest(),
            "build_sha256": {module: hashlib.sha256((ROOT / (module + ".py")).read_bytes()).hexdigest() for module in MODULES},
            "limits": "Normalized API-cell detectors only, before queue grouping. Vision, native enrichment and judgment validity excluded. Targets 95% precision/90% recall are sample scores, not confidence bounds or independent adjudication. Absence of a scoped label means a labeled negative; corpus completeness is the labeler's responsibility."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--split", choices=("calibration", "held_out"), default="calibration")
    args = parser.parse_args()
    try:
        raw = args.corpus.read_bytes()
        if len(raw) > 2_000_000:
            raise ValueError("Corpus exceeds 2 MB.")
        result = evaluate(json.loads(raw), args.split)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError):
        print(json.dumps({"status": "invalid", "error": "Corpus, detector dependencies or normalized inputs could not be evaluated. No score or release approval produced."}))
        return 2
    print(json.dumps(result, indent=2))
    return 0  # Successful measurement can contain failures; not a release gate.


if __name__ == "__main__":
    raise SystemExit(main())

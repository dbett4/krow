#!/usr/bin/env python3
"""Prospective synthetic input holdout, not independent reviewer or release approval."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import stat

from evaluate_detectors import MODULES, ROOT, evaluate

KINDS = ["broken-ref", "blank-linked-cell", "low-contrast"]
POLICY = {"precision": .95, "recall": .90, "cases": 48,
          "scope": "Normalized observed errors, explicit linked-empty displays, normal-size sRGB text below WCAG AA 4.5. Native enrichment and accounting judgments excluded."}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def build():
    return {name: sha((ROOT / (name + ".py")).read_bytes())
            for name in (*MODULES, "evaluate_detectors", "synthetic_holdout")}


def save(path, value):
    with path.open("x") as file:
        json.dump(value, file, indent=2)
    path.chmod(0o600)


def prepare(folder):
    # Never reuses a run directory, dataset or tuning seed.
    folder.mkdir(mode=0o700)
    plan = {"product": "Krow", "prepared_at": datetime.now(timezone.utc).isoformat(),
            "build_sha256": build(), "policy": POLICY,
            "calibration_sha256": sha((ROOT / "fixtures/detector-calibration.json").read_bytes()),
            "independence_verified": False, "release_acceptance_verified": False}
    save(folder / "plan.json", plan)
    return plan


def contrast(fg, bg):
    """Reference from WCAG sRGB relative luminance, not detector outputs/helpers."""
    def luminance(color):
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
        return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))
    high, low = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (high + .05) / (low + .05)


def generate(seed):
    rng = random.Random(int(seed, 16))
    cases = []
    for index in range(POLICY["cases"]):
        row = rng.randrange(101, 900001)
        cells, labels = [], []
        def add(cell, kind=None):
            address = chr(65 + len(cells)) + str(row)
            cells.append({"addr": address, **cell})
            if kind:
                labels.append({"kind": kind, "addr": address})
        token = rng.choice(("#NUM!", "#N/A", "#NAME?", "#NULL!", "#SHEET!"))
        # Observed native-style error is positive. Intentional complete text literals
        # and ordinary documentation are negatives by the declared truth contract.
        add({"formula": "=SyntheticMissing" + str(rng.randrange(10000)), "value": token,
             "calculatedValue": token}, "broken-ref")
        literal = token + ' reference "' + secrets_from_rng(rng) + '"'
        add({"formula": '="' + literal.replace('"', '""') + '"', "value": literal, "calculatedValue": literal})
        add({"value": "Guidance " + token + " " + secrets_from_rng(rng)})
        add({"isLinked": True, "value": "", "calculatedValue": "", "type": "plainText"}, "blank-linked-cell")
        add({"isLinked": True, "value": str(rng.randrange(1, 100000)), "type": "plainText"})
        add({"isLinked": False, "value": "", "type": "plainText"})
        # Include both sides of AA and random chromatic pairs. Expected truth comes
        # from the independently expressed reference, never from scan_cells.
        pairs = [("#767676", "#FFFFFF"), ("#777777", "#FFFFFF")]
        pairs += [("#" + f"{rng.randrange(0x1000000):06X}", "#" + f"{rng.randrange(0x1000000):06X}") for _ in range(4)]
        for fg, bg in pairs:
            add({"value": "Synthetic label " + secrets_from_rng(rng), "fontColor": fg,
                 "backgroundColor": bg, "type": "plainText"},
                "low-contrast" if contrast(fg, bg) < 4.5 else None)
        add({"value": "", "fontColor": "#888888", "backgroundColor": "#888888"})
        cases.append({"id": f"prospective-{index:03}", "split": "held_out", "cells": cells, "expected": labels})
    return {"corpus_version": 1, "label_provenance": {
        "author": "Krow prospective synthetic protocol; same builder, not an independent labeler",
        "method": "New random cases generated after build/protocol freeze. Declared observation grammar and WCAG reference supply labels; calibration labels are never copied. One-use receipt; no detector tuning on these results.",
        "independent": False}, "detector_kinds": KINDS, "cases": cases}


def secrets_from_rng(rng):
    return f"{rng.getrandbits(48):012x}"


def run(folder):
    info = folder.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("Use the prepared private directory.")
    plan_bytes = (folder / "plan.json").read_bytes()
    plan = json.loads(plan_bytes)
    if (plan["build_sha256"] != build() or plan["policy"] != POLICY
            or plan["calibration_sha256"] != sha((ROOT / "fixtures/detector-calibration.json").read_bytes())):
        raise ValueError("Frozen build/protocol/calibration changed; this holdout cannot be scored.")
    # A failed/interrupted attempt remains consumed. No automatic rerun or retry.
    save(folder / "consumed.json", {"plan_sha256": sha(plan_bytes), "started_at": datetime.now(timezone.utc).isoformat()})
    seed = secrets.token_hex(16)
    corpus = generate(seed)
    calibration = json.loads((ROOT / "fixtures/detector-calibration.json").read_text())
    old_inputs = {sha(json.dumps({k: v for k, v in cell.items() if k != "addr"}, sort_keys=True).encode())
                  for case in calibration["cases"] for cell in case["cells"]}
    # Whole-case/address-only relabeling is not enough. Report any reused cell
    # patterns explicitly; invariant primitives (linked empty) are not new families.
    reused = sum(sha(json.dumps({k: v for k, v in cell.items() if k != "addr"}, sort_keys=True).encode()) in old_inputs
                 for case in corpus["cases"] for cell in case["cells"])
    save(folder / "corpus.json", corpus)
    report = evaluate(corpus, "held_out")
    if plan["build_sha256"] != build():
        raise ValueError("Build changed during evaluation; no acceptance receipt.")
    report.update({"holdout_process": "prospective_input_holdout_consumed_once", "seed": seed,
                   "plan_sha256": sha(plan_bytes), "frozen_build_sha256": plan["build_sha256"],
                   "exact_calibration_cell_patterns_reused": reused,
                   "tuning_labels_reused": False, "semantic_family_independence_verified": False,
                   "limits": report["limits"] + " Same builder authored protocol. New realizations, not independent human/native labels or unseen defect families. Failed cases are now exposed and must never be reused as holdout after tuning."})
    save(folder / "result.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "run"))
    parser.add_argument("directory", type=Path, help="New owner-only run directory, never an existing output.")
    args = parser.parse_args()
    try:
        result = prepare(args.directory) if args.operation == "prepare" else run(args.directory)
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        print(json.dumps({"status": "refused", "error": "Run already exists/consumed, permissions are unsafe, or frozen inputs changed. No score or approval claimed; preserve the directory for reconciliation."}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

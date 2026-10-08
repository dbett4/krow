# Wingman prospective synthetic holdout — October 8, 2026

Protocol committed before preparing this run. Detector files were not tuned or
changed. `.amp/in/holdout-20261008-a/plan.json` froze detector/evaluator/protocol/
calibration hashes and targets before seed/corpus creation. One exclusive consumption
marker prevents repeat scoring, including after interrupted attempts.

Actual first run: 48 new mixed cases, 624 normalized cells, zero exact calibration
cell-pattern reuse (address-independent), zero copied tuning labels, no Workiva calls.
Fresh synthetic labels derive from declared observation grammar and a separately
expressed WCAG sRGB contrast reference, not detector predictions.

| Kind | TP | FP | FN | TN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| broken-ref | 48 | 0 | 0 | 576 | 100% | 100% |
| blank-linked-cell | 48 | 0 | 0 | 576 | 100% | 100% |
| low-contrast | 215 | 0 | 0 | 409 | 100% | 100% |

Observed per-case p50 0.782 ms / p95 2.635 ms. No false-positive/missed locations
on this sample. Other detector outputs remain counted as exclusions in the result.
These are sample metrics, not confidence bounds, end-to-end native latency, or
independent product accuracy. Mixed cases make other families' cells negatives;
the true-negative counts do not establish production prevalence.

Six process/reference regressions passed: exact reference extremes and both sides
of AA, new generation without copied labels, freeze-before-corpus, restart/duplicate
run refusal, frozen-build/threshold drift, simultaneous one-use claim, interrupted
run refusal and private permissions. Full server suite: 838 passed, 13 optional
vision skips. Raw generated cases and complete counts/exclusions/hash/seed provenance
are retained privately in the run directory; not shipped as future holdout labels.

This is a **prospective input holdout**: realizations were unseen at build freeze.
Same builder authored the protocol; familiar defect families remain familiar.
Independent labeler/native adjudication, broader legitimate negatives, native
normalization and queue grouping remain unverified. G3 is not closed. Once exposed,
these cases cannot be held-out evidence for a tuned future build. Any future tuning
requires a fresh frozen run and retention of this result, including any failures.

Local only, no push/deployment/merge, no credentials/grants/customer data, no change
to the port 8770 installation or Passal. Next reversible goal: remove manual
schema/context reconstruction from the private packet handoff, then exercise it
with the shipped guide and a timed fresh-browser rehearsal.

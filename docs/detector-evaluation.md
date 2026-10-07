# Wingman detector evaluation

Run the actual normalized-cell detector pipeline offline, before queue grouping:

```sh
python3 server/evaluate_detectors.py server/fixtures/detector-calibration.json
python3 server/evaluate_detectors.py /private/labeled-corpus.json --split held_out
```

Exit 0 means measurement completed, not targets met or release approved. Exit 2
means no score was produced. JSON reports per-kind TP/FP/FN/TN, precision/recall,
false-alarm/missed locations, sample size, p50/p95 case latency, excluded kinds,
zero Workiva requests and corpus/module hashes. No raw cell values/formulas are
exported, but identifiers and label provenance may remain sensitive. Redirect
output only to an approved private path; the command saves nothing by default.

## Corpus contract and labeling

Use the included fictional calibration file as the exact JSON contract. Each
case supplies unique ID, `calibration` or `held_out` split, bounded normalized
cells and complete `{kind, addr}` positive labels for the declared detector kinds.
All other case addresses are negatives **for those kinds**. Unscoped predictions
are counted as exclusions, not discarded invisibly or mislabeled true negatives.
Duplicate case IDs/addresses/labels and exact input leakage across splits fail.
No cases in a selected split fails; no positives or predictions never passes.

The included six cases / 18 cells are developer-authored calibration, **not an
independent or held-out evaluation**. They test error tokens, blank links, contrast
and legitimate literal-text/zero/empty/readable lookalikes. Do not use them to
claim population accuracy. A declared `independent=true` remains an unverified
provenance claim; `independence_verified` and `release_acceptance_verified` always
remain false. The command cannot authenticate a labeler or enforce organizational
independence. Exact-input split checks cannot detect every semantic near-duplicate.

Before tuning, a separate labeler must freeze supported defect families, negatives,
sample size and exclusions, label unseen fictional cases, and retain adjudication
evidence outside this builder session. Evaluation targets remain ≥95% precision
and ≥90% recall per definite-defect kind, with both positives and negatives; small
sample matches are not statistical confidence or release acceptance. Formula/source
policy judgments and vision need separate coverage. Native normalization/enrichment
and user-visible queue grouping are not measured here.

## Initial measurement — October 7, 2026

| Scoped kind | TP | FP | FN | TN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| broken-ref | 2 | 1 | 0 | 15 | 66.7% | 100% |
| blank-linked-cell | 2 | 0 | 0 | 16 | 100% | 100% |
| low-contrast | 2 | 0 | 0 | 16 | 100% | 100% |

Observed p50 0.072 ms / p95 0.322 ms per three-cell case; not Workiva latency.
Excluded five findings in three kinds: accounting-column number (2), prefix
mismatch (2), degenerate-placeholder formula (1). Literal formula `="#REF!note"`
is currently reported broken because the detector matches an error-token prefix.
This is a calibration false alarm, not a measured production false-alarm rate.
No detector was tuned to conceal it in this measurement milestone.

Evidence: `.amp/in/artifacts/detector-calibration-result.json`. Six scorer/CLI
regressions verify asymmetric precision vs recall, missed labels, empty samples,
split leakage, claimed independence and no raw-source disclosure. G3 stays open.

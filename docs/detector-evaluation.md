# Krow detector evaluation

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
was reported broken because the detector matched an error-token prefix.
This is a calibration false alarm, not a measured production false-alarm rate.
No detector was tuned to conceal it in this measurement milestone.

Evidence: `.amp/in/artifacts/detector-calibration-result.json`. Six scorer/CLI
regressions verify asymmetric precision vs recall, missed labels, empty samples,
split leakage, claimed independence and no raw-source disclosure. G3 stays open.

## Follow-up: demonstrated literal-text false alarm

A complete quoted-literal formula now proves intentional text only when its
unescaped contents match calculated readback. Nonliteral formulas, missing formula
evidence and contradictory calculated errors still surface. This changes no native
read/write route or repair capability. Four literal regressions failed before the
fix, then all 18 literal/error-token/contradiction cases passed. Detector self-checks
passed 64/64; full server suite passed **821 tests, 13 optional vision skips**.

Same frozen corpus, unchanged labels: each of the three kinds now has 2 TP, 0 FP,
0 FN and 16 TN. Broken-ref calibration precision improved from 66.7% to 100%, with
recall staying 100%; p50 0.076 ms / p95 0.235 ms on this run. Sample remains tiny,
developer-authored and used for tuning; it is explicitly not held-out or G3 proof.
Other string-producing formulas can remain judgment/false-alarm candidates; no
general string-result inference was added. Native formula/result acceptance remains
unverified. Evidence: `error-literal-red.log`, `server-tests-literal.log` and
`detector-calibration-after-literal.json` under `.amp/in/artifacts/`.

## Prospective synthetic holdout process

The unchanged detector build can now be frozen **before new case realizations**
are generated. This is a temporal input holdout, not independent human labeling,
unseen defect-family coverage or a customer/native benchmark. The same builder
authored the protocol; independence and release-acceptance flags remain false.

```sh
python3 server/synthetic_holdout.py prepare /private/new-krow-holdout
python3 server/synthetic_holdout.py run /private/new-krow-holdout
```

Commit the protocol before preparing the run. `prepare` creates a new mode-700
directory, recording exact detector/evaluator/protocol/calibration hashes and the
fixed ≥95% precision/≥90% recall targets. It creates no corpus and runs no detector.
`run` verifies the frozen inputs, claims the run once with exclusive file creation,
then draws a fresh random seed, generates 48 new synthetic mixed cases (624 cells)
and measures the actual detector. New labels come from a declared observation
grammar plus separately expressed WCAG sRGB reference—not calibration labels or
predictions. Both sides of 4.5:1 and randomized chromatic pairs are included.

The private directory retains plan, consumed marker, synthetic corpus and full
result. Exact calibration cell-pattern reuse is counted independent of addresses;
shared primitives/families cannot be called novel just because IDs changed.
Generated formulas/results are fictional observations, not executed Workiva formulas.
No Workiva calls, credentials or customer data. Report contains provenance,
counts/errors/exclusions, timing, hashes and seed; no raw cell values/formulas.

Successful, failed and interrupted attempts are **consumed**, not automatically
retried. Preserve an interrupted directory for reconciliation. A changed build,
threshold, protocol or calibration invalidates a prepared run. Once results are
exposed, they may inform calibration fixes but must never be represented as held-out
evidence for a subsequently tuned build. Prepare a new run after any tuning and
retain earlier failures. Files/hashes are not signatures; a trusted operator can
tamper, so this is process integrity under local OS trust, not provenance authentication.

The independent G3 gate still requires a separate labeler/adjudicator and unseen
negative/positive families. This process makes new frozen-build evidence possible
now without relabeling the six tuning cases as held-out or claiming independence.

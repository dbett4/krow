# Wingman reporting context — October 7, 2026

Goal: arithmetic-green CSV evidence cannot hide a mismatched reporting period,
currency or row unit. Unknown units/basis cannot become a context match.

Implemented explicit reviewer-declared period/currency/unit/amount/basis policy,
bounded row findings, separate matched/failed/incomplete states, unscaled totals,
version 3 offline replay with context build hash and native-schema composition.
Existing Lockfield type/arithmetic checker is unchanged. No accounting approval,
fiscal calendar, FX, mapping/sign inference or Workiva mutation added.

## Executed proof

- Full server suite: **797 passed, 13 optional vision skips**.
- Real Chromium UI: explicit controls → keyboard check → actual download → CLI
  replay; policy edits invalidate evidence; clearing removes policy; narrow dark
  and desktop rendering captured and inspected.
- Independently specified asymmetric regression: `1001 + (-2) = 999` cents remains
  exactly 999, not scaled. Replacing only second record's labels with wrong period,
  EUR and units yields exactly three context findings at record 3 while arithmetic
  remains passed. No observed EUR/source row exported.
- Missing/ragged/duplicate-header binding, malformed policy, case/whitespace,
  issue truncation, unknown basis/unit binding and edited packet/build cases covered.
- Opt-in acceptance rerun against actual synthetic native table using the current
  service on 8783. Matched period/currency with absent row-unit column remains
  incomplete. Wrong-period/currency input fails. Version 3 native packet replays.
  Fingerprint remains `3563367713cdb0ea0ebab70fbb99c511902973204e933d5fd126e7b901dabcde`.
  No new table, schema write or dataset import needed.

Commands:

```sh
python3 -m pytest server/ -q
python3 -m pytest scripts/test_csv_review_browser.py -q
python3 scripts/csv_native_acceptance.py --port 8783 \
  --out .amp/in/artifacts/native-context-final
```

Private synthetic evidence: `server-tests-context.log`,
`native-context-final/receipt.json` and packets;
`context-browser-final/test_csv_review_browser0/` includes inspected default,
matched, mismatch, narrow-dark mismatch and incomplete screenshots.
Initial visual review caught a zero arithmetic-only issue counter beside three
context mismatches; it was corrected, regression-checked, recaptured and inspected.

## Boundaries and next goal

Policy is a declaration, not source authority. Amount labels may still be wrong
in the source; accounting basis is recorded, not evaluated. Original native/import/
accounting/period-and-unit authority flags remain false. Monthly label checks do
not close full accounting semantics or G1–G7.

Next selected goal: repeatable detector evaluation with explicit corpus/split/label
provenance and per-detector counts, false alarms, omissions and latency. Existing
regressions and fictional Riverton fixtures are developer-authored, not independent
held-out labels. Implement the measurement route without claiming G3 acceptance;
separate independent adjudication remains required before tuning/release claims.
Durable review decisions, clean-machine pilot and concurrency-safe actions remain
following goals. No push, deploy, merge or port 8770 change authorized/performed.

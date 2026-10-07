# Wingman private CSV review: October 7, 2026

## Scope and outcome

Owning repository: `https://github.com/dbett4/wingman`, safely cloned to
`/srv/agentops/repos/wingman`, branch `wingman/csv-review-20261007`.
Baseline remote main: `7f31318a4fedcf9e6880ae7516f0ad6e1df45cb5`.
Changes remain local/uncommitted, not pushed, deployed or publicly published.
Passal, the separate plugin checkout, private grants and port 8770 are untouched.

Three bounded goals: real CSV → review → explicit packet; downloaded packet →
offline reproduction; private bundle → fresh-extraction runtime smoke. The actual
plugin checker and its 40 tests were reused, not reimplemented. See
[inventory and roadmap](../product-development.md) and [operator guide](../csv-review.md).

## Executed checks

| Check | Result |
| --- | --- |
| `python3 -m pytest server/ -q` | 772 passed; 13 optional vision tests skipped, not claimed as covered |
| `python3 -m pytest server/test_csv_checks.py server/test_csv_review.py -q` | 64 passed, including inherited checker cases, real HTTP guards, packet tampering and CLI status |
| `AGENT_BROWSER_ENGINE=chrome python3 -m pytest scripts/test_csv_review_browser.py -q` | Real Chromium/HTTP/keyboard/download/replay, recovery and narrow/light/dark checks passed |
| Existing demo browser suite | 4 passed against simulated upstream; not live Workiva acceptance |
| Existing extension tests | 397 content checks, 6 background tests and 3 setup tests passed |
| `node --check extension/csv-review.js`; `git diff --check` | Passed |
| Local HTTP performance | 40 calls, 1,000 rows, two columns: p50 7.011 ms, p95 9.874 ms against predeclared 250 ms target; not browser or Workiva latency |

Evidence lives in repository-local `.amp/in/artifacts/`, excluded from Git:
`server-tests-final.log`, `extension-tests.log`, `demo-browser.log`,
`csv-local-benchmark.json`, final Chromium PNGs, bundle and smoke log.
Captures cover default, findings, supported pass and recoverable malformed CSV;
findings are also checked at 390 px and in dark mode. The final malformed state
retains inputs, disables evidence and gives quote/header/re-export guidance.
Visual inspection is builder review, not an independent release adjudication.
The provenance packet records this remaining gate rather than inventing a verdict.

## Reproduce the bounded private bundle

From this checkout, create a private artifact (no credentials/configs included):

```sh
zip -X .amp/in/artifacts/wingman-csv-review-private.zip \
  server/csv_review.py server/csv_checks.py \
  server/test_csv_review.py server/test_csv_checks.py \
  extension/csv-review.html extension/csv-review.css extension/csv-review.js \
  extension/setup.css extension/icons/icon128.png \
  scripts/test_csv_review_browser.py docs/csv-review.md \
  docs/product-development.md docs/roadmap.md docs/receipts/csv-review-20261007.md
sha256sum .amp/in/artifacts/wingman-csv-review-private.zip
```

Extract into an empty private directory. Python 3.11+ runs the service without
dependencies: `python3 server/csv_review.py --port 8781`. Follow the operator guide
for exact loopback/SSH access. Tests additionally need pytest; browser tests need
agent-browser and Chromium. Stop this disposable service with Ctrl+C. No system
service installation or production switch is implied.

Fresh-extraction acceptance: all five declared assets return 200 with their expected
types; a real request with `0.10` and `-0.03` returns exact complete total `0.07`;
saved packet and original CSV replay with exit 0. The smoke process is stopped and
its temporary extraction removed. Bundle hash and executed result are retained in
`csv-bundle-smoke.log` and `wingman-csv-review-private.zip.sha256`.

## Remaining risks and next decision

- This is a useful private local screen, not a full customer-ready Workiva product.
- Schema is caller supplied; periods, units, accounting, authorship and native
  import are unverified. Partial/unknown checks cannot become accounting approval.
- Loopback trusts local OS users; no hosted customer authentication or secure
  memory erasure. Explicit packets remain sensitive, unsigned user-managed files.
- No current native schema/API acceptance, clean-machine pilot, independent visual
  adjudication or independently labeled held-out detector evaluation is claimed.
- The public Lockfield page is discovery material. Prepared host assets do not prove
  a public connector; observed DNS/installation checks did not establish one.

Next measurable goal: authorize one synthetic Wdata table and read-only grant,
then bind its native schema identity/revision to this exact review flow; exercise
unauthorized and stale-schema failures and compare packet evidence to native
readback. Any credential/security change, live release or public publication needs
its own explicit authority. Keep production repairs disabled until approval,
conditional-write/readback and recovery gates are accepted.

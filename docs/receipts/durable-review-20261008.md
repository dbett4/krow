# Wingman durable review — October 8, 2026

Goal: preserve explicit evidence-bound decisions across restart without hiding
findings, promoting accounting authority, or resolving unvisited evidence.

Implemented an opt-in owner-only SQLite journal in the existing CSV workflow.
Default mode remains storage-free. Scope/identity are declarations, not authenticated
Workiva/reviewer identities. Reasons, locations and hashes are sensitive. Acceptance
is an exception decision only. Raw CSV is not retained; source authority is external.

Proof commands:

```sh
python3 -m pytest server/ -q
python3 -m pytest scripts/test_durable_review_browser.py scripts/test_csv_review_browser.py scripts/test_csv_bundle.py -q
node --check extension/csv-review.js
```

Result: **832 server tests passed, 13 optional vision tests skipped**; all four
real HTTP/restart/Chromium/isolated-bundle tests passed. JavaScript syntax and
diff-whitespace checks passed. This is builder verification, not independent
private-release acceptance.

Focused proof covers actual SQLite/process restart, exact-run/evidence/revision and
ten-minute expiry, simultaneous confirmation (one receipt), changed relevant values
and native binding, unchanged unrelated values, workspace/copy/period separation,
complete disappearance/recurrence, partial/truncated/unknown-context evidence, private
permissions and corrupt/foreign database preservation. HTTP denies cross-origin
confirmation. Chromium covers accept/reopen, actual response loss after commit then
history reconciliation, explicit handoff download, fresh-check vs historical forms,
input invalidation and incomplete coverage. No Workiva writes are performed.

Screenshots are under `.amp/in/durable-proof/` and the final rerun under
`.amp/in/durable-final/`; desktop accepted and narrow-dark historical/changed/partial
states were inspected with vision. Original findings/partial totals stay visible;
accepted decisions show reasons, fresh unchecked confirmation belongs to a future
decision, history is non-actionable, and unvisited findings remain unresolved.
Handoff button spacing was improved after inspection and recaptured.

Remaining gates: second reviewer must understand a handoff unaided; identity and
declared policy are not independently authenticated; snapshots are not signed;
retention is indefinite/operator-controlled; record ordinals reopen on movement;
no hosted tenancy, automated retention, native repair, or independent G4 acceptance.
Native freshness is not concurrency control. Port 8770 and installed release remain
unchanged. Local milestone only; no push, merge or deployment.

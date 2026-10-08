# Wingman private readiness — October 8, 2026

## Timed isolated setup and recoverability

Added actual extracted-bundle journal onboarding/restart/backup-readback proof to
`scripts/test_csv_bundle.py`. Both bundle tests passed. Existing VPS; empty HOME,
minimal PATH, Python `-S`, no credentials or wk available to the extracted runtime.

Measured initial run: extraction 0.082 seconds; actual CSV inspection by 0.341
seconds; entire confirm/restart/restored-backup readback sequence 0.593 seconds.
Three startup observations: 0.252, 0.101, 0.101 seconds. Sample is three process
starts, not a population latency benchmark or a human time-to-value study.
Exact asymmetric total 99.99, one retained accepted exception/reason, stale replay
rejection and absence of native configuration were verified. Backup was copied only
after stopping the disposable preview, into a distinct mode-700 directory/mode-600
file; original remained unchanged. Machine-readable result:
`.amp/in/timed-onboarding/test_timed_isolated_journal_on0/timed-onboarding.json`.

This is a timed dependency-isolated smoke, **not** an independent clean-machine
reviewer or native-import acceptance. The guide now defines the ≤10-minute unaided
reviewer acceptance flow and exact evidence to collect. Private-release acceptance
and security/visual/handoff independence remain open. No installation/deployment.

## Independent detector evidence inventory

Scoped Wingman fixtures/docs/retained artifacts and original Lockfield plugin
tests/docs/work review evidence were inspected. Only the developer-authored
`server/fixtures/detector-calibration.json` was recovered: six cases/eighteen cells,
all calibration, `independent=false`, used for tuning. Riverton is seeded demo
material, not accuracy evidence. Original plugin `work/release-v040/20261002-review.md`
records separate adversarial review, not a labeled held-out accuracy corpus;
`docs/public-release-review.md` records hosted reviewer cases as not run.
No recovered qualifying held-out corpus in these scoped sources. A separate
labeler must freeze unseen synthetic positives/negatives and adjudications before
evaluation. Do not manufacture independence by splitting existing developer labels.
G3 remains open; targets stay ≥95% precision and ≥90% recall per definite-defect kind.

## Native mutation concurrency remains unproven

Live adopted `wk -w lsl-account whoami` proved the existing LSL account; exact GET
of retained table `0f618794c8374c8fa18f872158f058ed` proved unshared synthetic name,
version 3, unchanged description, updated `2026-10-07T22:59:07Z`. No customer data,
new table, datasets, grant changes or native mutation in this follow-up.

The actual native snapshot was also passed through `bind_packet` into the new local
journal using a fictional integer/key case: subtotal 999, explicit invalid-value
exception, one confirmed receipt and readback after reopening the database succeeded.
Native fingerprint remained `3563367713cdb0ea0ebab70fbb99c511902973204e933d5fd126e7b901dabcde`.
Evidence: `.amp/in/native-journal-proof/receipt.json`; zero native writes and import/
approval flags false. This proves native-read-bound local decisions, not native
repair or a collaborator-concurrency guarantee.

The earlier actual description write/readback/restore established that version 3
did **not** change. A metadata fingerprint/read-before-write cannot exclude a
collaborator edit between read and write, nor make rollback conditional. Local
SQLite serialization protects local decisions only, not Workiva collaborators.

Adopted API-reference search returned Platform PATCH `/content/tables/{tableId}/properties`
and general Platform JSON-Patch `test` documentation. These are not the Wdata
`/table/{id}` update route; they cannot be imported as Wdata CAS guarantees.
The current adopted `wk raw` CLI exposes no caller-specified conditional headers.
The live public [Wdata update reference](https://developers.workiva.com/wdata-v1/wdata-updatetable.html)
was retrieved directly after external search was unavailable. Its PUT parameters
list only tableId and TableDto; the documented body has no version/precondition
field or conditional header. It warns that omitted user-defined columns can be
deleted from an empty table. This is not a safe place to infer undocumented guards.
No authoritative native Wdata conditional-write contract or acceptance proof was
recovered; absence of documentation is **not** a claim that Workiva has no such
feature. Do not experiment by weakening the write guard. The extracted-bundle test
verifies apply/import/undo/approve paths all refuse, even with `confirmed=true`.

Next safe action: obtain the endpoint-specific atomic precondition contract and
prove stale write/conditional restoration against this exact sandbox before adding
any enabled native action. Alternatively obtain an explicit read-only private-release
scope decision. Until then the CSV candidate exposes no native apply/import/undo
API. Readback and receipts are necessary but not substitutes for concurrency safety.

Port 8770 service remains active PID 1235 at retained release
`/opt/wingman/releases/0ee4f35957a0c53661dd1feffe8a76ca5aae2b85`.
All work is local; nothing pushed, merged, deployed or published.

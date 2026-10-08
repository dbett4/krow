# Wingman setup capabilities and integration — October 8, 2026

## Measurable improvement

Default setup previously offered native loading even with no sandbox configured.
The action is now disabled until local configuration explicitly enables it.
Configuration advertises no access verification or mutation authority. Configured
does not mean credentials work; an explicit schema load remains required. A bounded
configuration failure leaves loading/journaling unavailable, with recovery guidance
and local arithmetic checks still usable.

Real HTTP tests cover exact default/configured capabilities and no implicit native
read. Chromium tests exercise unconfigured, configured-but-unverified and HTTP 503
outage states; actual local inspection still returns partial subtotal 1200.15 during
the outage. The configured browser case uses only a constructed fictional table ID,
never loads it and never invokes Workiva. Initial focused run: 37 tests passed.
Rendered captures inspected: `.amp/in/capability-proof/test_native_configuration_and_0/`.
Independent visual/security/unaided-human acceptance remains open.
The validated visual packet `.amp/in/configuration-vision-review-packet.json` is
explicitly **advisory**, not independent release acceptance. Combined explicit-
Chromium verification subsequently passed 851 tests / 13 optional skips, including
the complete server, CSV bundle/browser/journal/pilot and legacy demo workflows;
`git diff --check` passed. Proof: `.amp/in/configuration-final/`.

## Authoritative endpoint investigation

Fresh public references fetched October 8 (no credentials or native requests):

| Endpoint | Evidence | Conclusion for Wingman repair |
| --- | --- | --- |
| Wdata PUT `/api/v1/table/{tableId}` | Previous exact-table write/readback/restore and public Wdata update reference | Version did not advance; no proven atomic precondition or conditional restore. |
| POST `/spreadsheets/{spreadsheetId}/sheets/{sheetId}/update` | [Current sheet update reference](https://developers.workiva.com/2026-01-01/updatesheet.html) | X-Version is API version, not resource revision. Parameters provide SheetUpdate, not a documented conditional-write contract. |
| POST `/content/tables/{tableId}/edit` | [Current table edit reference](https://developers.workiva.com/2026-01-01/tableedit.html) | X-Version is API version; asynchronous edit/polling does not establish CAS or safe conditional restoration. |
| PATCH `/content/tables/{tableId}/properties` | Adopted endpoint reference and general JSON-Patch guide | `test` supports conditional property patches; cannot transfer that guarantee to Wdata or sheet formatting. |

Fresh HTML SHA-256: sheet update
`3016df1597db06f2caf5f0c935b9e10c97ed90db73574a4034559e208cfbfc67`;
table edit `331939c6db5b30d22dd4a87fcecda84a6c66e1271bc6c497f22e2c0ad462a1ed`.
Sources retained under `.amp/in/updatesheet-current.*` and `.amp/in/tableedit-current.*`.
Absence of documentation does not prove Workiva has no conditional-write feature.

Actual legacy `server/fixer.py` formatting writes use the sheet-update route.
Contrast repair reads effective color, writes and reads back, then compensates by
unconditionally writing the previous effective color or explicit black. That does
not preserve an inherited/absent format or exclude collaborator races; its local
revert success is not restoration readback proof. Existing safeguards against lossy
scale changes remain valuable, but do not establish general native concurrency.
Do not enable legacy mutation as a workaround. The CSV candidate has no native
write routes, and the installed backend remains read-only and untouched.

## Authorized source integration

Dave subsequently authorized push and merge, not deployment. The clean feature
branch `wingman/csv-review-20261007` was pushed and default `main` safely fast-forwarded
through [the handoff commit](https://github.com/dbett4/wingman/commit/adce684dd3a936831d69265fad1b325f6fb814d5).
Fetch/readback matched both remote refs to local HEAD. No branch protection/PR
requirement; existing CI workflow only tests, with no deployment trigger.
[GitHub CI passed](https://github.com/dbett4/wingman/actions/runs/37729243126).
Post-integration: 845 tests passed / 13 optional skips, 397/397 extension checks.
Additional demo tests initially failed with unspecified browser engine; all four
passed explicitly in Chromium without code or assertion changes.

Port 8770 remained active PID 1235 at retained runtime
`/opt/wingman/releases/0ee4f35957a0c53661dd1feffe8a76ca5aae2b85`.
No grant, production/customer data, native mutation, merge-history rewrite or
deployment changes. Next acceptance needs independent unseen labels, a timed
unfamiliar reviewer and an endpoint-specific atomic write/conditional-restoration
contract before any repair can be enabled.

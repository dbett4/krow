# Wingman: product direction and development record

October 7, 2026. This extends, rather than replaces, the seven private-v1 gates in
[the existing roadmap](roadmap.md). None of those gates is closed by a local test.

## Target user, job and thesis

The primary user remains the financial-reporting reviewer responsible for a
Workiva workbook and its supporting data. The core job is to understand a reported
value, find missing or contradictory evidence, and leave a review another person
can reproduce. The first added workflow serves the same reviewer before a Wdata
load: screen an explicit CSV against an explicit expected schema.

**Thesis:** review quality improves when observations, unknowns, approval and
execution proof remain separate. Wingman should reduce the work of finding the
next justified action, not issue an unsupported “report ready” certificate.
Time savings and willingness to pay are hypotheses until a measured pilot.

## Actual source and deployment inventory

| Surface | Source / observed state | Reuse decision |
| --- | --- | --- |
| Wingman | `https://github.com/dbett4/wingman`, cloned to `/srv/agentops/repos/wingman`; starting remote main is `7f31318a4fedcf9e6880ae7516f0ad6e1df45cb5` | Owning product repository; existing Python service, Chrome panel, inspector, setup, detectors, guarded fixer, packets and tests retained |
| Wingman deployment | Fresh read-only check: `wingman-readonly.service` active/running, PID 1235; `/opt/wingman/current` points to release `0ee4f35957a0c53661dd1feffe8a76ca5aae2b85` | Existing port 8770 service preserved; no restart, installation, scope or credential change |
| Lockfield Workiva Plugin | Clean local Git main at `/home/dave/work/design-venture/lockfield/workiva-plugin`, commit `19376f7`; no Git remote configured; retained worktrees contain earlier feature/release branches | Production-oriented private MCP code: actor/tenant/connection scope, OAuth/PKCE, one-use proposal approvals, native schema-backed CSV screens, diagnostics and synthetic tests. Not evidence of public acceptance |
| Lockfield page | `https://lockfield.co/workiva-plugin/`, fetched October 7 with curl | Marketing/discovery page, explicitly private-pilot; not a running connector. FAQ says hosted ChatGPT and directory availability pending |
| Adopted website | `/home/dave/work/design-venture/lockfield/f2-identity-20261007/`, source lineage at `/home/dave/work/worktrees/lockfield-f2-identity-20261007` | Existing Astro/Cloudflare Pages website and artwork; not copied into Wingman. Latest adoption is a memory pointer, not freshly proven deployment ownership |
| Hosted plugin candidate | `deploy/`, `public-release/`, and `docs/public-host-preflight.md` in the plugin repository | Prepared read-only host and export assets; `mcp.lockfield.co` failed DNS lookup, Lockfield service inactive, expected local host install path absent at discovery. Do not claim a public deployment |
| Plugin live evidence | `docs/live-acceptance-2026-10-01.json` and write record alongside | Historical scoped reads, synthetic-file cell write/rollback and plain-text insertion. Query/refresh/Chain execution and v0.4 CSV workflow need current native acceptance |
| Regulated Reporting MCP | `/srv/agentops/repos/regulated-reporting-mcp`, separate GitHub repo with extensive uncommitted workbench changes | Related but separately owned; no changes or uncommitted work imported |
| Demo/portfolio | Wingman `demo/`, fictional Riverton fixtures; portfolio `dbett4/davebettner.com` | Demo exercises actual product modules with simulated upstream. Portfolio is evidence commentary, not product code or proof of current accuracy |
| Passal | Initial runner directory only | No Passal changes; not a Wingman source |

Recovered history: the prior Wingman implementation thread identifies
`/home/dave/work/wingman-inspect-20260915`; that path was absent at discovery.
Published GitHub history preserves the work, and the deployed snapshot survives.
Do not conclude that work was lost or recreate its inspector/setup/coverage flows.

## Naming and asset decisions

Product: **Wingman**. Descriptive integration name: **Lockfield Workiva Plugin**.
Existing Wingman manifest uses “Wingman” and “Wingman for Workiva”; its cobalt
wing icon, graphite/light surfaces and system typography remain the UI source.
Plugin package identity is `lockfield-workiva`; listing/brand docs use “Lockfield
for Workiva” and “Lockfield for Workiva — v0.4.0”. The live page says “Workiva
plugin”. These inconsistencies are recorded, not silently mass-renamed. Keep
machine identifiers, SSH bindings, OAuth audiences and shipped metadata stable
until an explicit compatibility-aware integration release.

UI survey: reused Wingman's own `extension/setup.css`, button primitives, native
form controls and licensed repository icons. The existing panel is appropriate
for in-editor review; the setup-page layout is appropriate for a private CSV tool.
No React/component registry, new brand, illustration or marketing mockup is needed.
Lockfield's sienna logo is not substituted for Wingman's established wing.

## Trust model

- Existing live deployment stays scoped/read-only. No client files are touched.
- Default CSV review uses caller-supplied schema with no Workiva requests. Optional
  native mode explicitly reads one configured private synthetic LSL table through
  the existing wk grant and rereads its schema/timestamp fingerprint on check.
  Observation is not native import acceptance; neither mode approves or alters data.
- Findings, exact valid-value totals, incompleteness and unknowns remain visible.
  A partial total is never labeled a complete column total.
- Reporting context is optional reviewer-declared policy. Row period/currency/unit
  mismatches override arithmetic-green UI; absent unit binding or unknown basis
  stays incomplete. Matching labels is not accounting correctness or approval.
- Local packet is unreviewed and binds input/schema/validator hashes and UTC time;
  it is neither signed attestation nor native execution proof. Hashes of predictable
  inputs are not anonymization. Column names and totals remain sensitive.
- No raw inputs persisted or logged by this tool; browser/process memory and OS
  swap are not secure erasure. Explicit downloads belong to the user. Local OS
  users are trusted; loopback/origin guards are not multi-tenant authentication.
- Live mutations remain blocked until exact human approval, stale-precondition
  checks, one-use execution, native readback and concurrency-safe recovery are
  accepted for that action. Neither this milestone nor plugin synthetic tests
  authorize enabling Wingman repairs in production.

## Phased roadmap and measurable goals

| Phase | Goal / acceptance metric | Gate |
| --- | --- | --- |
| 1. Private pre-import review | Run real supplied CSV through the existing validator; all 40 inherited cases plus real HTTP/UI/export/recovery checks pass; no Workiva requests, no retained raw rows, no stale downloadable results | Local milestone; not public SaaS or closure of G1–G7 |
| 2. Native schema-backed review | In one explicitly approved synthetic Wdata table, use existing plugin read policy to fetch schema; reject unauthorized tables before HTTP; bind native IDs/revision/evidence to packet; compare known type/header/key cases and stale schema cases | Approved grant/sandbox and accepted identity/topology; no credential or production-security changes implied |
| 3. Findings earn trust (G3) | Independent labeled lookalikes + held-out corpus; ≥95% precision and ≥90% recall per definite-defect detector, with sample counts, exclusions, false alarms, latency and API budget | Separate labeler/reviewer; thresholds fixed before tuning. Do not self-label then claim independence |
| 4. Durable review (G4) | Restart retains decisions; changed evidence reopens only affected exceptions; partial scan never resolves unvisited findings; second reviewer understands handoff unaided | Stable scope/finding identity, retention and recoverable private storage |
| 5. Supportable private release (G1/G6/G7) | Provisioned new reviewer reaches real inspection within 10 minutes from guide; install/update/rollback and offline/reload/access-expiry recovery pass; p50/p95 on declared sample | Clean-machine and authorized sandbox proof, separate security/visual review, owner acceptance |
| 6. Proven actions (G5) | Every enabled action survives expiry, double apply, timeout after commit, restart and collaborator edits; requested result/restore verified without overwriting newer work | Workiva conditional-write proof or explicit read-only release decision. Public hosting/store/billing remain separate scope |

## Hill-climbing record

**Goal 1 selected:** make the existing plugin CSV screen usable by a reviewer without
an MCP host, model, credentials or a synthetic result stub. This is a bounded
extension of existing capabilities, not another spreadsheet QA engine.

**Implementation:** copied the existing deterministic checker and all 40 tests;
only import/error adaptation and provenance header changed. Reused Wingman identity
and setup CSS for input → schema → check → findings → explicit JSON download.
Added a separate standard-library loopback entry point, exact Host/Origin checks,
bounded input, no-cache/CSP, no logging/storage and cancel/stale-result handling.

Results and final proof commands are recorded in `docs/receipts/csv-review-20261007.md`.

**Goal 2 selected and implemented:** let a second reviewer reproduce a downloaded
packet using the original CSV without reconstructing the schema. Packets now carry
the declared schema and key policy; the offline replay command checks exact results
and trust claims, distinguishes mismatch from invalid input, and exposes no source
values in its output. Browser download → CLI replay and altered-source/schema/result/
trust-claim tests pass. Replay explicitly does not authenticate authorship, timestamp
or approval.

**Goal 3 selected:** make the private CSV slice portable without credentials or a
running extension backend. A scoped ZIP includes only its runtime, existing Wingman
CSS/icon, tests and guides. Acceptance is a fresh extraction that serves all assets,
checks an asymmetric decimal input and replays the resulting packet. This is a local
packaging smoke, not a clean-machine customer pilot or public release.

**Goal 4 implemented:** native schema-backed review against one approved private
synthetic Wdata table. Actual schema reads, asymmetric 999-total/key/type cases,
metadata change → stale rejection → restore/readback and offline replay passed.
780 server tests passed with 13 optional vision skips; default Chromium flow and
native load/keyboard/download/reset plus desktop/narrow-dark inspection passed.
Native version was not a revision counter; fingerprint also binds updated/schema.
See [native acceptance receipt](receipts/native-schema-20261007.md). This is the
bounded native observation slice, not complete phase 2/import acceptance or G1–G7.

**Goal 5 implemented:** explicit reporting-period/currency/amount-unit and declared
accounting-basis context. Wrong-period/mixed-currency/unit labels fail independently
of exact arithmetic; absent row-unit binding or unknown basis stays incomplete.
Source units remain unscaled; packet version 3 replays context and native binding.
797 server tests/13 optional skips, actual native-bound context acceptance and
Chromium input/export/replay/invalidation plus inspected desktop/narrow-dark states
passed. See [reporting context receipt](receipts/reporting-context-20261007.md).
Fiscal-calendar/FX/mapping/basis correctness is not implemented or claimed.

**Goal 6 implemented:** repeatable offline detector measurement with explicit label
provenance/split, TP/FP/FN/TN, precision/recall, false-alarm/missed locations, excluded
kinds, latency and build/corpus hashes. Six developer-authored cases/18 cells found
a literal-error-text false alarm: broken-ref precision 66.7%, recall 100%. Other
two scoped kinds matched the small sample, not population/independent accuracy.
803 server tests passed/13 optional skips. See [evaluation guide/results](detector-evaluation.md).
No independent held-out labels recovered; G3 remains open.

**Next goal:** eliminate the demonstrated explicit-literal false alarm without
hiding genuine error tokens, then implement durable evidence-bound review decisions.
Independent labels and clean-machine proof remain gates. Dave authorized LSL
sandbox and local commits only. No push, deployment, merge or change to port 8770
is authorized. The installed read-only service is unchanged.

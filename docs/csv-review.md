# Wingman CSV review

This private read-only tool screens a real CSV against an explicit schema. Default
mode does not connect to Workiva. An optional operator-bound LSL sandbox mode reads
one synthetic table's native schema; neither mode uploads or changes Workiva data.

## Run and use

From the Wingman checkout on the VPS:

```sh
python3 server/csv_review.py --port 8781
```

Default mode: Python 3.11+; no pip install, credentials or model required. Open
`http://127.0.0.1:8781` in a browser on the VPS. A remote control terminal may use
its existing verified SSH route: `ssh -N -L 8781:127.0.0.1:8781 davgent`, then open
that exact loopback address. This forward is transport only; no Mac production
backend. Port 8770 and the installed extension are unchanged. Do not expose this
unauthenticated tool on a public interface or reverse proxy.

1. Try the fictional example to learn the flow, or choose/paste an approved UTF-8
   CSV. File selection reads locally; **Check CSV** sends it to the VPS process.
2. Declare exact column names, order, expected types, required flags and up to
   eight key columns from your approved schema. Nothing is inferred.
3. Run the check. The example has three data records, two issues at record 4 and
   exact valid-value subtotal `1200.15`, explicitly partial.
4. Review affected records (header = record 1), physical line endings, duplicate
   first occurrences and complete/partial totals. Quoted multiline records mean
   record number is not physical line number.
5. Correct your source outside Wingman and recheck. Any input edit clears earlier
   evidence and disables download. Choose **Download review evidence** explicitly
   to retain the JSON packet; it remains unreviewed, not accounting approval.
6. Clear inputs when finished. Stop with Ctrl+C. Default mode forgets all review
   data on restart; the explicitly enabled journal described below persists.

## Durable private review decisions (opt-in)

Create a new owner-only directory on the VPS and explicitly enable a journal:

```sh
mkdir -m 700 /private/wingman-review
python3 server/csv_review.py --port 8784 --review-db /private/wingman-review/review.db
```

Do not reuse an unrelated SQLite database. New journals are mode 600; unsafe paths,
corrupt files and unrelated databases fail closed without overwriting them.
Default mode still creates no database. The journal is not a hosted or authenticated
team database. Local OS users and the operator remain trusted.

Choose **Save this check and its review decisions**, then declare separate workspace,
file-copy and reporting-period labels. These are not authenticated Workiva IDs.
Run a fresh check. Each current finding offers **Accept exception** or **Reopen
exception**, requiring a reviewer label, reason and explicit evidence-only
confirmation. Reasons must not contain source values. Acceptance does not hide
findings, change arithmetic, approve accounting or authorize a Workiva write.
The UI reads back the committed decision; a fresh unchecked confirmation applies
to the next decision, not the already saved one.

Decisions bind scope, record ordinal/column, finding code, relevant value evidence,
schema/key/context/checker policy and native binding. Changing relevant evidence
reopens the affected exception; unrelated values preserve it. Row movement can
reopen ordinal identities. A complete subsequent check may mark absent findings
resolved under its **current declared policy**, not prove source correctness.
Ragged, unknown-type, unusable-header, missing-data or truncated evidence does not
resolve unvisited findings. Recurrence opens again. Scope/file-copy/period changes
never inherit acceptance. Confirmations expire after ten minutes or another saved
check/decision. SQLite transactions serialize competing confirmations; one commits.

**Load saved review** is historical and read-only in the UI. Supply the source and
run a fresh saved check before deciding. **Download saved review handoff** explicitly
exports scope, latest source hash/time/coverage, finding hashes/currentness/states
and the latest 200 decision events with total count/truncation. The original
arithmetic packet remains separately downloadable and unreviewed. Keep the original
source and declared policy with their source owner; hashes cannot reconstruct them.
No raw CSV is stored, but scope/reviewer/reason/location and hashes can be sensitive.
Reviewer identity, authorship, source authority and approval are not authenticated.

If a confirmation times out or its response is lost, do not blindly confirm again:
load history and reconcile the finding/revision/reason, then perform a fresh check.
Storage failure claims no success. Restart retains confirmed history. **Clear inputs**
does not delete the journal. Retention is indefinite until the operator chooses
otherwise; no automatic retention policy or secure erasure is claimed.

For backup/recovery, stop only this private preview, copy its database into an
owner-only backup directory, record a SHA-256, then restart the same retained
runtime. Verify saved scope/history through the UI. Restore only into a separate
private directory, compare the hash and test readback before adopting it; never
overwrite a live journal or foreign database. Keep the previous database/runtime
unchanged for reversal. Do not delete non-disposable review data without explicit
owner instruction. This milestone does not include schema migrations or native
repair execution. Separate reviewer handoff acceptance remains open.

## Private portable bundle and rollback

From the source checkout, build a **new** private ZIP path in an existing directory:

```sh
python3 scripts/build_csv_review_bundle.py /private/wingman-csv-review-v3.zip
python3 -m pytest scripts/test_csv_bundle.py -q
```

The builder uses a fixed allowlist, reproducible ZIP metadata and refuses overwrite.
It prints SHA-256; compare the hash through your trusted private handoff channel
before extraction. This hash is not a signature. No credentials, local configs,
customer data or installed-service files are included. The bundle contains only
the CSV runtime/native-schema/context modules, assets, scoped tests and guides,
not the full inspector or detector evaluator runtime.

Extract into a new private directory on the VPS, then run
`python3 server/csv_review.py --port 8781` (select a free loopback port).
Do not replace the port 8770 installation. Default mode needs
Python 3.11+ only. Native mode separately needs the already authorized wk grant;
the ZIP does not provision or expand it. Use the fictional example before approved
source data. Keep an older bundle/service directory unchanged for rollback: stop
only your new preview, rerun the retained older directory on its private port and
recheck source inputs. No database migration or Workiva mutation is involved.

The automated smoke uses a fresh extraction, empty home/minimal environment,
Python `-S` (no site packages) and no wk on PATH. It checks all assets, absent native
configuration, exact 999 total, reporting policy and offline packet replay. This is
an isolated dependency/onboarding smoke on this VPS, **not a clean-machine reviewer
pilot, authenticated hosted product or approved private release**. A new reviewer
still needs independent timed install/access/recovery and owner acceptance.

The timed journal smoke also measures extraction → actual inspection, then confirms
an exception, restarts the extracted runtime, and verifies a separately restored
owner-only backup. It runs without site packages, credentials or wk on PATH and
emits `timed-onboarding.json` under pytest's result directory:

```sh
python3 -m pytest scripts/test_csv_bundle.py -q --basetemp=/private/new-onboarding-proof
```

Use a **new disposable** basetemp path: pytest may remove an existing directory.
This measures automated setup, not human onboarding or a native grant. Native access
without a configured grant fails closed; the smoke never provisions credentials.

For independent private acceptance, give a new reviewer the trusted bundle/hash,
this guide and a synthetic source, but not developer assistance. Time from extraction
through inspecting actual records; require ≤10 minutes. Have them explain partial
totals and non-approval limits, accept/reopen an exception, restart/read saved history,
reconcile an uncertain confirmation, replay the arithmetic packet, and recover a
copy of the journal into a separate private directory. Record host/browser/Python,
candidate hash, start/end times, assistance, failures and recovery outcomes. For
native acceptance use only the existing authorized LSL synthetic table/grant on the
VPS; do not copy credentials or use customer data. A reviewer who built this candidate
cannot supply the independent acceptance. No timed human result is claimed yet.

## Native LSL sandbox schema

Dave authorized the existing LSL sandbox grant, not customer production or broader
grants. The scoped acceptance table is `0f618794c8374c8fa18f872158f058ed`, named
`zz Wingman Synthetic CSV Acceptance 20261007`. It contains no imported datasets.

```sh
python3 server/csv_review.py --port 8782 \
  --sandbox-table 0f618794c8374c8fa18f872158f058ed
```

This profile additionally requires the adopted `wk` command and its existing LSL
read grant on the VPS. Do not copy credentials into Wingman, the browser or a bundle.
Use exact loopback port 8782 (or an approved SSH forward) as above.

Open **Optional native LSL sandbox schema**, then **Load configured sandbox schema**.
Wingman proves the account through `wk`, reads only the configured ID, checks its
native account/table binding and unshared synthetic name, and locks the schema.
Key policy is still explicit. Each check rereads the schema and compares its full
fingerprint, native `updated` field and `version`; changed evidence requires reload.
The native `version` remained 3 across an actual update, so it is **not an optimistic
concurrency counter**. This workflow enables no Workiva writes.

Wdata supplies four managed columns. This bounded full-schema screen includes them
in exact header order; it does not infer an import-column mapping or hide them. The
acceptance CSV has `record_id,amount_cents,period,currency,_tags,_filename,_timestamp,_userid`,
with the managed fields blank. `mode=required`/`nullable` maps explicitly; unknown
modes/types remain unsupported. Native `float` is not silently treated as decimal.
`amount_cents` totals are integer source units, never automatically scaled to dollars.

Native packets use version 2 and retain the observed binding and fingerprint.
Offline replay checks their internal consistency, not a fresh live schema, authorship
or native import acceptance. The checker still reports local validation and unknown
accounting/period/unit authority. **Use declared schema instead** visibly drops native
binding and clears earlier evidence. No native binding is configured in default mode.

Opt-in acceptance (real local service and native sandbox schema, fictional CSV):

```sh
python3 scripts/csv_native_acceptance.py --port 8782 --out /private/path/native-proof
```

See [native acceptance and restoration receipt](receipts/native-schema-20261007.md).

## Reporting context (optional, explicit)

Enable **Check a declared reporting policy** and bind exact text period/currency
columns, expected YYYY-MM period, uppercase three-letter currency label, numeric
amount columns (one exact name per line), unit label and accounting basis. Bind a
unit column when the source contains one. Supported row-unit labels are `units`,
`cents`, `thousands`, `millions`; Wingman never derives units from a column name.
Empty unit binding and unknown accounting basis stay **incomplete**, not matched.

Every supplied row's labels are compared exactly, without trimming, coercion,
currency conversion or scaling. A wrong period, currency or unit creates separate
row-level context findings and a needs-review heading even when arithmetic passes.
Combined issue count includes schema/data and context findings. Exact totals remain
unscaled arithmetic; mixed labels make them unsuitable for reporting. The monthly
label check does not implement fiscal calendars, quarter/year-to-date semantics,
account mapping, sign conventions, FX or accounting-basis correctness.

Version 3 packets retain the explicit policy, context results and context-checker
build hash and replay them offline, including native-bound packets. A matched policy
means only that supplied row labels match the declaration. Original source/period/
unit authority and accounting correctness flags stay unverified; no approval is
created. Policy edits clear earlier results/download. Clear also clears policy.
Policy declarations in downloaded evidence can be sensitive.

## Reproduce a saved packet

Packets include the explicitly declared schema and key policy, so the next reviewer
does not have to reconstruct them. Keep the original CSV in its approved private
source location; Wingman does not keep a copy for you.

```sh
python3 server/csv_review.py --verify-packet wingman-csv-review.json --csv original.csv
```

This starts no HTTP service. It reads only the two explicit files, reruns the
validator and compares the input/schema/build hashes, every finding and total,
completeness flags and trust claims. Exit 0 means `reproduced`, exit 1 means
`mismatch` with the affected top-level fields, exit 2 means invalid/unreadable input.
Output contains no source rows or totals. A failed CSV screen can be faithfully
reproduced; replay does not turn failure into approval.

**Replay is reproducibility, not signed provenance.** A matching packet does not
authenticate its author, timestamp, native schema or accounting authority. Changing
both the supplied source and packet consistently can reproduce a different review.
Schema approval and trust in the original source remain external responsibilities.
The exact validator build must match; after a checker update use the retained
release to reproduce older evidence, rather than silently accepting new semantics.

## Limits, errors and privacy

256 KiB UTF-8 CSV, 1,000 data records, 64 columns, 8,192 characters per field.
The whole bounded input is checked; beyond the limit it is rejected without a
partial pass. First 100 issues are shown/exported with a full issue count and
truncation flag. Unsupported schema types mean incomplete, never passed. Numeric
values are exact decimals in source units; formatted currencies, NaN, whitespace
coercion and invented units are rejected. Key comparison is exact text.

Malformed CSV/schema and limits have actionable messages. A network failure or
ten-second deadline keeps your inputs, but no result/download. Stop waiting and
input changes ignore late replies; they do not cancel a server computation.
Restart the CSV process and check again; there is no mutation to replay.

Default mode makes no outbound or Workiva requests. Native mode uses `wk` for exact
schema reads and grant verification only; it sends no CSV to Workiva. It does not write uploaded inputs
or request logs. It does not use browser local/session storage, analytics or third-
party assets. Packets include hashes, schema column names, row locations and totals,
not raw CSV rows. Those fields can still be sensitive; hashes of guessable inputs
are not anonymization. Downloads are user-managed; Clear cannot remove a downloaded
file. Process memory, browser recovery and OS swap are outside secure-erasure claims.
Loopback access trusts local OS users; this is not a hosted customer access model.

## Reuse provenance

Validator and tests copied from the clean local Lockfield Workiva Plugin v0.4.0
repository at `/home/dave/work/design-venture/lockfield/workiva-plugin`, Git commit
`19376f7`. Original paths: `src/lockfield_workiva/local_checks.py` and
`tests/test_local_checks.py`. Original Git blob IDs:
`eeacb25fefaf9c485708d3b4f1626b6d6bf1ff2d` and
`a9bce7aafd55b76dad6e39f005fd334e26300d31`.
Checker logic is unchanged; Wingman's standard-library exception replaces the
plugin's package import. Keep validation changes synchronized through an explicit
source comparison, rather than maintaining divergent screens unknowingly.

The native-schema adapter, customer OAuth/proposal database, private configs and
operator grants were not copied. Wingman icons and `setup.css` are reused in place.
See [source inventory, thesis and roadmap](product-development.md).

## Verify

```sh
python3 -m pytest server/test_csv_checks.py server/test_csv_review.py server/test_csv_native.py server/test_csv_context.py -q
AGENT_BROWSER_ENGINE=chrome python3 -m pytest scripts/test_csv_review_browser.py -q
python3 -m pytest server/ -q
node extension/content.test.js
```

Browser tests require installed `agent-browser` and Chromium. Lightpanda is not
visual verification. The new command starts/stops a disposable local service,
downloads actual evidence, checks exact totals, keyboard submission, escaped
labels, malformed CSV, stale replies, input clearing, reload and narrow/light/dark
layouts. It neither modifies the installed extension nor requests live Workiva.

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
6. Clear inputs when finished. Stop with Ctrl+C. Restart forgets all process data.

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

# Wingman native-schema sandbox acceptance — October 7, 2026

Authority: Dave explicitly authorized LSL sandbox use, synthetic table creation,
the existing grant and local milestone commits. No production/customer data, grant
change, push, merge, deployment or port 8770 service update is authorized.

## Native target and adopted result

`wk whoami` proved the adopted `lsl-account` binding. Account pin:
`QWNjb3VudB8xMTQ4MjM2MTkwMA` (an identifier, not a credential).
Created one empty, unshared Wdata data/fact table:
`0f618794c8374c8fa18f872158f058ed`,
`zz Wingman Synthetic CSV Acceptance 20261007`.
Native GET matched ID, account, ordered schema and absence of imported data.
Retained this reusable synthetic fixture; no deletion or customer-table reuse.

Wingman accepts this operator-configured ID, not a browser-provided resource ID.
The native flow uses `wk`'s adopted credential resolver rather than copying OAuth
code or secrets. Data reads are exact-table GETs only, never listing datasets or
querying values. A human explicitly loads the schema; checking then rereads its
fingerprint. Native name/type/requiredness is locked, key policy stays explicit.
Default declared-schema mode still needs no grant.

Wdata added `_tags`, `_filename`, `_timestamp`, `_userid` to the four user columns.
This bounded full-schema screen exposes all eight. It does not certify import
mapping, silently discard native columns or equate unsupported `float` with decimal.

## Live acceptance and recovery

Executed against the actual local service and native Workiva schema:

```sh
python3 server/csv_review.py --port 8782 \
  --sandbox-table 0f618794c8374c8fa18f872158f058ed
python3 scripts/csv_native_acceptance.py --port 8782 \
  --out .amp/in/artifacts/native-acceptance-restored
```

The acceptance command checks fixed, independently specified fictional input:
IDs `001` and `1` remain distinct; integer amounts `1001` and `-2` total `999`.
Appending another `001` with invalid amount yields exactly the type/key findings at
record 4. Extra table authority is refused; wrong schema fingerprint is rejected;
the observed packet replays offline. Accounting/import flags remain false.

Real change test: changed only this empty table's description using native PUT,
with every user-defined column retained. Readback confirmed identical schema and
no imports. **Native `version` stayed 3 while `updated` changed.** The earlier
review binding was refused because its fingerprint includes `updated`, not merely
`version`. Restored the original description/schema and reread every user-controlled
field. Native modification timestamp/history remains, as expected; it cannot be
restored by pretending no action happened. Restored-target acceptance passed.
This does not establish compare-and-swap or permit production repair concurrency.

Private evidence under `.amp/in/artifacts/`: native create/readback; before, changed,
restored PUT/GET records; `native-acceptance-restored/receipt.json`, packet and
fictional CSV; `server-tests-native.log`; final native pass/stale/narrow-dark PNGs.
These contain synthetic metadata only, no tokens or credentials.

Regression coverage uses scripted wk answers for denied accounts/IDs/shared tables,
unknown modes, tampered packets and stale metadata through real loopback HTTP.
Those tests are not substituted for the native calls above. The existing full server
suite and default real-browser suite are rerun on this candidate. Optional vision
skips and independent release adjudication remain explicit.

Browser acceptance exercised actual schema load, locked fields, keyboard check,
native result/download, declared-schema reset and narrow/dark layout. The stale UI
capture uses an intentionally changed outgoing fingerprint against the real service;
the real native metadata-change test is separate. No simulated Workiva response is
presented as native proof. Initial inspection found an overly tall disabled editor;
compact read-only rows replaced it, and pass headings now explicitly say **local**.

## Recovered API traps and remaining gates

- Forge's create-table wrapper used `/tables`, returning 404; native API is `/table`.
- Native creation uses `type=data` and `tableSchema`, not UI label `fact`/`schema`.
- A semicolon in the description caused native 400. The stock wk CLI error omitted
  the nested diagnostic; the existing wk API exposed it without credentials.
- The official create/update routes are documented at
  https://developers.workiva.com/wdata-v1/wdata-createtable.html and
  https://developers.workiva.com/wdata-v1/wdata-updatetable.html.
- An initial regression asserted numeric substring `001` absent from a serialized
  packet; a UTC microsecond field legitimately contained it. Replaced with an
  unmistakable private-key sentinel, preserving the actual non-disclosure assertion.

Native schema observation is accepted for this synthetic slice, not native import,
accounting correctness, complete G1–G7 or a customer release. Next goal: explicit
period/currency/unit and accounting-policy context, with wrong-period/mixed-unit
cases that cannot inherit a green arithmetic result. Independent detector labels,
durable exception decisions, clean-machine onboarding and safe-action concurrency
acceptance remain open. Wingman still exposes no Workiva mutation path here.

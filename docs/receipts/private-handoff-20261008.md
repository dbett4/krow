# Wingman private handoff — October 8, 2026

## Goal and delivered behavior

Remove manual schema/context reconstruction from a read-only second-reviewer
handoff, targeting first useful evidence within ten minutes. The browser imports
the existing arithmetic packet's explicit policy and reproduces it through the
same offline verifier. Replay has no storage or native authority. Imported native
bindings remain historical; journal saving is switched off; no decisions or
approvals are imported. A fresh check is separately required before saving work.

Malformed/journal JSON preserves source and declared controls. Changed source
invalidates prior results and returns explicit mismatched fields. Strict HTTP
arguments reject requests for storage, native bindings or confirmation authority.
Same-origin checks, bounded payloads, no-cache and existing privacy controls apply.

## Measured rehearsal and limits

`scripts/test_private_pilot.py` builds and extracts the actual allowlisted ZIP,
starts Python with `-S`, empty HOME and minimal PATH, opens a fresh Chromium
session and exercises the shipped handoff flow. Initial successful run:

- Evidence reproduced by 1.161 seconds / five browser actions.
- Fresh inspection by 1.516 seconds, zero manually recreated schema/context fields.
- Entire journal confirmation, restart and historical readback by 3.470 seconds.
- Exact partial subtotal 1026; one arithmetic and three context issues; source
  edit produces csv_sha256/result mismatch; journal JSON rejected without changing
  controls; explicit exception confirmed and read back after process/browser restart.
- Zero Workiva requests. Native mutation/import/approval not verified or enabled.

Machine record and desktop default/reproduced plus narrow dark mismatch captures:
`.amp/in/pilot-centered/test_extracted_packet_handoff_0/`. All three captures were
inspected for readable boundaries, explicit replay limitations and overflow.

Combined final verification: 845 passed / 13 optional vision skips using
`python3 -m pytest server/ scripts/test_private_pilot.py scripts/test_csv_bundle.py
scripts/test_durable_review_browser.py scripts/test_csv_review_browser.py -q`.
`git diff --check` passed. Final proof is retained under `.amp/in/handoff-final/`.

Early runs exposed a Chrome automation coordinate click landing on HTML rather
than the replay button after results changed the layout. Captured event targets
proved this; scrolling controls into view before real browser actions repaired the
harness. No detector/replay assertions were relaxed to obtain a pass.

This is a **same-builder automated rehearsal on the existing VPS**, not an
independent human, unaided reviewer, clean physical machine, supported remote
SSH setup or full extension acceptance. The ten-minute human gate remains open.
No native schema, metadata update or service deployment was performed here.

## Next goal

Keep native mutation disabled. Continue endpoint-specific concurrency/recovery
investigation; collect independent held-out labels and an unfamiliar reviewer's
timed handoff for the exact candidate, without treating builder rehearsal as
independent acceptance. The port 8770 service remains unchanged. Local commits
only; no push, merge, deployment or release.

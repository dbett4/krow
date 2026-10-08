/* No browser storage, analytics or third-party assets. Native reads are explicit. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  let packet = null, generation = 0, controller = null, serial = 0;
  let nativeSchema = null;
  let savedReview = null;
  let importedPacket = null;
  const defaultBoundary = $("boundary-description").textContent;
  const types = ["string", "integer", "decimal", "boolean", "date", "timestamp"];
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function invalidate(message) {
    generation++;
    if (controller) controller.abort();
    controller = null;
    packet = null;
    savedReview = null;
    $("review-journal").replaceChildren();
    $("download").disabled = true;
    $("replay").disabled = !importedPacket || !$("csv").value;
    $("replay-status").textContent = "";
    $("check").disabled = false;
    $("cancel").hidden = true;
    $("message").textContent = message || "Inputs changed. Run a new check.";
    $("results").replaceChildren(el("p", "3. Review the evidence", "eyebrow"), el("h2", "Run a check for these inputs."), el("p", "Earlier arithmetic evidence is cleared when inputs change. Explicitly saved journal entries remain."));
  }
  function column(name = "", kind = "string", required = false, key = false) {
    const row = el("div", undefined, "column"), id = ++serial;
    const fields = el("div", undefined, "column-fields");
    const nameField = el("input"); nameField.value = name; nameField.required = true; nameField.maxLength = 128; nameField.id = "name-" + id; nameField.className = "name";
    const select = el("select"); select.id = "type-" + id; select.className = "type";
    types.forEach((type) => { const option = el("option", type); option.value = type; select.append(option); });
    if (!types.includes(kind)) { const option = el("option", kind + " (unsupported)"); option.value = kind; select.append(option); }
    select.value = kind;
    [["Column name", nameField], ["Expected type", select]].forEach(([text, input]) => { const group = el("div"), label = el("label", text); label.htmlFor = input.id; group.append(label, input); fields.append(group); });
    const flags = el("div", undefined, "column-flags");
    [["Required", "required", required], ["Key", "key", key]].forEach(([text, cls, checked]) => { const label = el("label"), input = el("input"); input.type = "checkbox"; input.className = cls; input.checked = checked; label.append(input, document.createTextNode(text)); flags.append(label); });
    const remove = el("button", "Remove", "wm-btn remove"); remove.type = "button"; remove.setAttribute("aria-label", "Remove column " + (name || id)); remove.addEventListener("click", () => { row.remove(); invalidate(); $("add").focus(); }); flags.append(remove);
    row.append(fields, flags); $("columns").append(row);
    return nameField;
  }
  function nativeMode(schema) {
    nativeSchema = schema;
    $("manual-schema").hidden = !schema;
    $("add").disabled = !!schema;
    $("columns").classList.toggle("native-columns", !!schema);
    [...$("columns").children].forEach((row, index) => {
      row.querySelector(".native-summary")?.remove();
      row.querySelector(".required").parentElement.hidden = !!schema;
      row.querySelector(".key").removeAttribute("aria-label");
      if (schema) {
        const item = schema.columns[index], summary = el("div", undefined, "native-summary");
        summary.append(el("strong", item.name), el("small", item.type + " · " + (item.required === undefined ? "Requiredness unknown" : item.required ? "Required" : "Nullable")));
        row.querySelector(".key").setAttribute("aria-label", "Key column " + item.name);
        row.prepend(summary);
      }
    });
    $("columns").querySelectorAll(".name, .type, .required, .remove").forEach((node) => { node.disabled = !!schema; });
    $("boundary-title").textContent = schema ? "Private sandbox schema · Read-only Workiva metadata" : "Private local screen · No Workiva connection";
    $("boundary-description").textContent = schema ? "CSV values stay in this VPS process. Only the configured synthetic table schema is read from Workiva. No import, period, units or accounting approval is established." : defaultBoundary;
    $("schema-status").textContent = schema ? schema.snapshot.binding.table_name + " · Version " + schema.snapshot.binding.version + " · Observed " + new Date(schema.snapshot.observed_at).toLocaleString() + ". Native fields locked; keys remain your explicit policy. Full schema includes managed columns; import mapping is not checked." : "Declared schema. Not native-verified.";
  }
  $("manual-schema").addEventListener("click", () => { invalidate(); nativeMode(null); });
  function contextMode(enabled) {
    $("use-context").checked = enabled;
    $("context-fields").disabled = !enabled;
    $("context-fields").hidden = !enabled;
  }
  $("use-context").addEventListener("change", () => { contextMode($("use-context").checked); invalidate(); });
  function forgetImportedPacket() {
    importedPacket = null; $("packet-file").value = ""; $("replay").disabled = true;
    $("packet-status").textContent = "No packet loaded. Ask the source owner for the review evidence JSON and original CSV.";
  }
  $("packet-file").addEventListener("change", async () => {
    invalidate(); importedPacket = null; $("replay").disabled = true;
    const request = generation, file = $("packet-file").files[0]; if (!file) return;
    try {
      if (file.size > 524288) throw new Error("Review packet exceeds 512 KiB. Existing source and policy were kept.");
      const data = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer()));
      if (request !== generation) return;
      const schema = data?.declared_schema, policy = data?.reporting_policy;
      if (data?.product !== "Wingman" || ![1, 2, 3].includes(data.packet_version) || !schema || !Array.isArray(schema.columns) || !schema.columns.length || schema.columns.length > 64 || !Array.isArray(schema.key_columns) || schema.key_columns.length > 8 ||
          schema.columns.some((item) => !item || typeof item.name !== "string" || !item.name.trim() || item.name.length > 128 || /[\x00\r\n]/.test(item.name) || typeof item.type !== "string" || !item.type.trim() || item.type.length > 64 || (item.required !== undefined && typeof item.required !== "boolean")) ||
          new Set(schema.columns.map((item) => item.name)).size !== schema.columns.length || new Set(schema.key_columns).size !== schema.key_columns.length || schema.key_columns.some((key) => !schema.columns.some((item) => item.name === key))) {
        throw new Error("Choose a supported Wingman arithmetic review packet, not journal handoff JSON. Existing source and policy were kept.");
      }
      if (policy && (typeof policy !== "object" || ["period_column", "expected_period", "currency_column", "expected_currency", "unit_column", "expected_unit", "accounting_basis"].some((key) => typeof policy[key] !== "string" || policy[key].length > 128) || !Array.isArray(policy.amount_columns) || !policy.amount_columns.length || policy.amount_columns.length > 64 || policy.amount_columns.some((name) => typeof name !== "string" || name.length > 128) || !["units", "cents", "thousands", "millions"].includes(policy.expected_unit) || !["unknown", "cash", "accrual", "modified_accrual"].includes(policy.accounting_basis))) {
        throw new Error("Packet reporting policy is invalid. Existing source and policy were kept.");
      }
      nativeMode(null); reviewMode(false); contextMode(!!policy);
      $("columns").replaceChildren(); schema.columns.forEach((item) => column(item.name, item.type, item.required === true, schema.key_columns.includes(item.name)));
      if (policy) {
        [["period-column", "period_column"], ["expected-period", "expected_period"], ["currency-column", "currency_column"], ["expected-currency", "expected_currency"], ["unit-column", "unit_column"], ["expected-unit", "expected_unit"], ["accounting-basis", "accounting_basis"]].forEach(([id, key]) => { $(id).value = policy[key]; });
        $("amount-columns").value = policy.amount_columns.join("\n");
      }
      importedPacket = data;
      $("replay").disabled = !$("csv").value;
      $("packet-status").textContent = "Declared policy loaded from historical packet. " + (data.native_schema ? "Native binding is historical, not connected or current. " : "") + "No approval or saved decisions imported. Supply the original CSV and reproduce, or run a fresh check.";
      $("message").textContent = "Packet policy loaded without retyping. No Workiva request or saved check. Review the declarations before checking.";
    } catch (error) { if (request === generation) { $("packet-status").textContent = "No packet loaded."; $("message").textContent = error instanceof SyntaxError || error instanceof TypeError ? "Packet is not supported UTF-8 JSON. Existing source and policy were kept." : error.message; } }
  });
  $("replay").addEventListener("click", async () => {
    if (!importedPacket || !$("csv").value) return;
    invalidate(); const request = generation;
    $("replay").disabled = true; $("replay-status").textContent = "Recomputing historical evidence against the supplied source…";
    try {
      const data = await journalRequest("/api/replay", { packet: importedPacket, csv_text: $("csv").value });
      if (request !== generation) return;
      $("replay-status").textContent = data.status === "reproduced" ? "Evidence reproduced. Historical results match this source and build. No authorship, current native schema or approval verified; run a fresh check before saving new decisions." : "Evidence mismatch: " + data.mismatched_fields.join(", ") + ". Ask the source owner for the correct source/packet/build. No prior approval is imported.";
    } catch (error) { if (request === generation) $("replay-status").textContent = "Replay unavailable. " + error.message + " Your source remains; confirm the service or packet, then retry."; }
    finally { if (request === generation) $("replay").disabled = !importedPacket || !$("csv").value; }
  });
  fetch("/api/review-config", { cache: "no-store", signal: AbortSignal.timeout(10000) }).then((response) => {
    if (!response.ok) throw new Error("Configuration unavailable");
    return response.json();
  }).then((config) => {
    $("durable-options").hidden = !config.durable_review_enabled;
    $("load-native").disabled = config.native_schema_configured !== true;
    $("native-availability").textContent = config.native_schema_configured === true
      ? "One operator-bound synthetic table configured. Access is not yet verified; load its schema explicitly. Native writes are disabled."
      : "No native sandbox configured. Continue with a declared schema or imported packet; no Workiva grant is needed. Native writes are disabled.";
  }).catch(() => {
    $("native-availability").textContent = "Service configuration unavailable. Native reads and journal saving remain unavailable; local CSV inputs are kept. Confirm the service and reload this page before starting a check. Native writes are disabled.";
  });
  function reviewMode(enabled) {
    $("save-review").checked = enabled;
    $("review-scope").disabled = !enabled;
    $("review-scope").hidden = !enabled;
  }
  $("save-review").addEventListener("change", () => {
    reviewMode($("save-review").checked);
    invalidate();
  });
  function reviewScope() {
    return { workspace: $("scope-workspace").value, file_copy: $("scope-file").value, period: $("scope-period").value };
  }
  async function journalRequest(path, body) {
    const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json", "X-Wingman-Review": "1" }, body: JSON.stringify(body), cache: "no-store", signal: AbortSignal.timeout(10000) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Private journal unavailable.");
    return data;
  }
  function renderJournal(snapshot, actionable = false) {
    savedReview = snapshot;
    const host = $("review-journal"); host.replaceChildren(el("h2", "Saved review · Not accounting approval"));
    host.append(el("p", snapshot.scope.workspace + " / " + snapshot.scope.file_copy + " / " + snapshot.scope.period),
      el("p", snapshot.observed_at ? "Observed " + new Date(snapshot.observed_at).toLocaleString() + " · " + (snapshot.complete ? "Complete finding coverage" : "Incomplete coverage — unvisited findings stay unresolved") : "No saved check for this scope."));
    if (!actionable && snapshot.run_id) host.append(el("p", "Historical evidence only. Supply the source and run a fresh saved check before deciding."));
    snapshot.findings.forEach((finding) => {
      const card = el("div", undefined, "decision-card"), location = finding.location;
      card.append(el("strong", location.code.replaceAll("_", " ")), el("p", (location.row ? "Record " + location.row : "Schema") + (location.column ? " · " + location.column : "")), el("p", finding.state.replaceAll("_", " "), "decision-state"));
      const previous = snapshot.history.find((event) => event.finding === finding.id);
      if (previous) card.append(el("small", "Last decision: " + previous.decision.replaceAll("_", " ") + " · " + previous.reviewer + " · " + previous.reason));
      if (actionable && finding.current) {
        const form = el("form"), label = el("label", "Reviewer label (not authenticated)"), reviewer = el("input"), reasonLabel = el("label", "Reason · Do not include source values"), reason = el("textarea"), confirmLabel = el("label", undefined, "context-toggle"), confirm = el("input");
        reviewer.id = "reviewer-" + finding.id; reviewer.required = true; reviewer.maxLength = 100; label.htmlFor = reviewer.id;
        reason.id = "reason-" + finding.id; reason.required = true; reason.maxLength = 1000; reason.className = "decision-reason"; reasonLabel.htmlFor = reason.id;
        confirm.type = "checkbox"; confirm.required = true; confirmLabel.append(confirm, document.createTextNode("Confirm this decision for this exact evidence only"));
        const button = el("button", finding.state === "accepted_exception" ? "Reopen exception" : "Accept exception", "wm-btn"); button.type = "submit";
        form.append(label, reviewer, reasonLabel, reason, confirmLabel, button);
        form.addEventListener("submit", async (event) => {
          event.preventDefault(); const request = generation; button.disabled = true;
          try {
            const data = await journalRequest("/api/review-decisions", { scope: snapshot.scope, run_id: snapshot.run_id, finding_id: finding.id, revision: finding.revision, evidence_sha256: finding.evidence_sha256, decision: finding.state === "accepted_exception" ? "open" : "accepted_exception", reason: reason.value, reviewer: reviewer.value, confirmed: confirm.checked });
            if (request !== generation) return;
            renderJournal(data, true); $("message").textContent = "Decision saved and read back. The finding remains; no accounting approval or Workiva change.";
          } catch (error) { if (request === generation) { button.disabled = false; $("message").textContent = error.message + " Load saved review before retrying an uncertain confirmation."; } }
        });
        card.append(form);
      }
      host.append(card);
    });
    if (snapshot.run_id) {
      const download = el("button", "Download saved review handoff", "wm-btn"); download.type = "button";
      download.addEventListener("click", () => { if (!savedReview) return; const url = URL.createObjectURL(new Blob([JSON.stringify(savedReview, null, 2)], { type: "application/json" })); const link = el("a"); link.href = url; link.download = "wingman-review-handoff.json"; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }); host.append(download);
    }
    host.append(el("p", snapshot.limits || "Local declarations only; no approval verified."), el("small", "Reasons and scope labels are retained in your operator's private journal. Clear inputs does not delete it. History preview includes the latest 200 events" + (snapshot.history_truncated ? " of " + snapshot.history_count : "") + "."));
  }
  $("load-review").addEventListener("click", async () => {
    invalidate("Loading historical review metadata only…"); const request = generation;
    try { const data = await journalRequest("/api/review-history", { scope: reviewScope() }); if (request === generation) { renderJournal(data); $("message").textContent = "Saved review loaded. Run a fresh check before confirming any decision."; } }
    catch (error) { if (request === generation) $("message").textContent = error.message; }
  });
  $("load-native").addEventListener("click", async () => {
    invalidate("Reading only the configured native sandbox schema…");
    const request = generation, abort = new AbortController(); controller = abort;
    $("check").disabled = true; $("cancel").hidden = false;
    const timeout = setTimeout(() => abort.abort(), 10000);
    try {
      const response = await fetch("/api/schema", { method: "POST", headers: { "Content-Type": "application/json", "X-Wingman-Review": "1" }, body: "{}", signal: abort.signal, cache: "no-store" });
      const data = await response.json(); if (request !== generation) return;
      if (!response.ok) throw new Error(data.error || "Sandbox schema unavailable.");
      $("columns").replaceChildren(); data.columns.forEach((item) => column(item.name, item.type, item.required === true));
      nativeMode(data); $("message").textContent = "Native schema loaded. Supply your CSV and select any explicit key policy, then check.";
    } catch (error) {
      if (request === generation) $("message").textContent = error.name === "AbortError" ? "Schema read timed out. Your inputs remain; try reloading the sandbox schema." : (error instanceof TypeError ? "Sandbox service unavailable. Your inputs remain." : error.message);
    } finally {
      clearTimeout(timeout); if (request === generation) { controller = null; $("check").disabled = false; $("cancel").hidden = true; }
    }
  });
  function render(data) {
    const result = data.result, host = $("results"); host.replaceChildren();
    host.append(el("p", "3. Review the evidence", "eyebrow"));
    const title = { passed: "Supported checks passed", failed: "Issues need your review", incomplete: "Some checks remain unknown" }[result.screen_status];
    const context = data.reporting_context, policy = data.reporting_policy;
    const heading = context && context.status !== "matched" ? "Reporting context needs review" : data.native_schema_observed && result.screen_status === "passed" ? "Supported local checks passed" : title;
    host.append(el("h2", heading, "result-title"), el("p", data.native_schema_observed ? "Native sandbox schema reread · Local checks, not native import acceptance" : "Caller-supplied schema · Not native-verified"));
    const contextBox = el("div", undefined, "context-evidence");
    contextBox.append(el("h3", context ? { matched: "Declared row labels matched", failed: "Reporting policy mismatches", incomplete: "Reporting context incomplete" }[context.status] : "Reporting context not checked"));
    if (context) {
      contextBox.append(el("p", policy.expected_period + " · " + policy.expected_currency + " · " + policy.expected_unit + " (unscaled) · Basis: " + policy.accounting_basis.replaceAll("_", " ")),
        el("p", "Bound amounts: " + policy.amount_columns.join(", ") + ". Arithmetic screen: " + result.screen_status + "."));
      context.unknowns.forEach((text) => contextBox.append(el("p", text)));
      context.issues.forEach((issue) => contextBox.append(el("p", issue.code.replaceAll("_", " ") + (issue.row ? " · Record " + issue.row : "") + (issue.column ? " · " + issue.column : ""))));
      if (context.issues_truncated) contextBox.append(el("p", "Showing first 100 of " + context.issue_count + " reporting issues."));
      if (context.status !== "matched") contextBox.append(el("strong", "Do not use combined totals for reporting until the context is resolved."));
      contextBox.append(el("p", context.limitations));
    } else contextBox.append(el("p", "Totals are arithmetic only. Period, currency, units and accounting basis have not been checked."));
    contextBox.append(el("small", "Reviewer-declared policy is not independent source verification or accounting approval."));
    host.append(contextBox);
    const stats = el("div", undefined, "stats");
    [[result.row_count, "Data records checked"], [result.issue_count + (context?.issue_count || 0), "Issues found"]].forEach(([count, text]) => { const item = el("div", undefined, "stat"); item.append(el("strong", count), el("span", text)); stats.append(item); }); host.append(stats);
    host.append(el("h3", "Exact totals · Source units"));
    const totals = Object.entries(result.numeric_totals);
    if (!totals.length) host.append(el("p", "No numeric schema columns to total."));
    totals.forEach(([name, total]) => { const item = el("div", undefined, "total"); item.append(el("strong", name), el("code", total.total), el("small", (total.complete ? "Complete numeric column" : "Partial total — do not use as a full column total") + " · " + total.validated_nonempty_values + " valid nonempty values")); host.append(item); });
    if (result.issues.length) {
      host.append(el("h3", "Findings"));
      const list = el("div", undefined, "findings"); list.tabIndex = 0; list.setAttribute("aria-label", "Row-level findings");
      result.issues.forEach((issue) => { const item = el("div", undefined, "finding");
        item.append(el("strong", issue.code.replaceAll("_", " ")), el("p", (issue.row ? "Record " + issue.row + " (header is record 1)" : "Schema") + (issue.column ? " · " + issue.column : "")));
        if (issue.first_row) item.append(el("small", "First occurrence: record " + issue.first_row));
        if (issue.csv_line_end) item.append(el("p", "Ends on CSV line " + issue.csv_line_end));
        if (issue.expected_type || issue.declared_type) item.append(el("p", "Declared type: " + (issue.expected_type || issue.declared_type)));
        if (issue.expected_columns !== undefined) item.append(el("p", "Expected " + issue.expected_columns + " columns; observed " + issue.actual_columns));
        list.append(item);
      }); host.append(list);
      if (result.issues_truncated) host.append(el("p", "Showing the first 100 of " + result.issue_count + " issues. Every input record was checked."));
    }
    host.append(el("h3", "What to do next"), el("p", result.screen_status === "passed" ? "Review the schema, period and units with your source owner before importing. A pass is not accounting approval." : "Review the referenced records and declared schema. Correct your source file, then run a new check. Wingman does not alter it."));
    host.append(el("p", "Checked " + new Date(data.generated_at).toLocaleString() + " · Unreviewed evidence", "hint"));
  }
  $("add").addEventListener("click", () => { if ($("columns").children.length >= 64) { $("message").textContent = "The schema is limited to 64 columns."; return; } invalidate(); column().focus(); });
  $("review-form").addEventListener("input", () => invalidate());
  $("sample").addEventListener("click", () => {
    forgetImportedPacket();
    invalidate("Fictional example loaded. Check it to find a duplicate key and an invalid amount.");
    nativeMode(null);
    contextMode(false);
    reviewMode(false);
    $("columns").replaceChildren(); column("department", "string", true, true); column("actual", "decimal", true);
    $("csv").value = "department,actual\nFinance,1250.25\nOperations,-50.10\nFinance,invalid\n"; $("file").value = "";
  });
  $("clear").addEventListener("click", () => { forgetImportedPacket(); invalidate("Inputs cleared. Explicitly saved journal entries remain; raw CSV is not retained."); nativeMode(null); contextMode(false); reviewMode(false); $("review-scope").querySelectorAll("input").forEach((node) => { node.value = ""; }); $("context-fields").querySelectorAll("input, textarea").forEach((node) => { node.value = ""; }); $("expected-unit").value = "units"; $("accounting-basis").value = "unknown"; $("csv").value = ""; $("file").value = ""; $("columns").replaceChildren(); column().focus(); });
  $("cancel").addEventListener("click", () => invalidate("Stopped waiting. No result is retained; the bounded local check may finish on the server."));
  $("file").addEventListener("change", async () => {
    invalidate(); const request = generation, file = $("file").files[0]; if (!file) return;
    if (file.size > 262144) { $("file").value = ""; $("message").textContent = "File exceeds 256 KiB. Existing pasted text was kept."; return; }
    try { const text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer()); if (request !== generation) return; $("csv").value = text; $("replay").disabled = !importedPacket || !text; $("message").textContent = importedPacket ? "CSV loaded locally. Reproduce imported evidence or run a fresh check with its declared policy." : "CSV loaded locally. Declare its expected schema before checking."; }
    catch (_) { if (request === generation) $("message").textContent = "File is not valid UTF-8. Export a UTF-8 CSV and try again."; }
  });
  $("review-form").addEventListener("submit", async (event) => {
    event.preventDefault(); invalidate("");
    const rows = [...$("columns").children], columns = nativeSchema ? nativeSchema.columns : rows.map((row) => ({ name: row.querySelector(".name").value, type: row.querySelector(".type").value, required: row.querySelector(".required").checked }));
    const key_columns = rows.filter((row) => row.querySelector(".key").checked).map((row) => row.querySelector(".name").value);
    const reporting_policy = $("use-context").checked ? {
      period_column: $("period-column").value, expected_period: $("expected-period").value,
      currency_column: $("currency-column").value, expected_currency: $("expected-currency").value,
      unit_column: $("unit-column").value, expected_unit: $("expected-unit").value,
      amount_columns: $("amount-columns").value.split(/\r?\n/), accounting_basis: $("accounting-basis").value,
    } : null;
    const request = generation, abort = new AbortController(); controller = abort;
    $("check").disabled = true; $("cancel").hidden = false; $("message").textContent = "Checking every supplied record…";
    const timeout = setTimeout(() => abort.abort(), 10000);
    try {
      const response = await fetch("/api/review", { method: "POST", headers: { "Content-Type": "application/json", "X-Wingman-Review": "1" }, body: JSON.stringify({ csv_text: $("csv").value, columns, key_columns, ...(reporting_policy ? { reporting_policy } : {}), ...(nativeSchema ? { native_schema_sha256: nativeSchema.snapshot.schema_sha256 } : {}), ...($("save-review").checked ? { review_scope: reviewScope() } : {}) }), signal: abort.signal, cache: "no-store" });
      const data = await response.json(); if (request !== generation) return;
      if (!response.ok) {
        const guidance = data.code === "invalid_csv" ? " Check that the header is present and every quoted field is closed. Re-export the CSV and try again." : "";
        throw new Error((data.error || "Review could not be completed.") + guidance);
      }
      packet = data.packet || data; render(packet);
      if (data.saved_review) renderJournal(data.saved_review, true);
      $("download").disabled = false; $("message").textContent = "Check finished. Review its limits before using the results.";
    } catch (error) { if (request === generation) $("message").textContent = error.name === "AbortError" ? "Check timed out. Your inputs remain; confirm the service is running and try again." : (error instanceof TypeError ? "Service unavailable. Your inputs remain; restart the private CSV service and try again." : error.message); }
    finally { clearTimeout(timeout); if (request === generation) { controller = null; $("check").disabled = false; $("cancel").hidden = true; } }
  });
  $("download").addEventListener("click", () => { if (!packet) return; const url = URL.createObjectURL(new Blob([JSON.stringify(packet, null, 2)], { type: "application/json" })); const link = el("a"); link.href = url; link.download = "wingman-csv-review.json"; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); });
  window.addEventListener("pagehide", () => { generation++; if (controller) controller.abort(); packet = null; });
  column();
})();

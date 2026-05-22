import test from "node:test";
import assert from "node:assert/strict";
import {
  PROCESS_CATEGORIES,
  SECTION_TITLES,
  addChecklistItem,
  createProcess,
  deleteChecklistItem,
  duplicateProcess,
  generateProcessDocument,
  updateChecklistItem,
  validateProcessInput,
} from "../processGenerator.js";
import { checklistToMarkdown, parseBackup, processToMarkdown, processesToBackup } from "../markdownExport.js";
import { loadSavedProcesses, saveProcesses } from "../processStorage.js";

function baseInput(overrides = {}) {
  return {
    name: "Estimate follow-up",
    businessName: "Sample Co",
    industry: "landscaping contractor",
    category: "Customer follow-up",
    status: "Draft",
    rawDescription: "When an estimate is sent, email the customer after two days, update the CRM, and hand accepted work to scheduling.",
    ...overrides,
  };
}

function fakeStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem(key) {
      return Object.hasOwn(data, key) ? data[key] : null;
    },
    setItem(key, value) {
      data[key] = String(value);
    },
    data,
  };
}

test("generates a process document with all required sections", () => {
  const generated = generateProcessDocument(baseInput());
  assert.deepEqual(Object.keys(generated.sections), SECTION_TITLES);
  assert.ok(generated.sections["Step-by-step SOP"].includes("1."));
  assert.ok(generated.checklist.length > 0);
});

test("validates required process name", () => {
  const errors = validateProcessInput(baseInput({ name: "" }));
  assert.ok(errors.includes("Process name is required."));
});

test("validates invalid category", () => {
  const errors = validateProcessInput(baseInput({ category: "Tax checklist" }));
  assert.ok(errors.includes("Choose a valid process category."));
  assert.ok(!PROCESS_CATEGORIES.includes("Tax checklist"));
});

test("keyword suggestions add billing and collections controls", () => {
  const generated = generateProcessDocument(
    baseInput({
      name: "Invoice collection",
      category: "Billing and collections",
      rawDescription: "Every week review overdue invoices, confirm payment status, send collections reminders, and escalate old balances.",
    }),
  );
  assert.match(generated.sections["Risks or failure points"], /payment has already been received/i);
  assert.match(generated.sections["Automation opportunities"], /payment links/i);
  assert.ok(generated.checklist.some((item) => /invoice|payment/i.test(item.text)));
});

test("keyword suggestions add field service controls", () => {
  const generated = generateProcessDocument(
    baseInput({
      name: "Job closeout",
      category: "Field/service operations",
      rawDescription: "After field crews finish jobs, collect photos, service notes, exceptions, and send the job to billing.",
    }),
  );
  assert.match(generated.sections["Quality control checks"], /photos and service notes/i);
  assert.match(generated.sections.Handoffs, /Field crew hands closeout notes/i);
});

test("checklist item creation, editing, completion toggle, and deletion", () => {
  const process = createProcess(baseInput());
  const item = addChecklistItem(process, "Call customer", "Use latest estimate");
  assert.ok(process.checklist.find((candidate) => candidate.id === item.id));

  const updated = updateChecklistItem(process, item.id, { text: "Call customer again", completed: true, notes: "Left voicemail" });
  assert.equal(updated.text, "Call customer again");
  assert.equal(updated.completed, true);
  assert.match(process.sections["Internal checklist"], /\[x\] Call customer again/);
  assert.match(process.sections["Internal checklist"], /Left voicemail/);

  deleteChecklistItem(process, item.id);
  assert.equal(process.checklist.some((candidate) => candidate.id === item.id), false);
});

test("full Markdown export includes metadata, sections, checklist status, and notes", () => {
  const process = createProcess(baseInput());
  updateChecklistItem(process, process.checklist[0].id, { completed: true, notes: "Confirmed by owner" });
  const markdown = processToMarkdown(process);
  assert.match(markdown, /^# Estimate follow-up/);
  assert.match(markdown, /\*\*Business\/client:\*\* Sample Co/);
  assert.match(markdown, /## Process summary/);
  assert.match(markdown, /- \[x\]/);
  assert.match(markdown, /Note: Confirmed by owner/);
});

test("checklist-only Markdown export excludes full SOP sections", () => {
  const process = createProcess(baseInput());
  const markdown = checklistToMarkdown(process);
  assert.match(markdown, /^# Estimate follow-up — Internal Checklist/);
  assert.doesNotMatch(markdown, /## Step-by-step SOP/);
  assert.match(markdown, /- \[ \]/);
});

test("duplicate process creates a new ID and preserves content", () => {
  const process = createProcess(baseInput());
  const copy = duplicateProcess(process);
  assert.notEqual(copy.id, process.id);
  assert.equal(copy.name, `${process.name} Copy`);
  assert.deepEqual(copy.sections, process.sections);
  assert.deepEqual(copy.checklist, process.checklist);
});

test("saves and loads processes from local storage-compatible storage", () => {
  const storage = fakeStorage();
  const process = createProcess(baseInput());
  saveProcesses([process], storage);
  const loaded = loadSavedProcesses(storage);
  assert.equal(loaded.length, 1);
  assert.equal(loaded[0].name, process.name);
});

test("loads starter processes when local storage is empty", () => {
  const storage = fakeStorage();
  const loaded = loadSavedProcesses(storage);
  assert.ok(loaded.length >= 12);
  assert.ok(loaded.some((process) => process.name === "Field service job closeout"));
  assert.ok(loaded.some((process) => process.name === "New tax client onboarding"));
});

test("JSON backup export and import round trip", () => {
  const process = createProcess(baseInput());
  const backup = processesToBackup([process]);
  const parsed = parseBackup(backup);
  assert.equal(parsed.length, 1);
  assert.equal(parsed[0].id, process.id);
});

test("invalid JSON backup reports a clear error", () => {
  assert.throws(() => parseBackup("not json"), /Invalid imported JSON backup/);
  assert.throws(() => parseBackup(JSON.stringify({ wrong: [] })), /processes array/);
});

test("import rejects invalid category", () => {
  const process = createProcess(baseInput());
  process.category = "Tax checklist";
  assert.throws(() => parseBackup(processesToBackup([process])), /invalid category/i);
});

test("import rejects invalid status", () => {
  const process = createProcess(baseInput());
  process.status = "Almost Done";
  assert.throws(() => parseBackup(processesToBackup([process])), /invalid status/i);
});

test("import rejects missing required sections", () => {
  const process = createProcess(baseInput());
  delete process.sections.Objective;
  assert.throws(() => parseBackup(processesToBackup([process])), /Objective/);
});

test("import rejects invalid checklist item shape", () => {
  const process = createProcess(baseInput());
  process.checklist[0].completed = "yes";
  assert.throws(() => parseBackup(processesToBackup([process])), /completed as true or false/);
});

test("import normalizes invalid updatedAt to a valid date string", () => {
  const process = createProcess(baseInput());
  process.updatedAt = "not-a-date";
  const [parsed] = parseBackup(processesToBackup([process]));
  assert.equal(Number.isNaN(Date.parse(parsed.updatedAt)), false);
});

test("Markdown export works after validated import", () => {
  const process = createProcess(baseInput());
  const [parsed] = parseBackup(processesToBackup([process]));
  const markdown = processToMarkdown(parsed);
  assert.match(markdown, /^# Estimate follow-up/);
  assert.match(markdown, /## Internal checklist/);
});

test("browser entry uses direct-open-safe bundle script", async () => {
  const { readFile } = await import("node:fs/promises");
  const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
  await readFile(new URL("../app.bundle.js", import.meta.url), "utf8");
  assert.match(html, /<script src="app\.bundle\.js"><\/script>/);
  assert.doesNotMatch(html, /type="module"/);
});

test("process list rendering avoids innerHTML for imported process names", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(new URL("../app.js", import.meta.url), "utf8");
  assert.doesNotMatch(source, /innerHTML/);
  assert.match(source, /name\.textContent = process\.name/);
});

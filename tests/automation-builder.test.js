import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  AUTOMATION_SECTION_TITLES,
  addAutomationChecklistItem,
  createAutomationPlan,
  duplicateAutomationPlan,
  generateAutomationPlan,
  scoreComplexity,
  scoreImpact,
} from "../automationGenerator.js";
import { automationChecklistToMarkdown, automationPlanToMarkdown, automationPlansToBackup, parseAutomationBackup } from "../automationExport.js";
import { loadSavedAutomationPlans, saveAutomationPlans } from "../automationStorage.js";

function input(overrides = {}) {
  return {
    automationName: "Job closeout to invoice prep",
    clientName: "GreenSide Landscaping",
    industry: "Home services",
    category: "Field service",
    status: "Ready to Review",
    businessProblem: "Crews finish jobs but missing photos and slow handoffs delay invoicing and missed revenue follow-up.",
    triggerType: "Job marked complete",
    sourceChannel: "File upload",
    desiredActions: ["Create or update record", "Notify internal team", "Update status"],
    toolsInUse: ["Google Forms", "Google Sheets", "Google Drive"],
    sourceOfTruth: "Google Sheet",
    rolesInvolved: ["Field lead", "Admin", "Owner"],
    requiredDataFields: ["Job ID", "Customer name", "Photos"],
    exceptionRules: ["Missing photo / proof", "Missing required field"],
    humanReviewPoint: "Owner review",
    frequency: "Per event",
    volume: "High",
    successMetric: "Invoice-ready closeout within 24 hours.",
    manualFallback: "Crew lead texts admin and admin updates the tracker manually.",
    optionalNotes: "",
    ...overrides,
  };
}

function fakeStorage(initial = {}) {
  const data = { ...initial };
  return { getItem: (key) => (Object.hasOwn(data, key) ? data[key] : null), setItem: (key, value) => { data[key] = String(value); }, data };
}

test("automation category starter template generation includes all sections", () => {
  const generated = generateAutomationPlan(input());
  assert.deepEqual(Object.keys(generated.sections), AUTOMATION_SECTION_TITLES);
  assert.match(generated.sections["Automation Summary"], /completed jobs|closeout/i);
});

test("automation trigger template generation appears in Trigger section", () => {
  const generated = generateAutomationPlan(input({ triggerType: "Invoice overdue", category: "Billing / collections" }));
  assert.match(generated.sections.Trigger, /overdue threshold/i);
});

test("automation action blocks are generated in selected order", () => {
  const generated = generateAutomationPlan(input({ desiredActions: ["Send email", "Create task", "Update status"] }));
  assert.match(generated.sections["Automation Flow"], /4\. Send the correct email/);
  assert.match(generated.sections["Automation Flow"], /5\. Create a task/);
});

test("automation tool recommendation defaults when no tools are selected", () => {
  const generated = generateAutomationPlan(input({ toolsInUse: [], sourceOfTruth: "None yet", category: "Document collection" }));
  assert.match(generated.sections["Recommended Tool Stack"], /Airtable|Google Forms|Make|Zapier/);
});

test("automation exception rule generation includes selected patterns", () => {
  const generated = generateAutomationPlan(input({ exceptionRules: ["Duplicate record", "No response after SLA"] }));
  assert.match(generated.sections["Exception Rules"], /find\/update path/);
  assert.match(generated.sections["Exception Rules"], /human owner/);
});

test("automation human review points are generated for approvals and customer-facing actions", () => {
  const generated = generateAutomationPlan(input({ desiredActions: ["Send email"], humanReviewPoint: "Manager approval" }));
  assert.match(generated.sections["Human Review Points"], /Manager approval/);
  assert.match(generated.sections["Human Review Points"], /customer-facing/);
});

test("automation complexity score threshold logic", () => {
  const score = scoreComplexity(input({ toolsInUse: ["QuickBooks", "Airtable", "Zapier", "Gmail"], desiredActions: ["Send email", "Send reminder", "Draft invoice"], exceptionRules: ["Amount over threshold", "No response after SLA"], humanReviewPoint: "Owner review" }));
  assert.equal(score.label, "High");
});

test("automation impact score threshold logic", () => {
  const score = scoreImpact(input({ category: "Sales follow-up", frequency: "Weekly", volume: "High", desiredActions: ["Send reminder", "Update status"] }));
  assert.equal(score.label, "High");
});

test("automation Markdown export contains all sections and Mermaid block", () => {
  const plan = createAutomationPlan(input());
  const markdown = automationPlanToMarkdown(plan);
  AUTOMATION_SECTION_TITLES.forEach((title) => assert.match(markdown, new RegExp(`## ${title}`)));
  assert.match(markdown, /```mermaid/);
});

test("automation checklist-only export", () => {
  const plan = createAutomationPlan(input());
  addAutomationChecklistItem(plan, "Confirm closeout fields");
  const markdown = automationChecklistToMarkdown(plan);
  assert.match(markdown, /Implementation Checklist/);
  assert.doesNotMatch(markdown, /## Automation Flow/);
});

test("automation JSON export/import round trip", () => {
  const plan = createAutomationPlan(input());
  const parsed = parseAutomationBackup(automationPlansToBackup([plan]));
  assert.equal(parsed[0].automationName, plan.automationName);
});

test("automation invalid JSON import rejection", () => {
  assert.throws(() => parseAutomationBackup("not json"), /Invalid automation JSON backup/);
  const plan = createAutomationPlan(input({ category: "Field service" }));
  plan.category = "Bad";
  assert.throws(() => parseAutomationBackup(automationPlansToBackup([plan])), /invalid category/);
});

test("duplicate automation plan creates new id and preserves content", () => {
  const plan = createAutomationPlan(input());
  const copy = duplicateAutomationPlan(plan);
  assert.notEqual(copy.id, plan.id);
  assert.deepEqual(copy.sections, plan.sections);
});

test("automation local storage load/save", () => {
  const storage = fakeStorage();
  const plan = createAutomationPlan(input());
  saveAutomationPlans([plan], storage);
  const loaded = loadSavedAutomationPlans(storage);
  assert.equal(loaded[0].automationName, plan.automationName);
});

test("index remains direct-open safe for Automation Builder", async () => {
  const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /id="automationMode"/);
  assert.match(html, /<script src="app\.bundle\.js"><\/script>/);
  assert.doesNotMatch(html, /type="module"/);
});

test("automation list rendering avoids innerHTML for user names", async () => {
  const source = await readFile(new URL("../app.js", import.meta.url), "utf8");
  assert.doesNotMatch(source, /innerHTML/);
  assert.match(source, /name\.textContent = plan\.automationName/);
});

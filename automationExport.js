import { AUTOMATION_CATEGORIES, AUTOMATION_SECTION_TITLES, AUTOMATION_STATUSES, AUTOMATION_TRIGGER_TYPES, checklistToAutomationSection } from "./automationGenerator.js";

function fmt(value) { return value ? new Date(value).toLocaleString() : "Not saved yet"; }
function nonEmpty(value) { return typeof value === "string" && value.trim().length > 0; }
function checklistMarkdown(checklist) {
  return (checklist || []).map((item) => `- [${item.completed ? "x" : " "}] ${item.text}${item.notes ? `\n  - Note: ${item.notes}` : ""}`).join("\n") || "- [ ] Add implementation tasks.";
}

export function automationPlanToMarkdown(plan) {
  const lines = [
    `# Automation Plan: ${plan.automationName}`,
    "",
    plan.clientName ? `**Client:** ${plan.clientName}` : null,
    plan.industry ? `**Industry:** ${plan.industry}` : null,
    `**Category:** ${plan.category}`,
    `**Status:** ${plan.status}`,
    `**Last updated:** ${fmt(plan.updatedAt)}`,
    "",
  ].filter((line) => line !== null);
  AUTOMATION_SECTION_TITLES.forEach((title) => {
    lines.push(`## ${title}`, "");
    if (title === "Implementation Checklist") {
      lines.push(checklistMarkdown(plan.checklist), "");
    } else if (title === "Mermaid Flowchart") {
      lines.push("```mermaid", plan.sections?.[title] || "flowchart TD\n    A[Trigger] --> B[Action]", "```", "");
    } else {
      lines.push(plan.sections?.[title] || "_Add details._", "");
    }
  });
  return lines.join("\n").trimEnd() + "\n";
}

export function automationChecklistToMarkdown(plan) {
  return [`# ${plan.automationName} — Implementation Checklist`, "", `**Status:** ${plan.status}`, `**Last updated:** ${fmt(plan.updatedAt)}`, "", checklistMarkdown(plan.checklist), ""].join("\n");
}

export function automationPlansToBackup(plans) {
  return JSON.stringify({ version: 1, exportedAt: new Date().toISOString(), automationPlans: plans }, null, 2);
}

function normalizeDate(value) {
  return typeof value === "string" && !Number.isNaN(Date.parse(value)) ? value : new Date().toISOString();
}

function validateChecklistItem(item, planName, index) {
  if (!item || typeof item !== "object" || Array.isArray(item)) throw new Error(`Invalid automation JSON backup. Checklist item ${index + 1} in "${planName}" must be an object.`);
  if (!nonEmpty(item.id)) throw new Error(`Invalid automation JSON backup. Checklist item ${index + 1} in "${planName}" is missing a valid id.`);
  if (typeof item.text !== "string") throw new Error(`Invalid automation JSON backup. Checklist item ${index + 1} in "${planName}" must have text as a string.`);
  if (typeof item.completed !== "boolean") throw new Error(`Invalid automation JSON backup. Checklist item ${index + 1} in "${planName}" must have completed as true or false.`);
  if (item.notes !== undefined && typeof item.notes !== "string") throw new Error(`Invalid automation JSON backup. Checklist item ${index + 1} in "${planName}" must have notes as a string when provided.`);
  return { id: item.id, text: item.text, completed: item.completed, notes: item.notes || "" };
}

function validatePlan(plan, index) {
  if (!plan || typeof plan !== "object" || Array.isArray(plan)) throw new Error(`Invalid automation JSON backup. Plan ${index + 1} must be an object.`);
  if (!nonEmpty(plan.id)) throw new Error(`Invalid automation JSON backup. Plan ${index + 1} is missing a valid id.`);
  if (!nonEmpty(plan.automationName)) throw new Error(`Invalid automation JSON backup. Plan ${index + 1} is missing a valid automation name.`);
  if (!AUTOMATION_CATEGORIES.includes(plan.category)) throw new Error(`Invalid automation JSON backup. "${plan.automationName}" has an invalid category.`);
  if (!AUTOMATION_STATUSES.includes(plan.status)) throw new Error(`Invalid automation JSON backup. "${plan.automationName}" has an invalid status.`);
  if (!AUTOMATION_TRIGGER_TYPES.includes(plan.triggerType)) throw new Error(`Invalid automation JSON backup. "${plan.automationName}" has an invalid trigger type.`);
  if (!plan.sections || typeof plan.sections !== "object" || Array.isArray(plan.sections)) throw new Error(`Invalid automation JSON backup. "${plan.automationName}" must include a sections object.`);
  if (!Array.isArray(plan.checklist)) throw new Error(`Invalid automation JSON backup. "${plan.automationName}" must include a checklist array.`);
  const checklist = plan.checklist.map((item, itemIndex) => validateChecklistItem(item, plan.automationName, itemIndex));
  const sections = {};
  AUTOMATION_SECTION_TITLES.forEach((title) => {
    if (title === "Implementation Checklist") {
      sections[title] = checklistToAutomationSection(checklist);
      return;
    }
    if (typeof plan.sections[title] !== "string") throw new Error(`Invalid automation JSON backup. "${plan.automationName}" is missing the required "${title}" section.`);
    sections[title] = plan.sections[title];
  });
  return { ...plan, automationName: plan.automationName.trim(), clientName: typeof plan.clientName === "string" ? plan.clientName : "", industry: typeof plan.industry === "string" ? plan.industry : "", sections, checklist, updatedAt: normalizeDate(plan.updatedAt) };
}

export function parseAutomationBackup(jsonText) {
  let parsed;
  try { parsed = JSON.parse(jsonText); } catch { throw new Error("Invalid automation JSON backup. Choose a valid Automation Builder backup file."); }
  const plans = Array.isArray(parsed) ? parsed : parsed?.automationPlans;
  if (!Array.isArray(plans)) throw new Error("Invalid automation JSON backup. The file must contain an automationPlans array.");
  return plans.map(validatePlan);
}

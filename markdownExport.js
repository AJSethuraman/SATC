import { PROCESS_CATEGORIES, SECTION_TITLES, STATUS_OPTIONS, checklistToSection } from "./processGenerator.js";

function formatDate(value) {
  if (!value) return "Not saved yet";
  return new Date(value).toLocaleString();
}

function checklistMarkdown(checklist) {
  if (!checklist || !checklist.length) return "- [ ] Add checklist items.";
  return checklist
    .map((item) => {
      const status = item.completed ? "x" : " ";
      const note = item.notes ? `\n  - Note: ${item.notes}` : "";
      return `- [${status}] ${item.text}${note}`;
    })
    .join("\n");
}

export function processToMarkdown(process) {
  const lines = [
    `# ${process.name}`,
    "",
    process.businessName ? `**Business/client:** ${process.businessName}` : null,
    process.industry ? `**Industry/business type:** ${process.industry}` : null,
    `**Category:** ${process.category}`,
    `**Status:** ${process.status}`,
    `**Last updated:** ${formatDate(process.updatedAt)}`,
    "",
  ].filter((line) => line !== null);

  SECTION_TITLES.forEach((title) => {
    lines.push(`## ${title}`, "");
    if (title === "Internal checklist") {
      lines.push(checklistMarkdown(process.checklist), "");
    } else {
      lines.push(process.sections?.[title] || "_Add details._", "");
    }
  });

  return lines.join("\n").trimEnd() + "\n";
}

export function checklistToMarkdown(process) {
  return [`# ${process.name} — Internal Checklist`, "", `**Status:** ${process.status}`, `**Last updated:** ${formatDate(process.updatedAt)}`, "", checklistMarkdown(process.checklist), ""].join("\n");
}

export function processesToBackup(processes) {
  return JSON.stringify({ version: 1, exportedAt: new Date().toISOString(), processes }, null, 2);
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeUpdatedAt(value) {
  if (typeof value === "string" && !Number.isNaN(Date.parse(value))) {
    return value;
  }
  return new Date().toISOString();
}

function validateChecklistItem(item, processName, index) {
  if (!item || typeof item !== "object" || Array.isArray(item)) {
    throw new Error(`Invalid imported JSON backup. Checklist item ${index + 1} in "${processName}" must be an object.`);
  }
  if (!isNonEmptyString(item.id)) {
    throw new Error(`Invalid imported JSON backup. Checklist item ${index + 1} in "${processName}" is missing a valid id.`);
  }
  if (typeof item.text !== "string") {
    throw new Error(`Invalid imported JSON backup. Checklist item ${index + 1} in "${processName}" must have text as a string.`);
  }
  if (typeof item.completed !== "boolean") {
    throw new Error(`Invalid imported JSON backup. Checklist item ${index + 1} in "${processName}" must have completed as true or false.`);
  }
  if (item.notes !== undefined && typeof item.notes !== "string") {
    throw new Error(`Invalid imported JSON backup. Checklist item ${index + 1} in "${processName}" must have notes as a string when provided.`);
  }
  return {
    id: item.id,
    text: item.text,
    completed: item.completed,
    notes: item.notes || "",
  };
}

function validateImportedProcess(process, index) {
  if (!process || typeof process !== "object" || Array.isArray(process)) {
    throw new Error(`Invalid imported JSON backup. Process ${index + 1} must be an object.`);
  }
  if (!isNonEmptyString(process.id)) {
    throw new Error(`Invalid imported JSON backup. Process ${index + 1} is missing a valid id.`);
  }
  if (!isNonEmptyString(process.name)) {
    throw new Error(`Invalid imported JSON backup. Process ${index + 1} is missing a valid name.`);
  }
  if (!PROCESS_CATEGORIES.includes(process.category)) {
    throw new Error(`Invalid imported JSON backup. "${process.name}" has an invalid category.`);
  }
  if (!STATUS_OPTIONS.includes(process.status)) {
    throw new Error(`Invalid imported JSON backup. "${process.name}" has an invalid status.`);
  }
  if (!process.sections || typeof process.sections !== "object" || Array.isArray(process.sections)) {
    throw new Error(`Invalid imported JSON backup. "${process.name}" must include a sections object.`);
  }
  if (!Array.isArray(process.checklist)) {
    throw new Error(`Invalid imported JSON backup. "${process.name}" must include a checklist array.`);
  }

  const checklist = process.checklist.map((item, itemIndex) => validateChecklistItem(item, process.name, itemIndex));
  const sections = {};
  SECTION_TITLES.forEach((title) => {
    if (title === "Internal checklist") {
      sections[title] = typeof process.sections[title] === "string" ? process.sections[title] : checklistToSection(checklist);
      return;
    }
    if (typeof process.sections[title] !== "string") {
      throw new Error(`Invalid imported JSON backup. "${process.name}" is missing the required "${title}" section.`);
    }
    sections[title] = process.sections[title];
  });
  sections["Internal checklist"] = checklistToSection(checklist);

  return {
    id: process.id,
    name: process.name.trim(),
    businessName: typeof process.businessName === "string" ? process.businessName : "",
    industry: typeof process.industry === "string" ? process.industry : "",
    category: process.category,
    status: process.status,
    rawDescription: typeof process.rawDescription === "string" ? process.rawDescription : "",
    sections,
    checklist,
    updatedAt: normalizeUpdatedAt(process.updatedAt),
  };
}

export function parseBackup(jsonText) {
  let parsed;
  try {
    parsed = JSON.parse(jsonText);
  } catch {
    throw new Error("Invalid imported JSON backup. Choose a valid Process Builder backup file.");
  }

  const processes = Array.isArray(parsed) ? parsed : parsed?.processes;
  if (!Array.isArray(processes)) {
    throw new Error("Invalid imported JSON backup. The file must contain a processes array.");
  }

  return processes.map(validateImportedProcess);
}

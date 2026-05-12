import { SECTION_TITLES } from "./processGenerator.js";

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

  const invalid = processes.some((process) => !process || !process.id || !process.name || !process.category || !process.status || !process.sections || !Array.isArray(process.checklist));
  if (invalid) {
    throw new Error("Invalid imported JSON backup. One or more saved processes is missing required fields.");
  }

  return processes;
}

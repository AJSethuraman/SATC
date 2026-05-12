const STORAGE_KEY = "process-builder-processes-v1";

const SECTION_TITLES = [
  "Objective",
  "Trigger event",
  "Frequency",
  "Required inputs",
  "Tools/systems used",
  "Responsible role",
  "Step-by-step SOP",
  "Decision points",
  "Quality control checks",
  "Common exceptions",
  "Client/vendor communication points",
  "Internal checklist",
  "Risks or failure points",
  "Automation opportunities",
  "Suggested next improvement",
];

const TYPE_RULES = {
  Tax: {
    role: "Tax preparer or tax client service coordinator",
    inputs: ["Client tax documents", "Prior-year return", "Engagement letter", "Open items list"],
    tools: ["Tax preparation software", "Client portal", "Document storage", "E-signature tool"],
    qc: ["Confirm engagement letter is signed", "Reconcile source documents to return inputs", "Review diagnostics before delivery"],
    automation: ["Portal reminders for missing documents", "Template-based open item emails", "Status updates based on workflow stage"],
  },
  Bookkeeping: {
    role: "Bookkeeper or accounting manager",
    inputs: ["Bank and credit card feeds", "Receipts", "Payroll reports", "Prior close checklist"],
    tools: ["Accounting system", "Bank portal", "Receipt capture tool", "Spreadsheet workpapers"],
    qc: ["Reconcile all balance sheet accounts", "Review uncategorized transactions", "Compare P&L to prior period"],
    automation: ["Bank rule cleanup", "Recurring journal templates", "Auto-generated close checklist"],
  },
  Admin: {
    role: "Administrative coordinator",
    inputs: ["Request details", "Approvals", "Due date", "Contact information"],
    tools: ["Email", "Shared drive", "Task manager", "Calendar"],
    qc: ["Confirm all required fields are complete", "Validate approval before final action", "Archive final records"],
    automation: ["Intake form routing", "Reminder sequences", "Document naming templates"],
  },
  Sales: {
    role: "Sales owner or account executive",
    inputs: ["Lead source", "Prospect notes", "Qualification criteria", "Proposal template"],
    tools: ["CRM", "Email", "Scheduling link", "Proposal software"],
    qc: ["Confirm next step is logged", "Validate prospect fit", "Review proposal for pricing accuracy"],
    automation: ["Lead capture to CRM", "Follow-up email sequences", "Proposal status alerts"],
  },
  "Client onboarding": {
    role: "Client onboarding coordinator",
    inputs: ["Signed agreement", "Client contact details", "System access needs", "Initial document request"],
    tools: ["Client portal", "CRM", "E-signature tool", "Task manager"],
    qc: ["Confirm contract and payment setup", "Validate portal access", "Check that welcome email was sent"],
    automation: ["Welcome packet delivery", "Task template creation", "Automatic reminders for setup tasks"],
  },
  "Follow-up / collections": {
    role: "Accounts receivable or client success owner",
    inputs: ["Invoice or request details", "Due date", "Contact history", "Escalation rules"],
    tools: ["Accounting system", "Email", "CRM", "Payment processor"],
    qc: ["Confirm balance is still open", "Check for prior disputes", "Document every outreach attempt"],
    automation: ["Scheduled payment reminders", "Escalation alerts", "Payment link insertion"],
  },
  "General operations": {
    role: "Operations owner",
    inputs: ["Request details", "Standard procedure", "Required approvals", "Completion criteria"],
    tools: ["Task manager", "Shared drive", "Email", "Reporting dashboard"],
    qc: ["Confirm owner and due date", "Check completion evidence", "Update the process log"],
    automation: ["Task routing rules", "Recurring process templates", "Exception reporting"],
  },
};

const STARTER_PROCESSES = [
  {
    name: "Monthly bookkeeping close",
    type: "Bookkeeping",
    status: "In Use",
    rawDescription:
      "Each month we import bank and credit card transactions, categorize anything uncoded, request receipts from the client, reconcile accounts, review payroll and loan balances, then send financial statements with a short summary.",
  },
  {
    name: "New tax client onboarding",
    type: "Client onboarding",
    status: "Draft",
    rawDescription:
      "After a prospect accepts the tax engagement, send the engagement letter, collect organizer details, create the portal, request prior returns and current year documents, assign the preparer, and confirm the expected filing timeline.",
  },
  {
    name: "Missing document follow-up",
    type: "Tax",
    status: "Needs Review",
    rawDescription:
      "When a return is waiting on documents, review the open items list, email the client with a clear request, set a reminder, update the workflow status, and escalate by phone if the deadline is close.",
  },
  {
    name: "Invoice collection follow-up",
    type: "Follow-up / collections",
    status: "In Use",
    rawDescription:
      "Every week check overdue invoices, verify no payment came in, send a friendly reminder with the payment link, note the account, and escalate old balances to the owner.",
  },
  {
    name: "Employee onboarding",
    type: "Admin",
    status: "Draft",
    rawDescription:
      "When a candidate accepts, collect employment forms, set up payroll, create system accounts, schedule orientation, prepare equipment, and confirm the manager has a first-week plan.",
  },
  {
    name: "Vendor bill approval",
    type: "General operations",
    status: "Draft",
    rawDescription:
      "When a vendor bill arrives, save the invoice, match it to the purchase request, send it to the department owner for approval, enter it into accounting, schedule payment, and file proof of approval.",
  },
];

const state = {
  processes: [],
  activeId: null,
};

const elements = {
  processForm: document.querySelector("#processForm"),
  processName: document.querySelector("#processName"),
  processType: document.querySelector("#processType"),
  statusTag: document.querySelector("#statusTag"),
  rawDescription: document.querySelector("#rawDescription"),
  sectionsContainer: document.querySelector("#sectionsContainer"),
  sectionTemplate: document.querySelector("#sectionTemplate"),
  processList: document.querySelector("#processList"),
  processCount: document.querySelector("#processCount"),
  activeProcessTitle: document.querySelector("#activeProcessTitle"),
  activeProcessMeta: document.querySelector("#activeProcessMeta"),
  saveState: document.querySelector("#saveState"),
  searchInput: document.querySelector("#searchInput"),
  newProcessBtn: document.querySelector("#newProcessBtn"),
  saveProcessBtn: document.querySelector("#saveProcessBtn"),
  duplicateProcessBtn: document.querySelector("#duplicateProcessBtn"),
  deleteProcessBtn: document.querySelector("#deleteProcessBtn"),
  exportMarkdownBtn: document.querySelector("#exportMarkdownBtn"),
  exportChecklistBtn: document.querySelector("#exportChecklistBtn"),
};

function createId() {
  return `process-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function sentenceCase(text) {
  const trimmed = text.trim();
  return trimmed ? trimmed.charAt(0).toUpperCase() + trimmed.slice(1) : trimmed;
}

function splitIntoSteps(description) {
  const normalized = description
    .replace(/\r/g, "")
    .split(/\n|\.|;|\bthen\b|\band then\b|\bafter that\b|\bnext\b/i)
    .map((part) => part.replace(/^[-*\d.)\s]+/, "").trim())
    .filter((part) => part.length > 2);

  if (normalized.length) {
    return normalized.map((step, index) => `${index + 1}. ${sentenceCase(step)}.`);
  }

  return [
    "1. Capture the request or trigger.",
    "2. Gather required information and documents.",
    "3. Complete the work using the standard tools.",
    "4. Review quality control checks.",
    "5. Communicate completion and archive the record.",
  ];
}

function detectFrequency(description) {
  const text = description.toLowerCase();
  if (/daily|each day|every day/.test(text)) return "Daily or each business day.";
  if (/weekly|each week|every week/.test(text)) return "Weekly.";
  if (/monthly|each month|month-end|month end/.test(text)) return "Monthly.";
  if (/quarterly|each quarter/.test(text)) return "Quarterly.";
  if (/annually|yearly|each year|tax season/.test(text)) return "Annually or seasonally.";
  if (/when|after|once|as soon as/.test(text)) return "Event-driven when the trigger occurs.";
  return "To be confirmed; add the expected cadence.";
}

function detectTrigger(description, type) {
  const sentences = description.split(/[.!?\n]/).map((s) => s.trim()).filter(Boolean);
  const triggerSentence = sentences.find((sentence) => /when|after|once|every|each/i.test(sentence));
  if (triggerSentence) return sentenceCase(triggerSentence) + ".";

  const fallback = {
    Tax: "A tax engagement or filing task is ready to begin.",
    Bookkeeping: "A new accounting period is ready to close or review.",
    Admin: "An internal or client administrative request is received.",
    Sales: "A new lead or sales opportunity is created.",
    "Client onboarding": "A client signs or verbally accepts the engagement.",
    "Follow-up / collections": "A due date passes or a requested item remains outstanding.",
    "General operations": "A recurring operational task reaches its scheduled start point.",
  };
  return fallback[type] || fallback["General operations"];
}

function findMentionedTools(description, defaults) {
  const knownTools = [
    "email",
    "spreadsheet",
    "excel",
    "quickbooks",
    "xero",
    "portal",
    "crm",
    "calendar",
    "slack",
    "teams",
    "payroll",
    "bank",
    "task manager",
    "drive",
  ];
  const text = description.toLowerCase();
  const matches = knownTools.filter((tool) => text.includes(tool));
  return [...new Set([...matches.map(sentenceCase), ...defaults])];
}

function buildSections({ name, type, rawDescription }) {
  const rules = TYPE_RULES[type] || TYPE_RULES["General operations"];
  const steps = splitIntoSteps(rawDescription);
  const tools = findMentionedTools(rawDescription, rules.tools);

  return {
    "Objective": `Create a reliable, repeatable process for ${name || "this process"} that reduces missed steps and makes ownership clear.`,
    "Trigger event": detectTrigger(rawDescription, type),
    "Frequency": detectFrequency(rawDescription),
    "Required inputs": rules.inputs.map((item) => `- ${item}`).join("\n") + "\n- Add any process-specific documents or approvals.",
    "Tools/systems used": tools.map((item) => `- ${item}`).join("\n"),
    "Responsible role": rules.role,
    "Step-by-step SOP": steps.join("\n"),
    "Decision points": [
      "- Is all required information available before work begins?",
      "- Does the item meet criteria for standard handling, or does it need escalation?",
      "- Is client/vendor/internal approval required before completion?",
    ].join("\n"),
    "Quality control checks": rules.qc.map((item) => `- ${item}`).join("\n"),
    "Common exceptions": [
      "- Missing or incomplete information.",
      "- Owner or approver is unavailable.",
      "- Deadline is accelerated or already past due.",
      "- Source records do not match expected amounts or status.",
    ].join("\n"),
    "Client/vendor communication points": [
      "- Confirm receipt of the request or trigger.",
      "- Send a concise list of missing items or decisions needed.",
      "- Provide a status update when work moves to review or completion.",
      "- Confirm completion and next expected action.",
    ].join("\n"),
    "Internal checklist": steps.map((step) => `- [ ] ${step.replace(/^\d+\.\s*/, "")}`).join("\n"),
    "Risks or failure points": [
      "- Work starts without complete inputs.",
      "- Status is not updated, causing duplicate work or missed follow-up.",
      "- Quality review is skipped under time pressure.",
      "- Communication is not documented in the system of record.",
    ].join("\n"),
    "Automation opportunities": rules.automation.map((item) => `- ${item}`).join("\n"),
    "Suggested next improvement": "Turn the strongest checklist items into a reusable task template, assign owners, and review the process after the next two cycles.",
  };
}

function makeProcess({ name, type, status, rawDescription }) {
  const process = {
    id: createId(),
    name,
    type,
    status,
    rawDescription,
    sections: buildSections({ name, type, rawDescription }),
    updatedAt: new Date().toISOString(),
  };
  return process;
}

function loadProcesses() {
  const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  if (saved.length) return saved;
  const starters = STARTER_PROCESSES.map(makeProcess);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(starters));
  return starters;
}

function persistProcesses() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.processes));
  elements.saveState.textContent = `Saved locally at ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

function getActiveProcess() {
  return state.processes.find((process) => process.id === state.activeId) || null;
}

function renderList() {
  const query = elements.searchInput.value.toLowerCase();
  const filtered = state.processes.filter((process) =>
    [process.name, process.type, process.status].join(" ").toLowerCase().includes(query),
  );

  elements.processCount.textContent = `${state.processes.length} saved`;
  elements.processList.innerHTML = "";

  filtered.forEach((process) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `process-item${process.id === state.activeId ? " active" : ""}`;
    item.innerHTML = `<strong>${process.name}</strong><span>${process.type} • ${process.status}</span>`;
    item.addEventListener("click", () => selectProcess(process.id));
    elements.processList.append(item);
  });
}

function renderEditor() {
  const process = getActiveProcess();
  elements.sectionsContainer.innerHTML = "";

  if (!process) {
    elements.activeProcessTitle.textContent = "Untitled process";
    elements.activeProcessMeta.textContent = "Generate a process structure to begin editing.";
    return;
  }

  elements.processName.value = process.name;
  elements.processType.value = process.type;
  elements.statusTag.value = process.status;
  elements.rawDescription.value = process.rawDescription;
  elements.activeProcessTitle.textContent = process.name;
  elements.activeProcessMeta.textContent = `${process.type} • ${process.status} • Last updated ${new Date(process.updatedAt).toLocaleString()}`;

  SECTION_TITLES.forEach((title) => {
    const fragment = elements.sectionTemplate.content.cloneNode(true);
    const label = fragment.querySelector(".section-title");
    const textarea = fragment.querySelector(".section-textarea");
    label.textContent = title;
    textarea.value = process.sections[title] || "";
    textarea.dataset.section = title;
    textarea.addEventListener("input", () => {
      process.sections[title] = textarea.value;
      process.updatedAt = new Date().toISOString();
      persistProcesses();
      renderList();
    });
    elements.sectionsContainer.append(fragment);
  });
}

function selectProcess(id) {
  state.activeId = id;
  renderList();
  renderEditor();
}

function collectFormValues() {
  return {
    name: elements.processName.value.trim() || "Untitled process",
    type: elements.processType.value,
    status: elements.statusTag.value,
    rawDescription: elements.rawDescription.value.trim(),
  };
}

function saveActiveFromForm({ rebuildSections = false } = {}) {
  const values = collectFormValues();
  let process = getActiveProcess();

  if (!process) {
    process = makeProcess(values);
    state.processes.unshift(process);
    state.activeId = process.id;
  } else {
    process.name = values.name;
    process.type = values.type;
    process.status = values.status;
    process.rawDescription = values.rawDescription;
    if (rebuildSections) {
      process.sections = buildSections(values);
    }
    process.updatedAt = new Date().toISOString();
  }

  persistProcesses();
  renderList();
  renderEditor();
}

function resetForNewProcess() {
  state.activeId = null;
  elements.processForm.reset();
  elements.sectionsContainer.innerHTML = "";
  elements.activeProcessTitle.textContent = "New process";
  elements.activeProcessMeta.textContent = "Enter rough notes and generate a structure.";
  renderList();
}

function duplicateActiveProcess() {
  const process = getActiveProcess();
  if (!process) return;
  const copy = structuredClone(process);
  copy.id = createId();
  copy.name = `${process.name} Copy`;
  copy.status = "Draft";
  copy.updatedAt = new Date().toISOString();
  state.processes.unshift(copy);
  state.activeId = copy.id;
  persistProcesses();
  renderList();
  renderEditor();
}

function deleteActiveProcess() {
  const process = getActiveProcess();
  if (!process) return;
  const confirmed = window.confirm(`Delete "${process.name}" from local storage?`);
  if (!confirmed) return;
  state.processes = state.processes.filter((item) => item.id !== process.id);
  state.activeId = state.processes[0]?.id || null;
  persistProcesses();
  renderList();
  renderEditor();
}

function toMarkdown(process, checklistOnly = false) {
  if (checklistOnly) {
    return `# ${process.name} Checklist\n\n${process.sections["Internal checklist"] || "- [ ] Add checklist items."}\n`;
  }

  const header = [`# ${process.name}`, "", `**Type:** ${process.type}`, `**Status:** ${process.status}`, ""].join("\n");
  const body = SECTION_TITLES.map((title) => `## ${title}\n\n${process.sections[title] || "_Add details._"}`).join("\n\n");
  return `${header}${body}\n`;
}

function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function exportActive(checklistOnly = false) {
  const process = getActiveProcess();
  if (!process) return;
  const slug = process.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "process";
  const filename = checklistOnly ? `${slug}-checklist.md` : `${slug}-sop.md`;
  downloadText(filename, toMarkdown(process, checklistOnly));
}

function bindEvents() {
  elements.processForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveActiveFromForm({ rebuildSections: true });
  });
  elements.saveProcessBtn.addEventListener("click", () => saveActiveFromForm());
  elements.newProcessBtn.addEventListener("click", resetForNewProcess);
  elements.duplicateProcessBtn.addEventListener("click", duplicateActiveProcess);
  elements.deleteProcessBtn.addEventListener("click", deleteActiveProcess);
  elements.exportMarkdownBtn.addEventListener("click", () => exportActive(false));
  elements.exportChecklistBtn.addEventListener("click", () => exportActive(true));
  elements.searchInput.addEventListener("input", renderList);
}

function init() {
  state.processes = loadProcesses();
  state.activeId = state.processes[0]?.id || null;
  bindEvents();
  renderList();
  renderEditor();
}

init();

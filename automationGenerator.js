export const AUTOMATION_STORAGE_KEY = "process-builder-automation-plans-v1";

export const AUTOMATION_CATEGORIES = ["Field service", "Billing / collections", "Client onboarding", "Document collection", "Sales follow-up", "Employee onboarding", "Custom"];
export const AUTOMATION_STATUSES = ["Draft", "Ready to Review", "Ready to Build", "Implemented", "Needs Review", "Deprecated"];
export const AUTOMATION_TRIGGER_TYPES = ["New lead received", "Form submitted", "Document received", "Job marked complete", "Invoice overdue", "Proposal accepted", "Employee accepted", "Scheduled time", "Status changed", "Custom"];
export const AUTOMATION_SOURCE_CHANNELS = ["Email", "Web form", "Spreadsheet row", "CRM / deal stage", "Job system", "Phone/text manually logged", "File upload", "Custom"];
export const AUTOMATION_ACTIONS = ["Send email", "Send reminder", "Create task", "Create or update record", "Create folder", "Request missing information", "Notify internal team", "Update status", "Draft invoice", "Create summary/report", "Custom"];
export const AUTOMATION_TOOLS = ["Gmail", "Google Forms", "Google Sheets", "Google Drive", "Airtable", "Zapier", "Make", "Slack", "QuickBooks", "Jobber", "Housecall Pro", "CRM", "HR app", "Custom"];
export const AUTOMATION_SOURCES_OF_TRUTH = ["Google Sheet", "Airtable base", "Zapier Table", "Existing CRM / PM system", "None yet"];
export const AUTOMATION_ROLES = ["Owner", "Admin", "Field lead", "Sales rep", "Bookkeeper", "HR", "Customer / client", "Employee", "Vendor", "Custom"];
export const AUTOMATION_EXCEPTION_RULES = ["Missing required field", "Missing document", "Missing photo / proof", "Duplicate record", "Owner approval required", "Amount over threshold", "Unpaid balance", "No response after SLA", "Custom"];
export const AUTOMATION_REVIEW_POINTS = ["None", "Admin review", "Owner review", "Manager approval"];
export const AUTOMATION_FREQUENCIES = ["Per event", "Daily", "Weekly", "Monthly"];
export const AUTOMATION_VOLUMES = ["Low", "Medium", "High"];
export const AUTOMATION_INDUSTRIES = ["Home services", "Professional services", "Medical/admin", "Retail", "Agency", "Property management", "Custom"];

export const AUTOMATION_SECTION_TITLES = [
  "Automation Summary",
  "Business Problem Being Solved",
  "Trigger",
  "Required Inputs",
  "Source of Truth",
  "Systems Involved",
  "Roles Involved",
  "Automation Flow",
  "Exception Rules",
  "Human Review Points",
  "Data Fields Needed",
  "Recommended Tool Stack",
  "Complexity",
  "Impact",
  "First Version Scope",
  "Manual Fallback",
  "Implementation Checklist",
  "Client-facing Summary",
  "Next Best Automation",
  "Mermaid Flowchart",
];

const AUTOMATION_CATEGORY_TEMPLATES = {
  "Field service": {
    summary: "Standardize how completed jobs are captured, reviewed, and handed to the office for closeout or invoice prep.",
    inputs: ["Customer name", "Job address", "Job ID", "Completion date", "Photos or proof", "Crew notes"],
    fields: ["job_id", "customer_name", "address", "crew_lead", "completion_date", "photos_url", "closeout_status"],
    next: "Invoice-ready closeout record -> invoice preparation and customer follow-up reminder.",
  },
  "Billing / collections": {
    summary: "Standardize invoice follow-up, reminder timing, and escalation for overdue balances.",
    inputs: ["Invoice number", "Customer name", "Amount due", "Due date", "Email address", "Reminder count"],
    fields: ["invoice_number", "customer_name", "amount_due", "due_date", "age_bucket", "reminder_count", "payment_status"],
    next: "Paid invoice -> receipt notification and cash application update.",
  },
  "Client onboarding": {
    summary: "Turn a new client or accepted proposal into a tracked onboarding workflow with clean handoffs.",
    inputs: ["Client name", "Main contact", "Email", "Service package", "Start date", "Assigned manager"],
    fields: ["client_name", "contact_email", "service_package", "assigned_manager", "folder_link", "onboarding_status"],
    next: "Document received -> update onboarding status and notify the assigned manager.",
  },
  "Document collection": {
    summary: "Track requested documents, missing items, reminder cadence, and review readiness.",
    inputs: ["Client or customer name", "Contact email", "Request list", "Due date", "Assigned reviewer", "Upload link"],
    fields: ["client_name", "email", "requested_items", "received_items", "due_date", "completeness_status", "folder_link"],
    next: "Complete document package -> start production or review checklist.",
  },
  "Sales follow-up": {
    summary: "Capture new leads, assign ownership, and ensure follow-up happens within the agreed response window.",
    inputs: ["Lead name", "Phone", "Email", "Service interest", "Lead source", "Assigned rep"],
    fields: ["lead_name", "email", "phone", "lead_source", "service_type", "assigned_rep", "follow_up_deadline", "status"],
    next: "Appointment set -> estimate or proposal follow-up sequence.",
  },
  "Employee onboarding": {
    summary: "Turn an accepted employee into a tracked setup workflow for paperwork, access, scheduling, and manager readiness.",
    inputs: ["Employee name", "Email", "Start date", "Role", "Manager", "Location"],
    fields: ["employee_name", "email", "role", "start_date", "manager", "paperwork_status", "access_status", "onboarding_status"],
    next: "Day-one complete -> 30-day check-in and training follow-up workflow.",
  },
  Custom: {
    summary: "Scope a small first version of this automation with a clear trigger, source of truth, exception path, and manual fallback.",
    inputs: ["Requester", "Trigger details", "Required data", "Owner", "Due date", "Success criteria"],
    fields: ["record_id", "owner", "trigger_date", "status", "next_action", "exception_flag"],
    next: "Stable first version -> automate the next recurring handoff or reminder.",
  },
};

const TRIGGER_TEMPLATES = {
  "New lead received": "A new lead is received from the selected source channel and needs ownership, follow-up, and status tracking.",
  "Form submitted": "A submitted form creates a new record and starts the automation flow.",
  "Document received": "A document or file upload is received and should be matched to the correct record.",
  "Job marked complete": "A job is marked complete and needs closeout review before downstream actions run.",
  "Invoice overdue": "An invoice crosses the overdue threshold and enters the reminder/escalation flow.",
  "Proposal accepted": "A proposal is accepted and the onboarding or delivery setup should begin.",
  "Employee accepted": "A candidate accepts the offer and onboarding setup should begin.",
  "Scheduled time": "A scheduled time arrives and the automation checks records that need action.",
  "Status changed": "A tracked record changes status and triggers the next action.",
  Custom: "A custom trigger starts the automation. Define the exact event before building.",
};

const ACTION_BLOCKS = {
  "Send email": "Send the correct email template to the customer/client, employee, vendor, or internal owner.",
  "Send reminder": "Queue a reminder based on due date, SLA, or no-response timing.",
  "Create task": "Create a task for the responsible human owner with due date and context.",
  "Create or update record": "Create a new record or update the matched existing record in the source of truth.",
  "Create folder": "Create or confirm the standard folder structure and save links on the record.",
  "Request missing information": "Send a focused request for missing information and mark the record incomplete until resolved.",
  "Notify internal team": "Notify the assigned team member or channel with the record link and next action.",
  "Update status": "Update status, timestamp, and owner so the workflow remains visible.",
  "Draft invoice": "Draft the invoice or invoice-prep task, but keep final approval human-owned in version one.",
  "Create summary/report": "Create a short summary for owner review or client delivery.",
  Custom: "Run the custom action after confirming required data and fallback behavior.",
};

const EXCEPTION_BLOCKS = {
  "Missing required field": "Stop downstream actions, mark `Incomplete Input`, notify owner/admin, and add a follow-up task.",
  "Missing document": "Hold workflow, request the missing document, and queue a reminder cadence.",
  "Missing photo / proof": "Hold closeout or delivery until required proof is attached and reviewed.",
  "Duplicate record": "Stop the create step, attempt a find/update path, and flag uncertain matches for review.",
  "Owner approval required": "Pause external communication until the owner approves the record or message.",
  "Amount over threshold": "Route to approval before billing, collections, or customer-facing actions continue.",
  "Unpaid balance": "Hold non-essential downstream work and notify billing/owner for review.",
  "No response after SLA": "Send a reminder, then escalate to the human owner if there is still no response.",
  Custom: "Document the custom exception, owner, stop condition, and manual fallback.",
};

export const AUTOMATION_STARTER_TEMPLATES = [
  { automationName: "Field service job closeout", clientName: "", industry: "Home services", category: "Field service", status: "Ready to Review", businessProblem: "Crews complete jobs but office staff receive inconsistent notes and missing photos, delaying invoice prep.", triggerType: "Job marked complete", sourceChannel: "Web form", desiredActions: ["Create or update record", "Notify internal team", "Update status"], toolsInUse: ["Google Forms", "Google Sheets", "Google Drive"], sourceOfTruth: "Google Sheet", rolesInvolved: ["Field lead", "Admin", "Owner"], requiredDataFields: ["Job ID", "Customer name", "Address", "Photos", "Crew notes"], exceptionRules: ["Missing photo / proof", "Missing required field", "Owner approval required"], humanReviewPoint: "Owner review", frequency: "Per event", volume: "Medium", successMetric: "Completed jobs are invoice-ready within 24 hours.", manualFallback: "Crew lead texts admin and admin enters the closeout in the tracker.", optionalNotes: "" },
  { automationName: "Overdue invoice follow-up", clientName: "", industry: "Professional services", category: "Billing / collections", status: "Ready to Review", businessProblem: "Overdue invoices are followed up inconsistently and owners hear about old balances too late.", triggerType: "Invoice overdue", sourceChannel: "Spreadsheet row", desiredActions: ["Send reminder", "Create or update record", "Notify internal team"], toolsInUse: ["QuickBooks", "Airtable", "Gmail", "Zapier"], sourceOfTruth: "Airtable base", rolesInvolved: ["Admin", "Owner", "Customer / client"], requiredDataFields: ["Invoice number", "Customer", "Due date", "Amount", "Email"], exceptionRules: ["Amount over threshold", "Duplicate record", "No response after SLA"], humanReviewPoint: "Owner review", frequency: "Weekly", volume: "Medium", successMetric: "Faster collection and fewer missed overdue balances.", manualFallback: "Admin reviews the aging report and sends manual reminders weekly.", optionalNotes: "" },
  { automationName: "New client onboarding", clientName: "", industry: "Professional services", category: "Client onboarding", status: "Ready to Review", businessProblem: "New clients are won but setup steps, folders, kickoff messages, and internal tasks happen inconsistently.", triggerType: "Proposal accepted", sourceChannel: "CRM / deal stage", desiredActions: ["Create or update record", "Create folder", "Send email", "Create task"], toolsInUse: ["Zapier", "Google Drive", "Gmail", "CRM"], sourceOfTruth: "Zapier Table", rolesInvolved: ["Sales rep", "Admin", "Customer / client", "Owner"], requiredDataFields: ["Client name", "Email", "Package", "Manager", "Start date"], exceptionRules: ["Missing required field", "Duplicate record"], humanReviewPoint: "Manager approval", frequency: "Per event", volume: "Medium", successMetric: "Every signed client receives a consistent kickoff within one business day.", manualFallback: "Admin creates folder and sends kickoff email from a template.", optionalNotes: "" },
  { automationName: "Missing document collection", clientName: "", industry: "Professional services", category: "Document collection", status: "Ready to Review", businessProblem: "Documents arrive through scattered emails and staff lose track of missing items.", triggerType: "Status changed", sourceChannel: "File upload", desiredActions: ["Request missing information", "Send reminder", "Update status"], toolsInUse: ["Airtable", "Google Drive", "Gmail"], sourceOfTruth: "Airtable base", rolesInvolved: ["Admin", "Customer / client"], requiredDataFields: ["Client", "Email", "Requested items", "Due date", "Folder link"], exceptionRules: ["Missing document", "Duplicate record", "No response after SLA"], humanReviewPoint: "Admin review", frequency: "Daily", volume: "High", successMetric: "Fewer stale missing-item requests and faster file completion.", manualFallback: "Staff sends manual missing-item email and updates the tracker.", optionalNotes: "" },
  { automationName: "New lead follow-up", clientName: "", industry: "Home services", category: "Sales follow-up", status: "Ready to Review", businessProblem: "Leads come in from forms and calls but follow-up timing is inconsistent and ownership is unclear.", triggerType: "New lead received", sourceChannel: "Web form", desiredActions: ["Create or update record", "Notify internal team", "Send email", "Send reminder"], toolsInUse: ["Zapier", "CRM", "Gmail", "Slack"], sourceOfTruth: "Zapier Table", rolesInvolved: ["Sales rep", "Owner", "Customer / client"], requiredDataFields: ["Lead name", "Phone", "Email", "Service interest", "Assigned rep"], exceptionRules: ["Missing required field", "Duplicate record", "No response after SLA"], humanReviewPoint: "Owner review", frequency: "Per event", volume: "High", successMetric: "Every lead receives follow-up within the agreed response window.", manualFallback: "Admin sends a daily lead list and assigns reps manually.", optionalNotes: "" },
  { automationName: "New employee onboarding", clientName: "", industry: "Medical/admin", category: "Employee onboarding", status: "Ready to Review", businessProblem: "After a hire accepts, paperwork, account access, and manager setup tasks are tracked in email and memory.", triggerType: "Employee accepted", sourceChannel: "Email", desiredActions: ["Create or update record", "Send email", "Create task", "Notify internal team"], toolsInUse: ["Zapier", "Gmail", "Google Drive", "HR app", "Slack"], sourceOfTruth: "Zapier Table", rolesInvolved: ["HR", "Owner", "Employee"], requiredDataFields: ["Employee name", "Email", "Role", "Start date", "Manager"], exceptionRules: ["Missing required field", "No response after SLA"], humanReviewPoint: "Admin review", frequency: "Per event", volume: "Low", successMetric: "New hires arrive with fewer missing forms and setup gaps.", manualFallback: "HR sends welcome packet manually and tracks progress in a spreadsheet.", optionalNotes: "" },
];

export function createAutomationId(prefix = "automation") {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function unique(items) {
  return [...new Set((items || []).filter(Boolean))];
}

function asBullets(items) {
  return unique(items).map((item) => `- ${item}`).join("\n");
}

function list(items, fallback = "To be defined.") {
  return unique(items).length ? unique(items).join(", ") : fallback;
}

export function parseTags(value) {
  if (Array.isArray(value)) return value.map(String).map((item) => item.trim()).filter(Boolean);
  return String(value || "").split(",").map((item) => item.trim()).filter(Boolean);
}

export function validateAutomationInput(input) {
  const errors = [];
  if (!input.automationName || !input.automationName.trim()) errors.push("Automation name is required.");
  if (!input.businessProblem || !input.businessProblem.trim()) errors.push("Business problem is required.");
  if (!input.manualFallback || !input.manualFallback.trim()) errors.push("Manual fallback is required.");
  if (!AUTOMATION_CATEGORIES.includes(input.category)) errors.push("Choose a valid automation category.");
  if (!AUTOMATION_TRIGGER_TYPES.includes(input.triggerType)) errors.push("Choose a valid trigger type.");
  if (!AUTOMATION_STATUSES.includes(input.status)) errors.push("Choose a valid automation status.");
  if (!input.desiredActions || input.desiredActions.length === 0) errors.push("Choose at least one desired automated action.");
  return errors;
}

export function scoreComplexity(input) {
  const reasons = [];
  const tools = input.toolsInUse || [];
  let score = 0;
  if (tools.length > 1) { score += tools.length - 1; reasons.push(`+${tools.length - 1} for additional systems after the first`); }
  if ([input.sourceChannel, ...(input.exceptionRules || [])].some((value) => /file|upload|document|photo|proof/i.test(value))) { score += 1; reasons.push("+1 for file uploads or attachments"); }
  if ((input.desiredActions || []).length >= 3) { score += 1; reasons.push("+1 for three or more automated actions"); }
  if ((input.exceptionRules || []).length >= 2) { score += 1; reasons.push("+1 for two or more exception rules"); }
  if (input.humanReviewPoint && input.humanReviewPoint !== "None") { score += 1; reasons.push("+1 for human approval/review"); }
  if (input.triggerType === "Scheduled time" && input.sourceChannel !== "Custom") { score += 1; reasons.push("+1 for scheduled behavior plus downstream event/source checks"); }
  if (tools.some((tool) => ["QuickBooks", "HR app"].includes(tool))) { score += 1; reasons.push("+1 for accounting, payroll, HR, or billing systems"); }
  const label = score <= 2 ? "Low" : score <= 5 ? "Medium" : "High";
  return { score, label, reasons: reasons.length ? reasons : ["No additional complexity rules fired"] };
}

export function scoreImpact(input) {
  const reasons = [];
  let score = 0;
  if (["Billing / collections", "Sales follow-up", "Client onboarding", "Employee onboarding", "Field service"].includes(input.category)) { score += 2; reasons.push("+2 for revenue, onboarding, employee setup, or field closeout impact"); }
  if (["Daily", "Weekly"].includes(input.frequency)) { score += 1; reasons.push("+1 for daily or weekly cadence"); }
  if (input.volume === "High") { score += 1; reasons.push("+1 for high volume"); }
  if ((input.rolesInvolved || []).some((role) => ["Owner", "Admin"].includes(role))) { score += 1; reasons.push("+1 for reducing owner/admin handoffs"); }
  if ((input.desiredActions || []).some((action) => ["Request missing information", "Send reminder", "Draft invoice", "Update status"].includes(action))) { score += 1; reasons.push("+1 for preventing missed follow-up/status/invoice work"); }
  if (/delay|slow|miss|revenue|follow[- ]?up|document|handoff/i.test(input.businessProblem || "")) { score += 1; reasons.push("+1 for problem language indicating delays, missed items, or slow follow-up"); }
  const label = score <= 2 ? "Low" : score <= 4 ? "Medium" : "High";
  return { score, label, reasons: reasons.length ? reasons : ["No additional impact rules fired"] };
}

function recommendToolStack(input, complexity) {
  const selected = input.toolsInUse || [];
  if (selected.length) {
    return `${selected.join(" + ")} — selected tools should be used where they already hold data or team habits. ${input.sourceOfTruth !== "None yet" ? `${input.sourceOfTruth} should act as the visible source of truth.` : "Confirm one visible source of truth before building."}`;
  }
  if (complexity.label === "High" || (input.exceptionRules || []).length >= 3) return "Make + Airtable — recommended for multiple branches, fallback routes, explicit error handling, and review queues.";
  if (["Document collection", "Billing / collections"].includes(input.category) || input.humanReviewPoint !== "None") return "Airtable + Gmail — recommended for record-centric workflows needing forms, filtering, review, and approvals.";
  if (["Field service", "Client onboarding"].includes(input.category)) return "Google Forms + Google Sheets + Google Drive — recommended for low-friction intake, file links, and team-owned tracking.";
  return "Zapier + Zapier Tables — recommended for broad app-to-app handoffs with lighter branching and a simple source of truth.";
}

function humanReview(input) {
  const points = [];
  if (input.humanReviewPoint && input.humanReviewPoint !== "None") points.push(`${input.humanReviewPoint} before downstream actions that affect customers, money, or status.`);
  if ((input.desiredActions || []).some((action) => ["Send email", "Draft invoice"].includes(action))) points.push("Review customer-facing messages or invoice drafts before using full automation.");
  if ((input.exceptionRules || []).some((rule) => /approval|threshold|missing/i.test(rule))) points.push("Review records with missing data, approvals, or threshold exceptions before external communication continues.");
  return points.length ? asBullets(points) : "No formal review point selected. Revisit this before automating customer-facing or money-related steps.";
}

function flowchart(input) {
  return [
    "flowchart TD",
    `    A[${input.triggerType}] --> B{Required fields present?}`,
    "    B -- No --> C[Mark Incomplete Input]",
    "    C --> D[Request missing information / queue reminder]",
    `    B -- Yes --> E[Create or update ${input.sourceOfTruth || "source-of-truth record"}]`,
    "    E --> F{Exception or approval needed?}",
    "    F -- Yes --> G[Human review]",
    "    G --> H{Approved?}",
    "    H -- No --> I[Notify owner and use manual fallback]",
    "    H -- Yes --> J[Run selected actions]",
    "    F -- No --> J",
    "    J --> K[Notify team / update status]",
    "    K --> L[Log result and close]",
  ].join("\n");
}

function buildChecklist(flow, input) {
  const items = [
    "Confirm trigger and source channel",
    "Create or confirm source-of-truth fields",
    ...flow.map((step) => step.replace(/^\d+\.\s*/, "")),
    "Configure exception paths and manual fallback",
    "Test with at least three realistic records",
  ];
  if ((input.exceptionRules || []).length) items.push("Test each selected exception rule");
  return unique(items).map((text) => ({ id: createAutomationId("auto-item"), text, completed: false, notes: "" }));
}

export function checklistToAutomationSection(checklist) {
  return (checklist || []).map((item) => `- [${item.completed ? "x" : " "}] ${item.text}${item.notes ? ` — Note: ${item.notes}` : ""}`).join("\n") || "- [ ] Add implementation checklist items.";
}

export function generateAutomationPlan(input) {
  const errors = validateAutomationInput(input);
  if (errors.length) throw new Error(errors.join(" "));
  const template = AUTOMATION_CATEGORY_TEMPLATES[input.category] || AUTOMATION_CATEGORY_TEMPLATES.Custom;
  const requiredFields = unique([...template.inputs, ...parseTags(input.requiredDataFields)]);
  const dataFields = unique([...template.fields, ...parseTags(input.requiredDataFields).map((field) => field.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/(^_|_$)/g, ""))]);
  const flow = [
    `1. Trigger starts when: ${TRIGGER_TEMPLATES[input.triggerType]}`,
    `2. Capture or find the record from ${input.sourceChannel}.`,
    `3. Confirm required fields: ${requiredFields.join(", ")}.`,
    ...input.desiredActions.map((action, index) => `${index + 4}. ${ACTION_BLOCKS[action] || ACTION_BLOCKS.Custom}`),
    `${input.desiredActions.length + 4}. Update status, timestamp, owner, and next action in ${input.sourceOfTruth}.`,
  ];
  const exceptionLines = unique([...(input.exceptionRules || []).map((rule) => `${rule} -> ${EXCEPTION_BLOCKS[rule] || EXCEPTION_BLOCKS.Custom}`), "System/tool failure -> mark `Manual Fallback Required`, preserve the checklist, and add a retry note."]);
  const complexity = scoreComplexity(input);
  const impact = scoreImpact(input);
  const recommendedStack = recommendToolStack(input, complexity);
  const checklist = buildChecklist(flow, input);
  const sections = {
    "Automation Summary": template.summary,
    "Business Problem Being Solved": input.businessProblem,
    Trigger: TRIGGER_TEMPLATES[input.triggerType],
    "Required Inputs": asBullets(requiredFields),
    "Source of Truth": input.sourceOfTruth === "None yet" ? "None yet. Choose a simple visible tracker before building the first version." : input.sourceOfTruth,
    "Systems Involved": asBullets(input.toolsInUse?.length ? input.toolsInUse : recommendedStack.split(" — ")[0].split(" + ")),
    "Roles Involved": asBullets(input.rolesInvolved || []),
    "Automation Flow": flow.join("\n"),
    "Exception Rules": asBullets(exceptionLines),
    "Human Review Points": humanReview(input),
    "Data Fields Needed": asBullets(dataFields),
    "Recommended Tool Stack": recommendedStack,
    Complexity: `**${complexity.label} (${complexity.score})**\n${asBullets(complexity.reasons)}`,
    Impact: `**${impact.label} (${impact.score})**\n${asBullets(impact.reasons)}`,
    "First Version Scope": "Build the trigger, source-of-truth record, selected action blocks, exception flags, and human review path. Keep destructive actions, final billing, payroll/account changes, and custom edge cases manual until the first version is stable.",
    "Manual Fallback": input.manualFallback,
    "Implementation Checklist": checklistToAutomationSection(checklist),
    "Client-facing Summary": `This automation plan creates a practical first version for ${input.clientName || "the business"}: it starts from ${input.triggerType.toLowerCase()}, keeps ${input.sourceOfTruth.toLowerCase()} visible as the source of truth, and defines review and fallback rules before automating too much.`,
    "Next Best Automation": template.next,
    "Mermaid Flowchart": flowchart(input),
  };
  return { sections, checklist, complexity, impact };
}

export function createAutomationPlan(input) {
  const generated = generateAutomationPlan(input);
  const now = new Date().toISOString();
  return {
    id: createAutomationId(),
    ...input,
    automationName: input.automationName.trim(),
    clientName: (input.clientName || "").trim(),
    requiredDataFields: parseTags(input.requiredDataFields),
    sections: generated.sections,
    checklist: generated.checklist,
    updatedAt: now,
  };
}

export function duplicateAutomationPlan(plan) {
  return { ...structuredClone(plan), id: createAutomationId(), automationName: `${plan.automationName} Copy`, status: "Draft", updatedAt: new Date().toISOString() };
}

export function automationStarterPlans() {
  return AUTOMATION_STARTER_TEMPLATES.map(createAutomationPlan);
}

export function addAutomationChecklistItem(plan, text = "New implementation task", notes = "") {
  const item = { id: createAutomationId("auto-item"), text, completed: false, notes };
  plan.checklist = [...(plan.checklist || []), item];
  plan.sections["Implementation Checklist"] = checklistToAutomationSection(plan.checklist);
  plan.updatedAt = new Date().toISOString();
  return item;
}

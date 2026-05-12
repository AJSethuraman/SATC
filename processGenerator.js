export const STORAGE_KEY = "process-builder-processes-v2";

export const PROCESS_CATEGORIES = [
  "Client/customer onboarding",
  "Customer follow-up",
  "Billing and collections",
  "Monthly admin",
  "Field/service operations",
  "Employee onboarding",
  "Vendor management",
  "Document collection",
  "Sales pipeline",
  "Quality control",
  "Reporting",
  "Finance/bookkeeping",
  "Professional services",
  "Custom process",
];

export const STATUS_OPTIONS = ["Draft", "In Use", "Needs Review", "Deprecated"];

export const SECTION_TITLES = [
  "Process summary",
  "Objective",
  "Trigger event",
  "Frequency",
  "Required inputs",
  "Expected outputs",
  "Tools/systems used",
  "Roles and responsibilities",
  "Step-by-step SOP",
  "Decision points",
  "Handoffs",
  "Quality control checks",
  "Common exceptions",
  "Risks or failure points",
  "Client/customer/vendor communication points",
  "Internal checklist",
  "Automation opportunities",
  "Recommended next improvement",
];

const CATEGORY_TEMPLATES = {
  "Client/customer onboarding": {
    role: "Client-facing owner coordinates setup; operations owner confirms readiness; client provides required information.",
    inputs: ["Signed agreement or approved request", "Primary contact information", "Service scope", "Required setup details"],
    outputs: ["Customer record created", "Welcome or kickoff communication sent", "Initial tasks assigned", "Next milestone confirmed"],
    tools: ["CRM or customer list", "Email", "Shared drive", "Task manager"],
    handoffs: ["Sales or owner hands the new customer to the delivery or operations owner.", "Operations confirms setup is complete before work begins."],
    qc: ["Confirm contact details are accurate.", "Verify agreement, scope, and payment setup are complete.", "Check that the customer received next-step instructions."],
    automation: ["Create a reusable onboarding task template.", "Send automated welcome and reminder emails.", "Route intake form responses into the customer record."],
  },
  "Customer follow-up": {
    role: "Customer owner tracks open items, sends follow-up, and escalates stalled responses.",
    inputs: ["Customer name", "Reason for follow-up", "Last contact date", "Desired next action"],
    outputs: ["Customer response captured", "Next action scheduled", "Status updated"],
    tools: ["CRM or customer tracker", "Email", "Phone", "Calendar"],
    handoffs: ["Front office or sales passes unresolved requests to the responsible service owner."],
    qc: ["Confirm the follow-up message has one clear ask.", "Record the outreach attempt and next reminder date.", "Escalate time-sensitive items to the owner."],
    automation: ["Use reminder sequences for no-response customers.", "Add status-change alerts for overdue follow-up.", "Use message templates by follow-up reason."],
  },
  "Billing and collections": {
    role: "Billing owner verifies balances, sends payment requests, and escalates overdue accounts.",
    inputs: ["Invoice or balance due", "Due date", "Payment link or instructions", "Prior communication history"],
    outputs: ["Payment received or next collection step scheduled", "Account notes updated", "Escalations documented"],
    tools: ["Accounting or invoicing system", "Email", "Payment processor", "Customer record"],
    handoffs: ["Billing hands disputed balances to the owner or account manager.", "Owner approves escalation for long-overdue accounts."],
    qc: ["Confirm the invoice is still unpaid before contacting the customer.", "Check for disputes, credits, or payment arrangements.", "Document each outreach attempt."],
    automation: ["Schedule payment reminders before and after due dates.", "Insert payment links automatically.", "Create escalation alerts for aging balances."],
  },
  "Monthly admin": {
    role: "Operations or admin owner gathers monthly records, completes recurring checks, and reports open issues.",
    inputs: ["Monthly task list", "Open issue log", "Receipts or documents", "Reports or dashboard data"],
    outputs: ["Monthly admin package completed", "Open items assigned", "Summary sent to owner or client"],
    tools: ["Task manager", "Spreadsheet", "Shared drive", "Email"],
    handoffs: ["Admin owner requests missing information from team leads.", "Owner reviews unresolved issues before month close."],
    qc: ["Confirm all recurring tasks are checked off.", "Compare this month to the prior month for unusual gaps.", "Archive final records in the correct location."],
    automation: ["Create recurring monthly tasks.", "Use forms for missing information requests.", "Generate reminders for unresolved items."],
  },
  "Field/service operations": {
    role: "Dispatcher or operations owner schedules work; field team completes the job; office confirms closeout.",
    inputs: ["Work order or job request", "Customer address", "Crew assignment", "Photos or service notes"],
    outputs: ["Completed job record", "Customer update", "Closeout photos or notes", "Billing-ready status"],
    tools: ["Scheduling system", "Mobile checklist", "Photo storage", "Email or SMS"],
    handoffs: ["Office hands the job to the field crew with scope and timing.", "Field crew hands completed notes/photos back to office for closeout."],
    qc: ["Confirm required photos and notes are attached.", "Verify the job matches scope before billing.", "Review exceptions before marking complete."],
    automation: ["Use mobile closeout forms.", "Send automatic arrival/completion notices.", "Trigger billing tasks when closeout is complete."],
  },
  "Employee onboarding": {
    role: "Hiring manager owns readiness; admin owner handles forms, systems, and first-day logistics.",
    inputs: ["Accepted offer", "Employee information", "Required forms", "System access needs"],
    outputs: ["Employee record created", "Accounts and equipment ready", "First-week plan confirmed"],
    tools: ["Payroll system", "HR folder", "Email", "Task manager"],
    handoffs: ["Hiring manager sends role details to admin.", "Admin confirms setup back to the manager before the start date."],
    qc: ["Confirm required forms are complete.", "Verify access and equipment before day one.", "Check that the manager has scheduled orientation."],
    automation: ["Use an onboarding task template by role.", "Automate form requests and reminders.", "Create access request tickets from a form."],
  },
  "Vendor management": {
    role: "Requesting team member provides details; manager approves; admin or finance records the vendor item.",
    inputs: ["Vendor name", "Invoice, quote, or request", "Approval requirements", "Payment terms"],
    outputs: ["Approved vendor action", "Updated vendor record", "Payment or next step scheduled"],
    tools: ["Email", "Accounting system", "Shared drive", "Approval tracker"],
    handoffs: ["Requester sends vendor details to approver.", "Approver sends approved item to admin or finance for processing."],
    qc: ["Confirm approval authority before processing.", "Match vendor documentation to the request.", "Save approval evidence with the record."],
    automation: ["Use approval routing by amount or vendor type.", "Create naming rules for vendor files.", "Send reminders for pending approvals."],
  },
  "Document collection": {
    role: "Process owner requests documents; customer, vendor, or team member provides files; reviewer confirms completeness.",
    inputs: ["Document request list", "Due date", "Submission method", "Reviewer requirements"],
    outputs: ["Complete document package", "Missing items list resolved", "Files saved with standard names"],
    tools: ["Secure portal or upload folder", "Email", "Checklist", "Shared drive"],
    handoffs: ["Requester sends the list to the document provider.", "Reviewer receives completed package and flags missing items."],
    qc: ["Check every required document against the request list.", "Confirm signatures, dates, and file readability.", "Rename and archive files consistently."],
    automation: ["Use upload forms with required fields.", "Send automatic missing-item reminders.", "Create file naming templates."],
  },
  "Sales pipeline": {
    role: "Sales owner qualifies opportunities, manages follow-up, and hands won work to operations.",
    inputs: ["Lead source", "Customer need", "Estimate or proposal details", "Next follow-up date"],
    outputs: ["Qualified opportunity", "Proposal or estimate sent", "Next action logged", "Won/lost status updated"],
    tools: ["CRM", "Email", "Scheduling link", "Proposal or estimating tool"],
    handoffs: ["Marketing or intake hands new leads to sales.", "Sales hands won opportunities to onboarding or operations."],
    qc: ["Confirm fit before spending proposal time.", "Review estimate or proposal for scope and pricing accuracy.", "Make sure every opportunity has a next action."],
    automation: ["Capture website leads into the CRM.", "Create follow-up reminders by pipeline stage.", "Use proposal templates and status alerts."],
  },
  "Quality control": {
    role: "Reviewer checks work against standards before customer delivery or internal closeout.",
    inputs: ["Completed work", "Quality standards", "Customer requirements", "Exception notes"],
    outputs: ["Reviewed work", "Correction list or approval", "Final delivery status"],
    tools: ["QC checklist", "Task manager", "Shared drive", "Reporting dashboard"],
    handoffs: ["Doer submits completed work to reviewer.", "Reviewer returns corrections or approves final delivery."],
    qc: ["Confirm all required evidence is present.", "Check the work against the standard checklist.", "Document corrections and final approval."],
    automation: ["Use required QC fields before closeout.", "Trigger reviewer tasks automatically.", "Report recurring quality misses."],
  },
  Reporting: {
    role: "Reporting owner gathers source data, prepares the report, and sends insights to stakeholders.",
    inputs: ["Source data", "Reporting period", "Report template", "Recipient list"],
    outputs: ["Completed report", "Summary of key changes", "Open questions or follow-up actions"],
    tools: ["Spreadsheet", "Reporting dashboard", "Email", "Shared drive"],
    handoffs: ["Data owners provide source information to reporting owner.", "Reporting owner sends final report to decision-makers."],
    qc: ["Confirm data covers the correct period.", "Compare totals to source systems.", "Review unusual changes before sending."],
    automation: ["Schedule recurring data exports.", "Use dashboard refresh reminders.", "Create report distribution templates."],
  },
  "Finance/bookkeeping": {
    role: "Finance or bookkeeping owner gathers records, reconciles activity, and reports issues.",
    inputs: ["Bank and credit card activity", "Receipts", "Invoices or bills", "Payroll or payment records"],
    outputs: ["Updated financial records", "Reconciled accounts", "Financial summary or open items list"],
    tools: ["Accounting system", "Bank portal", "Receipt capture tool", "Spreadsheet"],
    handoffs: ["Business owner provides missing documents or context.", "Bookkeeper sends completed records or questions for review."],
    qc: ["Reconcile accounts to statements.", "Review uncategorized or unusual transactions.", "Confirm open items are documented."],
    automation: ["Use bank rules carefully and review exceptions.", "Automate receipt reminders.", "Create recurring close checklists."],
  },
  "Professional services": {
    role: "Engagement owner manages scope, delivery steps, client communication, and closeout.",
    inputs: ["Client request or scope", "Required documents", "Timeline", "Responsible team members"],
    outputs: ["Completed deliverable", "Client update", "Archived workpapers or notes", "Next recommendation"],
    tools: ["Project tracker", "Email", "Shared drive", "Template library"],
    handoffs: ["Client-facing owner gathers requirements.", "Delivery owner completes work and hands final output back for client communication."],
    qc: ["Confirm scope and deadline before starting.", "Review deliverable against client expectations.", "Save final files and notes in the standard location."],
    automation: ["Use project templates by service type.", "Automate client reminders for missing items.", "Create review tasks when work changes status."],
  },
  "Custom process": {
    role: "Assign a single accountable process owner and backup owner.",
    inputs: ["Process trigger", "Required information", "Approvals", "Completion criteria"],
    outputs: ["Completed process result", "Updated record", "Communication to the next owner or customer"],
    tools: ["Task manager", "Email", "Shared drive", "Spreadsheet or tracker"],
    handoffs: ["Define who starts the work, who reviews it, and who receives the finished output."],
    qc: ["Confirm required inputs before starting.", "Review completion evidence before closing.", "Document exceptions and follow-up items."],
    automation: ["Turn recurring steps into a task template.", "Use reminders for deadlines.", "Route intake information through a form."],
  },
};

const KEYWORD_RULES = [
  {
    name: "billing",
    pattern: /invoice|payment|overdue|collect|collections|balance|past due|billing/i,
    risks: ["Customer is contacted even though payment has already been received.", "Disputed balances are escalated without enough context."],
    qc: ["Verify current balance and due date before every collection touch.", "Check for credits, disputes, or payment plans."],
    handoffs: ["Billing owner escalates disputed or aged balances to the business owner."],
    automation: ["Automated invoice reminders with payment links.", "Aging report alerts for overdue balances."],
    checklist: ["Confirm invoice or balance is still open", "Send payment reminder with clear next step"],
  },
  {
    name: "sales",
    pattern: /customer|lead|estimate|proposal|quote|prospect|sales/i,
    risks: ["Lead has no next follow-up date and goes cold.", "Estimate or proposal scope is unclear before handoff."],
    qc: ["Confirm every lead has an owner, stage, and next action.", "Review estimates or proposals for scope and price accuracy."],
    handoffs: ["Sales owner hands accepted work to operations with scope, timing, and customer expectations."],
    automation: ["Pipeline reminders by stage.", "Estimate follow-up email templates."],
    checklist: ["Log next follow-up date", "Confirm customer expectations before handoff"],
  },
  {
    name: "field",
    pattern: /field|crew|job|photo|photos|service call|technician|site|dispatch|work order/i,
    risks: ["Field work is marked complete without photos or notes.", "Office does not receive closeout details needed for billing or follow-up."],
    qc: ["Require completion photos and service notes before closeout.", "Verify job scope was completed or exceptions were documented."],
    handoffs: ["Field crew hands closeout notes, photos, and exceptions back to office."],
    automation: ["Mobile job closeout form.", "Automatic billing task after closeout."],
    checklist: ["Attach closeout photos or notes", "Review exceptions before marking job complete"],
  },
  {
    name: "documents",
    pattern: /document|documents|form|forms|signature|signed|missing information|missing item|upload|file/i,
    risks: ["Work starts with incomplete or unreadable documents.", "Missing items are not tracked consistently."],
    qc: ["Check documents against a required-item list.", "Confirm signatures, dates, and file readability."],
    handoffs: ["Requester sends missing-item list to the customer, vendor, or internal owner."],
    automation: ["Document request forms with required fields.", "Automated missing-item reminder sequence."],
    checklist: ["Compare received documents to request list", "Send missing-item request if needed"],
  },
  {
    name: "reporting",
    pattern: /report|spreadsheet|monthly|dashboard|metrics|summary|close/i,
    risks: ["Report is sent with stale or incomplete source data.", "Monthly work is completed without documenting open issues."],
    qc: ["Confirm reporting period and source data before sending.", "Compare current results to the prior period for unusual changes."],
    handoffs: ["Reporting owner sends summary and open issues to the owner or client."],
    automation: ["Recurring monthly task template.", "Scheduled data export or dashboard refresh reminders."],
    checklist: ["Confirm reporting period", "Send summary with open issues"],
  },
  {
    name: "finance",
    pattern: /quickbooks|bank statement|bank|receipt|receipts|payroll|reconcil|bookkeep|credit card/i,
    risks: ["Transactions are categorized without support or owner context.", "Accounts are not reconciled before reports are delivered."],
    qc: ["Reconcile bank and credit card accounts to statements.", "Review uncategorized, unusual, or missing transactions."],
    handoffs: ["Bookkeeping owner sends open questions to the business owner before closeout."],
    automation: ["Receipt capture reminders.", "Recurring reconciliation checklist."],
    checklist: ["Reconcile accounts to statements", "Review uncategorized or unusual activity"],
  },
  {
    name: "approvals",
    pattern: /approval|approve|manager|owner|vendor|bill|purchase/i,
    risks: ["Work or payment proceeds without required approval.", "Approval evidence is separated from the final record."],
    qc: ["Confirm the right approver before processing.", "Save approval evidence with the final record."],
    handoffs: ["Requester hands complete support to approver; approver hands approved item to admin or finance."],
    automation: ["Approval routing by amount, department, or process type.", "Reminder alerts for pending approvals."],
    checklist: ["Confirm required approval is complete", "Save approval evidence"],
  },
];

export const STARTER_TEMPLATES = [
  { name: "New customer onboarding", businessName: "", industry: "Home services", category: "Client/customer onboarding", status: "Draft", rawDescription: "After a customer approves the work, collect contact details, confirm scope, create the customer record, schedule kickoff, send a welcome message, and assign the first internal tasks." },
  { name: "Customer estimate follow-up", businessName: "", industry: "Contractor or service business", category: "Customer follow-up", status: "Draft", rawDescription: "When an estimate is sent, log the follow-up date, call or email the customer after two days, answer questions, update the pipeline, and hand accepted work to scheduling." },
  { name: "Invoice collection follow-up", businessName: "", industry: "Small business", category: "Billing and collections", status: "In Use", rawDescription: "Every week review overdue invoices, confirm payment has not arrived, send a friendly reminder with the payment link, note the account, and escalate older balances to the owner." },
  { name: "Monthly admin close", businessName: "", industry: "Owner-led small business", category: "Monthly admin", status: "Draft", rawDescription: "At month end gather reports, review open tasks, collect missing receipts or documents, update the admin tracker, and send the owner a short summary of open issues." },
  { name: "Employee onboarding", businessName: "", industry: "Small business", category: "Employee onboarding", status: "Draft", rawDescription: "When a candidate accepts, collect employment forms, set up payroll, create system accounts, schedule orientation, prepare equipment, and confirm the manager has a first-week plan." },
  { name: "Vendor bill approval", businessName: "", industry: "Small business", category: "Vendor management", status: "Draft", rawDescription: "When a vendor bill arrives, save the invoice, match it to the purchase request, send it to the department owner for approval, enter it into accounting, schedule payment, and file proof of approval." },
  { name: "Field service job closeout", businessName: "", industry: "Field service", category: "Field/service operations", status: "Draft", rawDescription: "After a crew finishes a job, collect photos and service notes, confirm the job is complete, record any exceptions, notify the customer, and send the job to billing." },
  { name: "Document collection process", businessName: "", industry: "Professional services", category: "Document collection", status: "Draft", rawDescription: "When documents are needed, send the customer a clear request list, collect uploads, review for missing forms or signatures, follow up on missing items, and save final files in the shared folder." },
  { name: "Sales lead follow-up", businessName: "", industry: "Agency or consultant", category: "Sales pipeline", status: "Draft", rawDescription: "When a new lead comes in, qualify the need, schedule a call, send a proposal if there is a fit, follow up until a decision, and update the CRM stage." },
  { name: "Customer complaint resolution", businessName: "", industry: "Service business", category: "Quality control", status: "Draft", rawDescription: "When a customer complaint is received, acknowledge it, capture details, assign an owner, investigate what happened, offer a resolution, and review how to prevent the issue again." },
  { name: "Monthly bookkeeping close", businessName: "", industry: "Accounting or bookkeeping", category: "Finance/bookkeeping", status: "In Use", rawDescription: "Each month import bank and credit card transactions, categorize uncoded activity, request receipts, reconcile accounts, review payroll and loan balances, then send financial statements with a short summary." },
  { name: "New tax client onboarding", businessName: "", industry: "Tax or accounting", category: "Professional services", status: "Draft", rawDescription: "After a tax client accepts the engagement, send the agreement, collect organizer details, create the portal, request prior returns and current year documents, assign the preparer, and confirm the expected filing timeline." },
];

export function createId(prefix = "process") {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function validateProcessInput(input) {
  const errors = [];
  if (!input.name || !input.name.trim()) errors.push("Process name is required.");
  if (!PROCESS_CATEGORIES.includes(input.category)) errors.push("Choose a valid process category.");
  if (!STATUS_OPTIONS.includes(input.status)) errors.push("Choose a valid status.");
  return errors;
}

function unique(items) {
  return [...new Set(items.filter(Boolean))];
}

function asBullets(items) {
  return unique(items).map((item) => `- ${item}`).join("\n");
}

function sentenceCase(text) {
  const trimmed = text.trim();
  return trimmed ? trimmed.charAt(0).toUpperCase() + trimmed.slice(1) : trimmed;
}

export function splitIntoSteps(description) {
  const normalized = (description || "")
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
  const text = (description || "").toLowerCase();
  if (/daily|each day|every day/.test(text)) return "Daily or each business day.";
  if (/weekly|each week|every week/.test(text)) return "Weekly.";
  if (/monthly|each month|month-end|month end|month end/.test(text)) return "Monthly.";
  if (/quarterly|each quarter/.test(text)) return "Quarterly.";
  if (/annually|yearly|each year|tax season/.test(text)) return "Annually or seasonally.";
  if (/when|after|once|as soon as/.test(text)) return "Event-driven when the trigger occurs.";
  return "To be confirmed; edit this cadence for the business.";
}

function detectTrigger(description, category) {
  const sentences = (description || "").split(/[.!?\n]/).map((s) => s.trim()).filter(Boolean);
  const triggerSentence = sentences.find((sentence) => /when|after|once|every|each|at month end/i.test(sentence));
  if (triggerSentence) return `${sentenceCase(triggerSentence)}.`;

  const fallback = {
    "Client/customer onboarding": "A customer approves work, signs an agreement, or is ready to start.",
    "Customer follow-up": "A customer needs a response, reminder, or next step.",
    "Billing and collections": "An invoice is due, overdue, disputed, or ready for payment follow-up.",
    "Monthly admin": "The monthly admin cycle begins or month-end arrives.",
    "Field/service operations": "A job, service call, or work order is ready to schedule or close out.",
    "Employee onboarding": "A candidate accepts an offer or a start date is confirmed.",
    "Vendor management": "A vendor request, bill, quote, or approval need is received.",
    "Document collection": "Required information or documents are needed to continue work.",
    "Sales pipeline": "A lead, estimate request, or proposal opportunity is created.",
    "Quality control": "Work is complete enough for review or a quality issue is reported.",
    Reporting: "A reporting period closes or stakeholders request an update.",
    "Finance/bookkeeping": "A financial period, transaction batch, or reconciliation task is ready.",
    "Professional services": "A client request or engagement milestone is ready for action.",
    "Custom process": "The defined process trigger occurs.",
  };
  return fallback[category] || fallback["Custom process"];
}

function detectTools(description, defaults) {
  const knownTools = ["email", "spreadsheet", "excel", "quickbooks", "xero", "portal", "crm", "calendar", "slack", "teams", "payroll", "bank", "task manager", "drive", "phone", "sms", "invoice", "dashboard"];
  const text = (description || "").toLowerCase();
  const matches = knownTools.filter((tool) => text.includes(tool)).map(sentenceCase);
  return unique([...matches, ...defaults]);
}

function matchedRules(description) {
  return KEYWORD_RULES.filter((rule) => rule.pattern.test(description || ""));
}

export function buildChecklistItems(steps, rules) {
  const fromSteps = steps.map((step) => step.replace(/^\d+\.\s*/, ""));
  const fromRules = rules.flatMap((rule) => rule.checklist);
  return unique([...fromSteps, ...fromRules]).map((text) => ({ id: createId("item"), text, completed: false, notes: "" }));
}

export function checklistToSection(checklist) {
  if (!checklist || !checklist.length) return "- [ ] Add checklist items.";
  return checklist.map((item) => `- [${item.completed ? "x" : " "}] ${item.text}${item.notes ? ` — Note: ${item.notes}` : ""}`).join("\n");
}

export function generateProcessDocument(input) {
  const errors = validateProcessInput(input);
  if (errors.length) {
    throw new Error(errors.join(" "));
  }

  const template = CATEGORY_TEMPLATES[input.category];
  const rules = matchedRules(input.rawDescription);
  const steps = splitIntoSteps(input.rawDescription);
  const industryPhrase = input.industry ? ` for a ${input.industry} business` : "";
  const businessPhrase = input.businessName ? ` at ${input.businessName}` : "";
  const checklist = buildChecklistItems(steps, rules);

  const sections = {
    "Process summary": `${input.name}${businessPhrase}${industryPhrase}. This is a rule-based first draft for a recurring ${input.category.toLowerCase()} process. Review and edit every section before using it with a client or team.`,
    "Objective": `Create a clear, repeatable process for ${input.name} that makes ownership, handoffs, quality checks, and next actions easy to follow.`,
    "Trigger event": detectTrigger(input.rawDescription, input.category),
    "Frequency": detectFrequency(input.rawDescription),
    "Required inputs": asBullets(template.inputs),
    "Expected outputs": asBullets(template.outputs),
    "Tools/systems used": asBullets(detectTools(input.rawDescription, template.tools)),
    "Roles and responsibilities": template.role,
    "Step-by-step SOP": steps.join("\n"),
    "Decision points": asBullets([
      "Is all required information available before work begins?",
      "Does the item follow the standard path, or does it require manager/owner review?",
      "Is customer, vendor, or internal approval required before completion?",
      "Should an exception be documented and escalated?",
    ]),
    Handoffs: asBullets([...template.handoffs, ...rules.flatMap((rule) => rule.handoffs)]),
    "Quality control checks": asBullets([...template.qc, ...rules.flatMap((rule) => rule.qc)]),
    "Common exceptions": asBullets([
      "Missing, incomplete, or unclear information.",
      "Responsible owner is unavailable or unclear.",
      "Deadline is accelerated, missed, or dependent on another party.",
      "Customer, vendor, or internal stakeholder requests a non-standard path.",
    ]),
    "Risks or failure points": asBullets([
      "Work starts before the right inputs are available.",
      "Status is not updated, causing missed follow-up or duplicate work.",
      "Handoff expectations are unclear between roles.",
      "Quality review is skipped when the team is busy.",
      ...rules.flatMap((rule) => rule.risks),
    ]),
    "Client/customer/vendor communication points": asBullets([
      "Confirm receipt of the request or trigger.",
      "Send a clear list of missing items, decisions, or approvals needed.",
      "Provide status updates when the process moves to the next stage.",
      "Confirm completion, outcome, and any next expected action.",
    ]),
    "Internal checklist": checklistToSection(checklist),
    "Automation opportunities": asBullets([...template.automation, ...rules.flatMap((rule) => rule.automation)]),
    "Recommended next improvement": "Turn this process into a reusable task template, assign owners for each handoff, and review the process after the next two real uses.",
  };

  return { sections, checklist };
}

export function createProcess(input) {
  const generated = generateProcessDocument(input);
  const now = new Date().toISOString();
  return {
    id: createId(),
    name: input.name.trim(),
    businessName: (input.businessName || "").trim(),
    industry: (input.industry || "").trim(),
    category: input.category,
    status: input.status,
    rawDescription: (input.rawDescription || "").trim(),
    sections: generated.sections,
    checklist: generated.checklist,
    updatedAt: now,
  };
}

export function duplicateProcess(process) {
  return {
    ...structuredClone(process),
    id: createId(),
    name: `${process.name} Copy`,
    status: "Draft",
    updatedAt: new Date().toISOString(),
  };
}

export function starterProcesses() {
  return STARTER_TEMPLATES.map(createProcess);
}

export function addChecklistItem(process, text = "New checklist item", notes = "") {
  const item = { id: createId("item"), text, completed: false, notes };
  process.checklist = [...(process.checklist || []), item];
  process.sections["Internal checklist"] = checklistToSection(process.checklist);
  process.updatedAt = new Date().toISOString();
  return item;
}

export function updateChecklistItem(process, itemId, updates) {
  process.checklist = (process.checklist || []).map((item) => (item.id === itemId ? { ...item, ...updates } : item));
  process.sections["Internal checklist"] = checklistToSection(process.checklist);
  process.updatedAt = new Date().toISOString();
  return process.checklist.find((item) => item.id === itemId) || null;
}

export function deleteChecklistItem(process, itemId) {
  process.checklist = (process.checklist || []).filter((item) => item.id !== itemId);
  process.sections["Internal checklist"] = checklistToSection(process.checklist);
  process.updatedAt = new Date().toISOString();
  return process.checklist;
}

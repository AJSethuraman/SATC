import {
  PROCESS_CATEGORIES,
  SECTION_TITLES,
  STARTER_TEMPLATES,
  STATUS_OPTIONS,
  checklistToSection,
  createId,
  createProcess,
  duplicateProcess,
  generateProcessDocument,
  starterProcesses,
  validateProcessInput,
} from "./processGenerator.js";
import { checklistToMarkdown, parseBackup, processToMarkdown, processesToBackup } from "./markdownExport.js";
import { loadSavedProcesses, saveProcesses } from "./processStorage.js";
import {
  AUTOMATION_ACTIONS,
  AUTOMATION_CATEGORIES,
  AUTOMATION_EXCEPTION_RULES,
  AUTOMATION_FREQUENCIES,
  AUTOMATION_INDUSTRIES,
  AUTOMATION_REVIEW_POINTS,
  AUTOMATION_ROLES,
  AUTOMATION_SECTION_TITLES,
  AUTOMATION_SOURCES_OF_TRUTH,
  AUTOMATION_SOURCE_CHANNELS,
  AUTOMATION_STARTER_TEMPLATES,
  AUTOMATION_STATUSES,
  AUTOMATION_TOOLS,
  AUTOMATION_TRIGGER_TYPES,
  AUTOMATION_VOLUMES,
  addAutomationChecklistItem,
  automationStarterPlans,
  checklistToAutomationSection,
  createAutomationId,
  createAutomationPlan,
  duplicateAutomationPlan,
  generateAutomationPlan,
  parseTags,
  validateAutomationInput,
} from "./automationGenerator.js";
import { automationChecklistToMarkdown, automationPlanToMarkdown, automationPlansToBackup, parseAutomationBackup } from "./automationExport.js";
import { loadSavedAutomationPlans, saveAutomationPlans } from "./automationStorage.js";

const state = {
  processes: [],
  activeId: null,
  automationPlans: [],
  activeAutomationId: null,
  mode: "process",
};

const elements = {
  processForm: document.querySelector("#processForm"),
  processName: document.querySelector("#processName"),
  businessName: document.querySelector("#businessName"),
  industry: document.querySelector("#industry"),
  category: document.querySelector("#processCategory"),
  status: document.querySelector("#statusTag"),
  rawDescription: document.querySelector("#rawDescription"),
  sectionsContainer: document.querySelector("#sectionsContainer"),
  sectionTemplate: document.querySelector("#sectionTemplate"),
  checklistTemplate: document.querySelector("#checklistItemTemplate"),
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
  copyMarkdownBtn: document.querySelector("#copyMarkdownBtn"),
  copyChecklistBtn: document.querySelector("#copyChecklistBtn"),
  exportBackupBtn: document.querySelector("#exportBackupBtn"),
  importBackupInput: document.querySelector("#importBackupInput"),
  addChecklistItemBtn: document.querySelector("#addChecklistItemBtn"),
  readinessList: document.querySelector("#readinessList"),
  errorBanner: document.querySelector("#errorBanner"),
  starterSelect: document.querySelector("#starterSelect"),
  processMode: document.querySelector("#processMode"),
  automationMode: document.querySelector("#automationMode"),
  processModeBtn: document.querySelector("#processModeBtn"),
  automationModeBtn: document.querySelector("#automationModeBtn"),
  automationForm: document.querySelector("#automationForm"),
  automationName: document.querySelector("#automationName"),
  automationClientName: document.querySelector("#automationClientName"),
  automationIndustry: document.querySelector("#automationIndustry"),
  automationCategory: document.querySelector("#automationCategory"),
  automationStatus: document.querySelector("#automationStatus"),
  automationTriggerType: document.querySelector("#automationTriggerType"),
  automationSourceChannel: document.querySelector("#automationSourceChannel"),
  automationSourceOfTruth: document.querySelector("#automationSourceOfTruth"),
  automationHumanReviewPoint: document.querySelector("#automationHumanReviewPoint"),
  automationFrequency: document.querySelector("#automationFrequency"),
  automationVolume: document.querySelector("#automationVolume"),
  automationSuccessMetric: document.querySelector("#automationSuccessMetric"),
  automationBusinessProblem: document.querySelector("#automationBusinessProblem"),
  automationDesiredActions: document.querySelector("#automationDesiredActions"),
  automationToolsInUse: document.querySelector("#automationToolsInUse"),
  automationRolesInvolved: document.querySelector("#automationRolesInvolved"),
  automationExceptionRules: document.querySelector("#automationExceptionRules"),
  automationRequiredDataFields: document.querySelector("#automationRequiredDataFields"),
  automationManualFallback: document.querySelector("#automationManualFallback"),
  automationOptionalNotes: document.querySelector("#automationOptionalNotes"),
  automationStarterSelect: document.querySelector("#automationStarterSelect"),
  automationList: document.querySelector("#automationList"),
  automationCount: document.querySelector("#automationCount"),
  automationSearchInput: document.querySelector("#automationSearchInput"),
  activeAutomationTitle: document.querySelector("#activeAutomationTitle"),
  activeAutomationMeta: document.querySelector("#activeAutomationMeta"),
  automationSaveState: document.querySelector("#automationSaveState"),
  automationSectionsContainer: document.querySelector("#automationSectionsContainer"),
  saveAutomationBtn: document.querySelector("#saveAutomationBtn"),
  duplicateAutomationBtn: document.querySelector("#duplicateAutomationBtn"),
  deleteAutomationBtn: document.querySelector("#deleteAutomationBtn"),
  addAutomationChecklistItemBtn: document.querySelector("#addAutomationChecklistItemBtn"),
  exportAutomationMarkdownBtn: document.querySelector("#exportAutomationMarkdownBtn"),
  copyAutomationMarkdownBtn: document.querySelector("#copyAutomationMarkdownBtn"),
  exportAutomationChecklistBtn: document.querySelector("#exportAutomationChecklistBtn"),
  copyAutomationChecklistBtn: document.querySelector("#copyAutomationChecklistBtn"),
  exportAutomationBackupBtn: document.querySelector("#exportAutomationBackupBtn"),
  importAutomationBackupInput: document.querySelector("#importAutomationBackupInput"),
};

function showMessage(message, type = "error") {
  elements.errorBanner.textContent = message;
  elements.errorBanner.className = `message ${type}`;
  elements.errorBanner.hidden = false;
}

function clearMessage() {
  elements.errorBanner.hidden = true;
  elements.errorBanner.textContent = "";
}

function populateSelect(select, options) {
  select.replaceChildren();
  options.forEach((option) => {
    const optionElement = document.createElement("option");
    optionElement.value = option;
    optionElement.textContent = option;
    select.append(optionElement);
  });
}

function populateStarterSelect() {
  elements.starterSelect.replaceChildren();
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "Start blank or load a starter...";
  elements.starterSelect.append(blank);
  STARTER_TEMPLATES.forEach((template, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = template.name;
    elements.starterSelect.append(option);
  });
}

function loadProcesses() {
  try {
    return loadSavedProcesses(localStorage);
  } catch {
    showMessage("Failed local storage load. Starter templates were loaded instead, but saved browser data may be unavailable.");
    return starterProcesses();
  }
}

function persistProcesses() {
  try {
    saveProcesses(state.processes, localStorage);
    elements.saveState.textContent = `Saved locally at ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    return true;
  } catch {
    showMessage("Failed local storage save. Export a JSON backup before closing this browser tab.");
    return false;
  }
}

function getActiveProcess() {
  return state.processes.find((process) => process.id === state.activeId) || null;
}

function collectFormValues() {
  return {
    name: elements.processName.value.trim(),
    businessName: elements.businessName.value.trim(),
    industry: elements.industry.value.trim(),
    category: elements.category.value,
    status: elements.status.value,
    rawDescription: elements.rawDescription.value.trim(),
  };
}

function validateForm() {
  const errors = validateProcessInput(collectFormValues());
  if (errors.length) {
    showMessage(errors.join(" "));
    return false;
  }
  clearMessage();
  return true;
}

function syncChecklistSection(process) {
  process.sections["Internal checklist"] = checklistToSection(process.checklist);
}

function touch(process) {
  process.updatedAt = new Date().toISOString();
}

function renderList() {
  const query = elements.searchInput.value.toLowerCase();
  const filtered = state.processes.filter((process) => [process.name, process.businessName, process.industry, process.category, process.status].join(" ").toLowerCase().includes(query));

  elements.processCount.textContent = `${state.processes.length} saved`;
  elements.processList.replaceChildren();

  filtered.forEach((process) => {
    const item = document.createElement("article");
    item.className = `process-item${process.id === state.activeId ? " active" : ""}`;

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "process-open";

    const name = document.createElement("strong");
    name.textContent = process.name;
    const meta = document.createElement("span");
    meta.textContent = `${process.category} • ${process.status}`;
    const updated = document.createElement("small");
    updated.textContent = `Updated ${new Date(process.updatedAt).toLocaleString()}`;
    openButton.append(name, meta, updated);
    openButton.addEventListener("click", () => selectProcess(process.id));

    const statusSelect = document.createElement("select");
    statusSelect.className = "status-mini";
    statusSelect.setAttribute("aria-label", `Change status for ${process.name}`);
    STATUS_OPTIONS.forEach((status) => {
      const option = document.createElement("option");
      option.value = status;
      option.textContent = status;
      option.selected = status === process.status;
      statusSelect.append(option);
    });
    statusSelect.addEventListener("change", (event) => {
      process.status = event.target.value;
      touch(process);
      persistProcesses();
      renderList();
      renderEditor();
    });

    item.append(openButton, statusSelect);
    elements.processList.append(item);
  });
}

function renderChecklistItem(process, item) {
  const fragment = elements.checklistTemplate.content.cloneNode(true);
  const card = fragment.querySelector(".checklist-item");
  const checkbox = fragment.querySelector(".checklist-complete");
  const text = fragment.querySelector(".checklist-text");
  const notes = fragment.querySelector(".checklist-notes");
  const deleteBtn = fragment.querySelector(".delete-checklist-item");

  checkbox.checked = item.completed;
  text.value = item.text;
  notes.value = item.notes || "";

  const saveChecklistChange = () => {
    item.completed = checkbox.checked;
    item.text = text.value;
    item.notes = notes.value;
    syncChecklistSection(process);
    touch(process);
    persistProcesses();
    renderList();
    renderReadiness(process);
  };

  checkbox.addEventListener("change", saveChecklistChange);
  text.addEventListener("input", saveChecklistChange);
  notes.addEventListener("input", saveChecklistChange);
  deleteBtn.addEventListener("click", () => {
    process.checklist = process.checklist.filter((candidate) => candidate.id !== item.id);
    syncChecklistSection(process);
    touch(process);
    persistProcesses();
    renderEditor();
    renderList();
  });

  return card;
}

function renderInternalChecklist(process) {
  const wrapper = document.createElement("article");
  wrapper.className = "section-card checklist-card";
  const heading = document.createElement("div");
  heading.className = "section-heading";
  const title = document.createElement("h3");
  title.textContent = "Internal checklist";
  const help = document.createElement("p");
  help.textContent = "Edit checklist items, completion status, and notes. Export can include this section separately.";
  heading.append(title, help);
  const list = document.createElement("div");
  list.className = "checklist-list";
  process.checklist.forEach((item) => list.append(renderChecklistItem(process, item)));
  wrapper.append(heading, list);
  return wrapper;
}

function renderReadiness(process) {
  elements.readinessList.replaceChildren();
  const checks = process
    ? [
        { label: "Roles are assigned", ready: Boolean(process.sections["Roles and responsibilities"]?.trim()) },
        { label: "Handoffs are clear", ready: Boolean(process.sections.Handoffs?.trim()) },
        { label: "QC checks are present", ready: Boolean(process.sections["Quality control checks"]?.trim()) },
        { label: "Risks/failure points are reviewed", ready: Boolean(process.sections["Risks or failure points"]?.trim()) },
        { label: "Checklist items are usable", ready: Array.isArray(process.checklist) && process.checklist.some((item) => item.text.trim()) },
        { label: "Automation opportunities are reviewed", ready: Boolean(process.sections["Automation opportunities"]?.trim()) },
      ]
    : [
        { label: "Generate or open a process before export review", ready: false },
      ];

  checks.forEach((check) => {
    const item = document.createElement("li");
    item.className = check.ready ? "ready" : "needs-review";
    const marker = document.createElement("span");
    marker.setAttribute("aria-hidden", "true");
    marker.textContent = check.ready ? "✓" : "•";
    const text = document.createElement("span");
    text.textContent = check.label;
    item.append(marker, text);
    elements.readinessList.append(item);
  });
}

function renderEditor() {
  const process = getActiveProcess();
  elements.sectionsContainer.replaceChildren();

  if (!process) {
    elements.activeProcessTitle.textContent = "New process";
    elements.activeProcessMeta.textContent = "Enter rough notes and generate a process document.";
    renderReadiness(null);
    return;
  }

  elements.processName.value = process.name;
  elements.businessName.value = process.businessName || "";
  elements.industry.value = process.industry || "";
  elements.category.value = process.category;
  elements.status.value = process.status;
  elements.rawDescription.value = process.rawDescription || "";
  elements.activeProcessTitle.textContent = process.name;
  elements.activeProcessMeta.textContent = `${process.category} • ${process.status} • Updated ${new Date(process.updatedAt).toLocaleString()}`;
  renderReadiness(process);

  SECTION_TITLES.forEach((title) => {
    if (title === "Internal checklist") {
      elements.sectionsContainer.append(renderInternalChecklist(process));
      return;
    }

    const fragment = elements.sectionTemplate.content.cloneNode(true);
    const label = fragment.querySelector(".section-title");
    const textarea = fragment.querySelector(".section-textarea");
    label.textContent = title;
    textarea.value = process.sections[title] || "";
    textarea.addEventListener("input", () => {
      process.sections[title] = textarea.value;
      touch(process);
      persistProcesses();
      renderList();
    });
    elements.sectionsContainer.append(fragment);
  });
}

function selectProcess(id) {
  state.activeId = id;
  clearMessage();
  renderList();
  renderEditor();
}

function saveActiveFromForm({ rebuildSections = false } = {}) {
  if (!validateForm()) return;

  const values = collectFormValues();
  let process = getActiveProcess();

  if (!process) {
    process = createProcess(values);
    state.processes.unshift(process);
    state.activeId = process.id;
  } else {
    process.name = values.name;
    process.businessName = values.businessName;
    process.industry = values.industry;
    process.category = values.category;
    process.status = values.status;
    process.rawDescription = values.rawDescription;
    if (rebuildSections) {
      const generated = generateProcessDocument(values);
      process.sections = generated.sections;
      process.checklist = generated.checklist;
    }
    syncChecklistSection(process);
    touch(process);
  }

  persistProcesses();
  renderList();
  renderEditor();
}

function resetForNewProcess() {
  state.activeId = null;
  elements.processForm.reset();
  elements.category.value = PROCESS_CATEGORIES[0];
  elements.status.value = STATUS_OPTIONS[0];
  elements.sectionsContainer.replaceChildren();
  elements.activeProcessTitle.textContent = "New process";
  elements.activeProcessMeta.textContent = "Enter rough notes and generate a process document.";
  clearMessage();
  renderList();
}

function loadStarter(index) {
  const template = STARTER_TEMPLATES[index];
  if (!template) return;
  state.activeId = null;
  elements.processName.value = template.name;
  elements.businessName.value = template.businessName;
  elements.industry.value = template.industry;
  elements.category.value = template.category;
  elements.status.value = template.status;
  elements.rawDescription.value = template.rawDescription;
  elements.activeProcessTitle.textContent = `${template.name} starter`;
  elements.activeProcessMeta.textContent = "Review the starter details, then generate a process document.";
  elements.sectionsContainer.replaceChildren();
  renderReadiness(null);
}

function duplicateActiveProcess() {
  const process = getActiveProcess();
  if (!process) return;
  const copy = duplicateProcess(process);
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

function addChecklistItemToActiveProcess() {
  const process = getActiveProcess();
  if (!process) {
    showMessage("Generate or open a process before adding checklist items.");
    return;
  }
  process.checklist.push({ id: createId("item"), text: "New checklist item", completed: false, notes: "" });
  syncChecklistSection(process);
  touch(process);
  persistProcesses();
  renderEditor();
}

function downloadText(filename, text, type = "text/markdown;charset=utf-8") {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function slugify(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "process";
}

function exportActive(checklistOnly = false) {
  const process = getActiveProcess();
  if (!process) return;
  const filename = checklistOnly ? `${slugify(process.name)}-checklist.md` : `${slugify(process.name)}-process.md`;
  downloadText(filename, checklistOnly ? checklistToMarkdown(process) : processToMarkdown(process));
}

async function copyActive(checklistOnly = false) {
  const process = getActiveProcess();
  if (!process) return;
  const text = checklistOnly ? checklistToMarkdown(process) : processToMarkdown(process);
  try {
    await navigator.clipboard.writeText(text);
    showMessage(checklistOnly ? "Checklist Markdown copied to clipboard." : "Full process Markdown copied to clipboard.", "success");
  } catch {
    showMessage("Clipboard copy failed in this browser. Use the Markdown export instead.");
  }
}

function exportBackup() {
  downloadText(`process-builder-backup-${new Date().toISOString().slice(0, 10)}.json`, processesToBackup(state.processes), "application/json;charset=utf-8");
}

function importBackup(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      const imported = parseBackup(String(reader.result || ""));
      state.processes = imported;
      state.activeId = state.processes[0]?.id || null;
      persistProcesses();
      renderList();
      renderEditor();
      showMessage("JSON backup imported successfully.", "success");
    } catch (error) {
      showMessage(error.message || "Invalid imported JSON backup.");
    } finally {
      elements.importBackupInput.value = "";
    }
  });
  reader.addEventListener("error", () => showMessage("Invalid imported JSON backup. The file could not be read."));
  reader.readAsText(file);
}

function populateAutomationStarterSelect() {
  elements.automationStarterSelect.replaceChildren();
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "Start blank or load an automation starter...";
  elements.automationStarterSelect.append(blank);
  AUTOMATION_STARTER_TEMPLATES.forEach((template, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = template.automationName;
    elements.automationStarterSelect.append(option);
  });
}

function getSelected(select) {
  return [...select.selectedOptions].map((option) => option.value);
}

function setSelected(select, values = []) {
  [...select.options].forEach((option) => {
    option.selected = values.includes(option.value);
  });
}

function loadAutomationPlans() {
  try {
    return loadSavedAutomationPlans(localStorage);
  } catch {
    showMessage("Failed local storage load for automation plans. Starter automations were loaded instead.");
    return automationStarterPlans();
  }
}

function persistAutomationPlans() {
  try {
    saveAutomationPlans(state.automationPlans, localStorage);
    elements.automationSaveState.textContent = `Saved locally at ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    return true;
  } catch {
    showMessage("Failed local storage save for automation plans. Export a JSON backup before closing this browser tab.");
    return false;
  }
}

function getActiveAutomationPlan() {
  return state.automationPlans.find((plan) => plan.id === state.activeAutomationId) || null;
}

function collectAutomationValues() {
  return {
    automationName: elements.automationName.value.trim(),
    clientName: elements.automationClientName.value.trim(),
    industry: elements.automationIndustry.value,
    category: elements.automationCategory.value,
    status: elements.automationStatus.value,
    businessProblem: elements.automationBusinessProblem.value.trim(),
    triggerType: elements.automationTriggerType.value,
    sourceChannel: elements.automationSourceChannel.value,
    desiredActions: getSelected(elements.automationDesiredActions),
    toolsInUse: getSelected(elements.automationToolsInUse),
    sourceOfTruth: elements.automationSourceOfTruth.value,
    rolesInvolved: getSelected(elements.automationRolesInvolved),
    requiredDataFields: parseTags(elements.automationRequiredDataFields.value),
    exceptionRules: getSelected(elements.automationExceptionRules),
    humanReviewPoint: elements.automationHumanReviewPoint.value,
    frequency: elements.automationFrequency.value,
    volume: elements.automationVolume.value,
    successMetric: elements.automationSuccessMetric.value.trim(),
    manualFallback: elements.automationManualFallback.value.trim(),
    optionalNotes: elements.automationOptionalNotes.value.trim(),
  };
}

function validateAutomationForm() {
  const errors = validateAutomationInput(collectAutomationValues());
  if (errors.length) {
    showMessage(errors.join(" "));
    return false;
  }
  clearMessage();
  return true;
}

function renderAutomationList() {
  const query = elements.automationSearchInput.value.toLowerCase();
  const filtered = state.automationPlans.filter((plan) => [plan.automationName, plan.clientName, plan.industry, plan.category, plan.status].join(" ").toLowerCase().includes(query));
  elements.automationCount.textContent = `${state.automationPlans.length} saved`;
  elements.automationList.replaceChildren();
  filtered.forEach((plan) => {
    const item = document.createElement("article");
    item.className = `process-item${plan.id === state.activeAutomationId ? " active" : ""}`;
    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "process-open";
    const name = document.createElement("strong");
    name.textContent = plan.automationName;
    const meta = document.createElement("span");
    meta.textContent = `${plan.category} • ${plan.status}`;
    const updated = document.createElement("small");
    updated.textContent = `Updated ${new Date(plan.updatedAt).toLocaleString()}`;
    openButton.append(name, meta, updated);
    openButton.addEventListener("click", () => selectAutomationPlan(plan.id));
    const statusSelect = document.createElement("select");
    statusSelect.className = "status-mini";
    statusSelect.setAttribute("aria-label", `Change status for ${plan.automationName}`);
    AUTOMATION_STATUSES.forEach((status) => {
      const option = document.createElement("option");
      option.value = status;
      option.textContent = status;
      option.selected = status === plan.status;
      statusSelect.append(option);
    });
    statusSelect.addEventListener("change", (event) => {
      plan.status = event.target.value;
      plan.updatedAt = new Date().toISOString();
      persistAutomationPlans();
      renderAutomationList();
      renderAutomationEditor();
    });
    item.append(openButton, statusSelect);
    elements.automationList.append(item);
  });
}

function syncAutomationChecklistSection(plan) {
  plan.sections["Implementation Checklist"] = checklistToAutomationSection(plan.checklist);
}

function renderAutomationChecklistItem(plan, item) {
  const fragment = elements.checklistTemplate.content.cloneNode(true);
  const card = fragment.querySelector(".checklist-item");
  const checkbox = fragment.querySelector(".checklist-complete");
  const text = fragment.querySelector(".checklist-text");
  const notes = fragment.querySelector(".checklist-notes");
  const deleteBtn = fragment.querySelector(".delete-checklist-item");
  checkbox.checked = item.completed;
  text.value = item.text;
  notes.value = item.notes || "";
  const saveChange = () => {
    item.completed = checkbox.checked;
    item.text = text.value;
    item.notes = notes.value;
    syncAutomationChecklistSection(plan);
    plan.updatedAt = new Date().toISOString();
    persistAutomationPlans();
    renderAutomationList();
  };
  checkbox.addEventListener("change", saveChange);
  text.addEventListener("input", saveChange);
  notes.addEventListener("input", saveChange);
  deleteBtn.addEventListener("click", () => {
    plan.checklist = plan.checklist.filter((candidate) => candidate.id !== item.id);
    syncAutomationChecklistSection(plan);
    plan.updatedAt = new Date().toISOString();
    persistAutomationPlans();
    renderAutomationEditor();
    renderAutomationList();
  });
  return card;
}

function renderAutomationChecklist(plan) {
  const wrapper = document.createElement("article");
  wrapper.className = "section-card checklist-card";
  const heading = document.createElement("div");
  heading.className = "section-heading";
  const title = document.createElement("h3");
  title.textContent = "Implementation Checklist";
  const help = document.createElement("p");
  help.textContent = "Edit implementation tasks, completion status, and notes.";
  heading.append(title, help);
  const list = document.createElement("div");
  list.className = "checklist-list";
  plan.checklist.forEach((item) => list.append(renderAutomationChecklistItem(plan, item)));
  wrapper.append(heading, list);
  return wrapper;
}

function renderAutomationEditor() {
  const plan = getActiveAutomationPlan();
  elements.automationSectionsContainer.replaceChildren();
  if (!plan) {
    elements.activeAutomationTitle.textContent = "New automation plan";
    elements.activeAutomationMeta.textContent = "Answer the guided questions and generate an automation blueprint.";
    return;
  }
  elements.automationName.value = plan.automationName;
  elements.automationClientName.value = plan.clientName || "";
  elements.automationIndustry.value = plan.industry || AUTOMATION_INDUSTRIES[0];
  elements.automationCategory.value = plan.category;
  elements.automationStatus.value = plan.status;
  elements.automationBusinessProblem.value = plan.businessProblem || "";
  elements.automationTriggerType.value = plan.triggerType;
  elements.automationSourceChannel.value = plan.sourceChannel;
  elements.automationSourceOfTruth.value = plan.sourceOfTruth;
  elements.automationHumanReviewPoint.value = plan.humanReviewPoint;
  elements.automationFrequency.value = plan.frequency;
  elements.automationVolume.value = plan.volume;
  elements.automationSuccessMetric.value = plan.successMetric || "";
  elements.automationManualFallback.value = plan.manualFallback || "";
  elements.automationOptionalNotes.value = plan.optionalNotes || "";
  elements.automationRequiredDataFields.value = (plan.requiredDataFields || []).join(", ");
  setSelected(elements.automationDesiredActions, plan.desiredActions || []);
  setSelected(elements.automationToolsInUse, plan.toolsInUse || []);
  setSelected(elements.automationRolesInvolved, plan.rolesInvolved || []);
  setSelected(elements.automationExceptionRules, plan.exceptionRules || []);
  elements.activeAutomationTitle.textContent = plan.automationName;
  elements.activeAutomationMeta.textContent = `${plan.category} • ${plan.status} • Updated ${new Date(plan.updatedAt).toLocaleString()}`;

  AUTOMATION_SECTION_TITLES.forEach((title) => {
    if (title === "Implementation Checklist") {
      elements.automationSectionsContainer.append(renderAutomationChecklist(plan));
      return;
    }
    const fragment = elements.sectionTemplate.content.cloneNode(true);
    const label = fragment.querySelector(".section-title");
    const textarea = fragment.querySelector(".section-textarea");
    label.textContent = title;
    textarea.value = plan.sections[title] || "";
    textarea.addEventListener("input", () => {
      plan.sections[title] = textarea.value;
      plan.updatedAt = new Date().toISOString();
      persistAutomationPlans();
      renderAutomationList();
    });
    elements.automationSectionsContainer.append(fragment);
  });
}

function selectAutomationPlan(id) {
  state.activeAutomationId = id;
  clearMessage();
  renderAutomationList();
  renderAutomationEditor();
}

function saveActiveAutomationFromForm({ rebuildSections = false } = {}) {
  if (!validateAutomationForm()) return;
  const values = collectAutomationValues();
  let plan = getActiveAutomationPlan();
  if (!plan) {
    plan = createAutomationPlan(values);
    state.automationPlans.unshift(plan);
    state.activeAutomationId = plan.id;
  } else {
    Object.assign(plan, values, { requiredDataFields: parseTags(values.requiredDataFields) });
    if (rebuildSections) {
      const generated = generateAutomationPlan(values);
      plan.sections = generated.sections;
      plan.checklist = generated.checklist;
    }
    syncAutomationChecklistSection(plan);
    plan.updatedAt = new Date().toISOString();
  }
  persistAutomationPlans();
  renderAutomationList();
  renderAutomationEditor();
}

function resetForNewAutomation() {
  state.activeAutomationId = null;
  elements.automationForm.reset();
  elements.automationCategory.value = AUTOMATION_CATEGORIES[0];
  elements.automationStatus.value = AUTOMATION_STATUSES[0];
  elements.automationTriggerType.value = AUTOMATION_TRIGGER_TYPES[0];
  elements.automationSourceChannel.value = AUTOMATION_SOURCE_CHANNELS[0];
  elements.automationSourceOfTruth.value = AUTOMATION_SOURCES_OF_TRUTH[0];
  elements.automationHumanReviewPoint.value = AUTOMATION_REVIEW_POINTS[0];
  elements.automationFrequency.value = AUTOMATION_FREQUENCIES[0];
  elements.automationVolume.value = AUTOMATION_VOLUMES[0];
  elements.automationSectionsContainer.replaceChildren();
  elements.activeAutomationTitle.textContent = "New automation plan";
  elements.activeAutomationMeta.textContent = "Answer the guided questions and generate an automation blueprint.";
  renderAutomationList();
}

function loadAutomationStarter(index) {
  const template = AUTOMATION_STARTER_TEMPLATES[index];
  if (!template) return;
  state.activeAutomationId = null;
  elements.automationName.value = template.automationName;
  elements.automationClientName.value = template.clientName;
  elements.automationIndustry.value = template.industry;
  elements.automationCategory.value = template.category;
  elements.automationStatus.value = template.status;
  elements.automationBusinessProblem.value = template.businessProblem;
  elements.automationTriggerType.value = template.triggerType;
  elements.automationSourceChannel.value = template.sourceChannel;
  elements.automationSourceOfTruth.value = template.sourceOfTruth;
  elements.automationHumanReviewPoint.value = template.humanReviewPoint;
  elements.automationFrequency.value = template.frequency;
  elements.automationVolume.value = template.volume;
  elements.automationSuccessMetric.value = template.successMetric;
  elements.automationManualFallback.value = template.manualFallback;
  elements.automationOptionalNotes.value = template.optionalNotes;
  elements.automationRequiredDataFields.value = template.requiredDataFields.join(", ");
  setSelected(elements.automationDesiredActions, template.desiredActions);
  setSelected(elements.automationToolsInUse, template.toolsInUse);
  setSelected(elements.automationRolesInvolved, template.rolesInvolved);
  setSelected(elements.automationExceptionRules, template.exceptionRules);
  elements.activeAutomationTitle.textContent = `${template.automationName} starter`;
  elements.activeAutomationMeta.textContent = "Review the starter details, then generate an automation plan.";
  elements.automationSectionsContainer.replaceChildren();
}

function duplicateActiveAutomation() {
  const plan = getActiveAutomationPlan();
  if (!plan) return;
  const copy = duplicateAutomationPlan(plan);
  state.automationPlans.unshift(copy);
  state.activeAutomationId = copy.id;
  persistAutomationPlans();
  renderAutomationList();
  renderAutomationEditor();
}

function deleteActiveAutomation() {
  const plan = getActiveAutomationPlan();
  if (!plan) return;
  if (!window.confirm(`Delete "${plan.automationName}" from local storage?`)) return;
  state.automationPlans = state.automationPlans.filter((item) => item.id !== plan.id);
  state.activeAutomationId = state.automationPlans[0]?.id || null;
  persistAutomationPlans();
  renderAutomationList();
  renderAutomationEditor();
}

function addChecklistItemToActiveAutomation() {
  const plan = getActiveAutomationPlan();
  if (!plan) {
    showMessage("Generate or open an automation plan before adding checklist items.");
    return;
  }
  addAutomationChecklistItem(plan);
  persistAutomationPlans();
  renderAutomationEditor();
}

function exportActiveAutomation(checklistOnly = false) {
  const plan = getActiveAutomationPlan();
  if (!plan) return;
  const filename = checklistOnly ? `${slugify(plan.automationName)}-implementation-checklist.md` : `${slugify(plan.automationName)}-automation-plan.md`;
  downloadText(filename, checklistOnly ? automationChecklistToMarkdown(plan) : automationPlanToMarkdown(plan));
}

async function copyActiveAutomation(checklistOnly = false) {
  const plan = getActiveAutomationPlan();
  if (!plan) return;
  const text = checklistOnly ? automationChecklistToMarkdown(plan) : automationPlanToMarkdown(plan);
  try {
    await navigator.clipboard.writeText(text);
    showMessage(checklistOnly ? "Automation checklist Markdown copied to clipboard." : "Automation plan Markdown copied to clipboard.", "success");
  } catch {
    showMessage("Clipboard copy failed in this browser. Use Markdown export instead.");
  }
}

function exportAutomationBackup() {
  downloadText(`automation-builder-backup-${new Date().toISOString().slice(0, 10)}.json`, automationPlansToBackup(state.automationPlans), "application/json;charset=utf-8");
}

function importAutomationBackup(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      const imported = parseAutomationBackup(String(reader.result || ""));
      state.automationPlans = imported;
      state.activeAutomationId = state.automationPlans[0]?.id || null;
      persistAutomationPlans();
      renderAutomationList();
      renderAutomationEditor();
      showMessage("Automation JSON backup imported successfully.", "success");
    } catch (error) {
      showMessage(error.message || "Invalid automation JSON backup.");
    } finally {
      elements.importAutomationBackupInput.value = "";
    }
  });
  reader.addEventListener("error", () => showMessage("Invalid automation JSON backup. The file could not be read."));
  reader.readAsText(file);
}

function switchMode(mode) {
  state.mode = mode;
  const automation = mode === "automation";
  elements.processMode.hidden = automation;
  elements.automationMode.hidden = !automation;
  elements.processModeBtn.classList.toggle("button-primary", !automation);
  elements.automationModeBtn.classList.toggle("button-primary", automation);
  clearMessage();
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
  elements.copyMarkdownBtn.addEventListener("click", () => copyActive(false));
  elements.copyChecklistBtn.addEventListener("click", () => copyActive(true));
  elements.exportBackupBtn.addEventListener("click", exportBackup);
  elements.importBackupInput.addEventListener("change", (event) => importBackup(event.target.files[0]));
  elements.addChecklistItemBtn.addEventListener("click", addChecklistItemToActiveProcess);
  elements.searchInput.addEventListener("input", renderList);
  elements.starterSelect.addEventListener("change", (event) => loadStarter(event.target.value));
  elements.processModeBtn.addEventListener("click", () => switchMode("process"));
  elements.automationModeBtn.addEventListener("click", () => switchMode("automation"));
  elements.automationForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveActiveAutomationFromForm({ rebuildSections: true });
  });
  elements.saveAutomationBtn.addEventListener("click", () => saveActiveAutomationFromForm());
  elements.duplicateAutomationBtn.addEventListener("click", duplicateActiveAutomation);
  elements.deleteAutomationBtn.addEventListener("click", deleteActiveAutomation);
  elements.addAutomationChecklistItemBtn.addEventListener("click", addChecklistItemToActiveAutomation);
  elements.exportAutomationMarkdownBtn.addEventListener("click", () => exportActiveAutomation(false));
  elements.copyAutomationMarkdownBtn.addEventListener("click", () => copyActiveAutomation(false));
  elements.exportAutomationChecklistBtn.addEventListener("click", () => exportActiveAutomation(true));
  elements.copyAutomationChecklistBtn.addEventListener("click", () => copyActiveAutomation(true));
  elements.exportAutomationBackupBtn.addEventListener("click", exportAutomationBackup);
  elements.importAutomationBackupInput.addEventListener("change", (event) => importAutomationBackup(event.target.files[0]));
  elements.automationSearchInput.addEventListener("input", renderAutomationList);
  elements.automationStarterSelect.addEventListener("change", (event) => loadAutomationStarter(event.target.value));
}

function init() {
  populateSelect(elements.category, PROCESS_CATEGORIES);
  populateSelect(elements.status, STATUS_OPTIONS);
  populateStarterSelect();
  populateSelect(elements.automationIndustry, AUTOMATION_INDUSTRIES);
  populateSelect(elements.automationCategory, AUTOMATION_CATEGORIES);
  populateSelect(elements.automationStatus, AUTOMATION_STATUSES);
  populateSelect(elements.automationTriggerType, AUTOMATION_TRIGGER_TYPES);
  populateSelect(elements.automationSourceChannel, AUTOMATION_SOURCE_CHANNELS);
  populateSelect(elements.automationSourceOfTruth, AUTOMATION_SOURCES_OF_TRUTH);
  populateSelect(elements.automationHumanReviewPoint, AUTOMATION_REVIEW_POINTS);
  populateSelect(elements.automationFrequency, AUTOMATION_FREQUENCIES);
  populateSelect(elements.automationVolume, AUTOMATION_VOLUMES);
  populateSelect(elements.automationDesiredActions, AUTOMATION_ACTIONS);
  populateSelect(elements.automationToolsInUse, AUTOMATION_TOOLS);
  populateSelect(elements.automationRolesInvolved, AUTOMATION_ROLES);
  populateSelect(elements.automationExceptionRules, AUTOMATION_EXCEPTION_RULES);
  populateAutomationStarterSelect();
  state.processes = loadProcesses();
  state.activeId = state.processes[0]?.id || null;
  state.automationPlans = loadAutomationPlans();
  state.activeAutomationId = state.automationPlans[0]?.id || null;
  bindEvents();
  renderList();
  renderEditor();
  renderAutomationList();
  renderAutomationEditor();
  switchMode("process");
}

init();

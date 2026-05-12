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

const state = {
  processes: [],
  activeId: null,
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
  errorBanner: document.querySelector("#errorBanner"),
  starterSelect: document.querySelector("#starterSelect"),
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
  select.innerHTML = options.map((option) => `<option value="${option}">${option}</option>`).join("");
}

function populateStarterSelect() {
  elements.starterSelect.innerHTML = `<option value="">Start blank or load a starter...</option>${STARTER_TEMPLATES.map((template, index) => `<option value="${index}">${template.name}</option>`).join("")}`;
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
  elements.processList.innerHTML = "";

  filtered.forEach((process) => {
    const item = document.createElement("article");
    item.className = `process-item${process.id === state.activeId ? " active" : ""}`;
    item.innerHTML = `
      <button type="button" class="process-open">
        <strong>${process.name}</strong>
        <span>${process.category} • ${process.status}</span>
        <small>Updated ${new Date(process.updatedAt).toLocaleString()}</small>
      </button>
      <select class="status-mini" aria-label="Change status for ${process.name}">
        ${STATUS_OPTIONS.map((status) => `<option value="${status}" ${status === process.status ? "selected" : ""}>${status}</option>`).join("")}
      </select>
    `;
    item.querySelector(".process-open").addEventListener("click", () => selectProcess(process.id));
    item.querySelector(".status-mini").addEventListener("change", (event) => {
      process.status = event.target.value;
      touch(process);
      persistProcesses();
      renderList();
      renderEditor();
    });
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
  wrapper.innerHTML = `
    <div class="section-heading">
      <h3>Internal checklist</h3>
      <p>Edit checklist items, completion status, and notes. Export can include this section separately.</p>
    </div>
    <div class="checklist-list"></div>
  `;
  const list = wrapper.querySelector(".checklist-list");
  process.checklist.forEach((item) => list.append(renderChecklistItem(process, item)));
  return wrapper;
}

function renderEditor() {
  const process = getActiveProcess();
  elements.sectionsContainer.innerHTML = "";

  if (!process) {
    elements.activeProcessTitle.textContent = "New process";
    elements.activeProcessMeta.textContent = "Enter rough notes and generate a process document.";
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
  elements.sectionsContainer.innerHTML = "";
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
  elements.sectionsContainer.innerHTML = "";
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

function addChecklistItem() {
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
  elements.addChecklistItemBtn.addEventListener("click", addChecklistItem);
  elements.searchInput.addEventListener("input", renderList);
  elements.starterSelect.addEventListener("change", (event) => loadStarter(event.target.value));
}

function init() {
  populateSelect(elements.category, PROCESS_CATEGORIES);
  populateSelect(elements.status, STATUS_OPTIONS);
  populateStarterSelect();
  state.processes = loadProcesses();
  state.activeId = state.processes[0]?.id || null;
  bindEvents();
  renderList();
  renderEditor();
}

init();

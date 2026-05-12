import {
  escapeHtml,
  formatAnswer,
  generateClientRequestEmail,
  generateClientRequestPrintHtml,
  generateInternalChecklistPrintHtml,
  groupTasksByCategory
} from './outputs.js';
import { PARTY_TYPES } from './models.js';
import { buildChecklist, duplicateChecklist, getWorkflowQuestions, regenerateChecklist, workflows } from './workflows.js';

const STORAGE_KEY = 'workflow-task-checklists';

const form = document.querySelector('#checklist-form');
const workflowSelect = document.querySelector('#workflow');
const partyTypeSelect = document.querySelector('#party-type');
const checklistsContainer = document.querySelector('#checklists');
const intakeQuestionnaire = document.querySelector('#intake-questionnaire');
const summary = document.querySelector('#summary');
const emptyStateTemplate = document.querySelector('#empty-state-template');
const clearAllButton = document.querySelector('#clear-all');

let checklists = loadChecklists();
let editingChecklistId = null;

function loadChecklists() {
  const savedChecklists = localStorage.getItem(STORAGE_KEY);

  if (!savedChecklists) {
    return [];
  }

  try {
    return JSON.parse(savedChecklists);
  } catch (error) {
    console.warn('Unable to load saved checklists. Starting fresh.', error);
    return [];
  }
}

function saveChecklists() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(checklists));
}

function formatDate(dateValue) {
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC'
  }).format(new Date(`${dateValue}T12:00:00Z`));
}

function populatePartyTypeOptions() {
  partyTypeSelect.innerHTML = Object.entries(PARTY_TYPES)
    .map(([key, label]) => `<option value="${key}">${label}</option>`)
    .join('');
}

function populateWorkflowOptions() {
  workflowSelect.innerHTML = Object.entries(workflows)
    .map(([key, workflow]) => `<option value="${key}">${workflow.name}</option>`)
    .join('');
}

function renderQuestionFields(questions, answers = {}, namePrefix = 'question') {
  return questions
    .map(
      (question) => `
        <label>
          ${escapeHtml(question.label)}
          <select name="${namePrefix}:${escapeHtml(question.id)}">
            <option value="" ${!answers[question.id] ? 'selected' : ''}>No answer</option>
            <option value="yes" ${answers[question.id] === 'yes' ? 'selected' : ''}>Yes</option>
            <option value="no" ${answers[question.id] === 'no' ? 'selected' : ''}>No</option>
          </select>
        </label>
      `
    )
    .join('');
}

function renderIntakeQuestions() {
  const selectedWorkflow = workflows[workflowSelect.value];
  const questions = getWorkflowQuestions(workflowSelect.value);

  if (!questions.length) {
    intakeQuestionnaire.innerHTML = '';
    intakeQuestionnaire.hidden = true;
    return;
  }

  intakeQuestionnaire.hidden = false;
  intakeQuestionnaire.innerHTML = `
    <div class="intake-heading">
      <div>
        <p class="eyebrow">Optional intake</p>
        <h3>${escapeHtml(selectedWorkflow.name)} questions</h3>
      </div>
      <p>Answers are saved with the checklist and may add conditional tasks.</p>
    </div>
    <div class="question-grid">
      ${renderQuestionFields(questions)}
    </div>
  `;
}

function getIntakeAnswers(formData, workflowKey) {
  return getIntakeAnswersFromPrefix(formData, workflowKey, 'question');
}

function getIntakeAnswersFromPrefix(formData, workflowKey, prefix) {
  return getWorkflowQuestions(workflowKey).reduce((answers, question) => {
    answers[question.id] = formData.get(`${prefix}:${question.id}`) ?? '';
    return answers;
  }, {});
}

function formatAudience(audience) {
  if (audience === 'client') {
    return 'Client-facing';
  }

  return 'Internal';
}

function renderSummary() {
  const totalTasks = checklists.reduce((total, checklist) => total + checklist.tasks.length, 0);
  const completeTasks = checklists.reduce(
    (total, checklist) => total + checklist.tasks.filter((task) => task.completed).length,
    0
  );

  summary.textContent = checklists.length
    ? `${checklists.length} checklist${checklists.length === 1 ? '' : 's'} • ${completeTasks}/${totalTasks} tasks complete`
    : 'Nothing saved yet';
}

function renderChecklists() {
  checklistsContainer.innerHTML = '';
  renderSummary();

  if (!checklists.length) {
    checklistsContainer.append(emptyStateTemplate.content.cloneNode(true));
    return;
  }

  checklists
    .slice()
    .sort((a, b) => new Date(a.dueDate) - new Date(b.dueDate))
    .forEach((checklist) => {
      checklistsContainer.append(createChecklistCard(checklist));
    });
}

function renderEditForm(checklist) {
  const questions = getWorkflowQuestions(checklist.workflowKey);

  return `
    <form class="edit-checklist-form" data-action="save-edit">
      <div class="edit-grid">
        <label>
          Client name
          <input name="editClientName" type="text" value="${escapeHtml(checklist.clientName)}" required />
        </label>
        <label>
          Party type
          <select name="editPartyType">
            ${Object.entries(PARTY_TYPES)
              .map(
                ([key, label]) =>
                  `<option value="${key}" ${checklist.party?.partyType === key ? 'selected' : ''}>${label}</option>`
              )
              .join('')}
          </select>
        </label>
        <label>
          Due date
          <input name="editDueDate" type="date" value="${escapeHtml(checklist.dueDate)}" required />
        </label>
      </div>
      <div class="edit-questions">
        <div class="intake-heading">
          <div>
            <p class="eyebrow">Edit intake</p>
            <h4>${escapeHtml(checklist.workflowName)} questions</h4>
          </div>
          <p>Changing answers regenerates tasks while preserving notes and completion for matching tasks.</p>
        </div>
        <div class="question-grid">
          ${renderQuestionFields(questions, checklist.intakeAnswers ?? {}, 'editQuestion')}
        </div>
      </div>
      <div class="edit-actions">
        <button class="button button-primary" type="submit">Save changes</button>
        <button class="button button-ghost" data-action="cancel-edit" type="button">Cancel</button>
      </div>
    </form>
  `;
}

function createChecklistCard(checklist) {
  const completedTasks = checklist.tasks.filter((task) => task.completed).length;
  const intakeAnswers = checklist.intakeAnswers ?? {};
  const workflowQuestions = getWorkflowQuestions(checklist.workflowKey);
  const editForm = editingChecklistId === checklist.id ? renderEditForm(checklist) : '';
  const intakeSummary = workflowQuestions.length
    ? `
      <details class="answer-summary">
        <summary>Intake answers</summary>
        <dl>
          ${workflowQuestions
            .map(
              (question) => `
                <div>
                  <dt>${escapeHtml(question.label)}</dt>
                  <dd>${formatAnswer(intakeAnswers[question.id])}</dd>
                </div>
              `
            )
            .join('')}
        </dl>
      </details>
    `
    : '';
  const article = document.createElement('article');
  article.className = 'checklist-card';
  article.dataset.checklistId = checklist.id;

  article.innerHTML = `
    <div class="card-header">
      <div>
        <p class="eyebrow">${escapeHtml(checklist.workflowName)}</p>
        <h3>${escapeHtml(checklist.clientName)}</h3>
        <p class="description">${escapeHtml(PARTY_TYPES[checklist.party?.partyType] ?? 'Party')} • Due ${formatDate(checklist.dueDate)} • ${completedTasks}/${checklist.tasks.length} complete</p>
      </div>
      <div class="card-actions">
        <button class="button button-ghost" data-action="edit-checklist" type="button">Edit</button>
        <button class="button button-ghost" data-action="duplicate-checklist" type="button">Duplicate</button>
        <button class="button button-ghost" data-action="copy-client-email" type="button">Copy client request email</button>
        <button class="button button-ghost" data-action="print-client-list" type="button">Print client request list</button>
        <button class="button button-ghost" data-action="print-internal-checklist" type="button">Print internal checklist</button>
        <button class="button button-danger" data-action="delete-checklist" type="button">Delete</button>
      </div>
    </div>
    ${editForm}
    ${intakeSummary}
    <div class="task-groups"></div>
  `;

  const taskGroups = article.querySelector('.task-groups');

  groupTasksByCategory(checklist.tasks).forEach(({ category, tasks }) => {
    const categorySection = document.createElement('section');
    categorySection.className = 'task-category';
    categorySection.innerHTML = `
      <div class="category-heading">
        <h4>${escapeHtml(category)}</h4>
        <span>${tasks.length} task${tasks.length === 1 ? '' : 's'}</span>
      </div>
      <ol class="task-list"></ol>
    `;

    const taskList = categorySection.querySelector('.task-list');

    tasks.forEach((task) => {
      const taskItem = document.createElement('li');
      taskItem.className = task.completed ? 'task-item is-complete' : 'task-item';
      taskItem.dataset.taskId = task.id;
      taskItem.innerHTML = `
        <div class="task-main">
          <label class="task-check">
            <input type="checkbox" ${task.completed ? 'checked' : ''} data-action="toggle-task" />
            <span>${escapeHtml(task.title)}</span>
          </label>
          <div class="task-meta">
            <span class="audience-badge audience-${escapeHtml(task.audience || 'internal')}">${escapeHtml(task.audienceLabel || formatAudience(task.audience))}</span>
            <time datetime="${task.suggestedDate}">${formatDate(task.suggestedDate)}</time>
          </div>
        </div>
        <label class="notes-label">
          Notes
          <textarea data-action="update-notes" rows="2" placeholder="Add notes, questions, or follow-up details">${escapeHtml(task.notes)}</textarea>
        </label>
      `;
      taskList.append(taskItem);
    });

    taskGroups.append(categorySection);
  });

  return article;
}

function findChecklist(checklistId) {
  return checklists.find((checklist) => checklist.id === checklistId);
}

function handleSubmit(event) {
  event.preventDefault();
  const formData = new FormData(form);
  const workflowKey = formData.get('workflow');
  const checklist = buildChecklist({
    clientName: formData.get('clientName'),
    dueDate: formData.get('dueDate'),
    workflowKey,
    partyType: formData.get('partyType'),
    answers: getIntakeAnswers(formData, workflowKey)
  });

  checklists = [checklist, ...checklists];
  editingChecklistId = null;
  saveChecklists();
  form.reset();
  renderIntakeQuestions();
  renderChecklists();
}


async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.top = '-9999px';
  document.body.append(textarea);
  textarea.select();
  document.execCommand('copy');
  textarea.remove();
}

function printHtmlDocument(html) {
  const printWindow = window.open('', '_blank');

  if (!printWindow) {
    window.alert('Unable to open the print window. Please allow popups for this local app and try again.');
    return;
  }

  printWindow.document.open();
  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
}

async function handleChecklistInteraction(event) {
  const action = event.target.dataset.action;

  const clickActions = [
    'delete-checklist',
    'edit-checklist',
    'cancel-edit',
    'duplicate-checklist',
    'copy-client-email',
    'print-client-list',
    'print-internal-checklist'
  ];

  if (!action || (event.type === 'click' && !clickActions.includes(action))) {
    return;
  }

  const checklistCard = event.target.closest('.checklist-card');
  const checklist = findChecklist(checklistCard.dataset.checklistId);

  if (!checklist) {
    return;
  }

  if (action === 'edit-checklist') {
    editingChecklistId = checklist.id;
    renderChecklists();
    return;
  }

  if (action === 'cancel-edit') {
    editingChecklistId = null;
    renderChecklists();
    return;
  }

  if (action === 'duplicate-checklist') {
    checklists = [duplicateChecklist(checklist), ...checklists];
    editingChecklistId = null;
    saveChecklists();
    renderChecklists();
    return;
  }

  if (action === 'save-edit') {
    event.preventDefault();
    const formData = new FormData(event.target);
    const updatedChecklist = regenerateChecklist(checklist, {
      clientName: formData.get('editClientName'),
      dueDate: formData.get('editDueDate'),
      partyType: formData.get('editPartyType'),
      answers: getIntakeAnswersFromPrefix(formData, checklist.workflowKey, 'editQuestion')
    });
    checklists = checklists.map((savedChecklist) =>
      savedChecklist.id === updatedChecklist.id ? updatedChecklist : savedChecklist
    );
    editingChecklistId = null;
    saveChecklists();
    renderChecklists();
    return;
  }

  if (action === 'copy-client-email') {
    try {
      await copyTextToClipboard(generateClientRequestEmail(checklist));
      event.target.textContent = 'Copied';
      window.setTimeout(() => {
        event.target.textContent = 'Copy client request email';
      }, 1600);
    } catch (error) {
      console.error('Unable to copy client request email.', error);
      window.alert('Unable to copy the email. Please try again or use a supported browser.');
    }
    return;
  }

  if (action === 'print-client-list') {
    printHtmlDocument(generateClientRequestPrintHtml(checklist));
    return;
  }

  if (action === 'print-internal-checklist') {
    printHtmlDocument(generateInternalChecklistPrintHtml(checklist));
    return;
  }

  if (action === 'delete-checklist') {
    checklists = checklists.filter((savedChecklist) => savedChecklist.id !== checklist.id);
    if (editingChecklistId === checklist.id) {
      editingChecklistId = null;
    }
  }

  if (action === 'toggle-task') {
    const taskItem = event.target.closest('.task-item');
    const task = checklist.tasks.find((savedTask) => savedTask.id === taskItem.dataset.taskId);
    task.completed = event.target.checked;
  }

  if (action === 'update-notes') {
    const taskItem = event.target.closest('.task-item');
    const task = checklist.tasks.find((savedTask) => savedTask.id === taskItem.dataset.taskId);
    task.notes = event.target.value;
    saveChecklists();
    return;
  }

  saveChecklists();
  renderChecklists();
}

function clearAllData() {
  const confirmed = window.confirm('Delete all saved checklists from this browser?');

  if (!confirmed) {
    return;
  }

  checklists = [];
  saveChecklists();
  renderChecklists();
}

populatePartyTypeOptions();
populateWorkflowOptions();
renderIntakeQuestions();
renderChecklists();

form.addEventListener('submit', handleSubmit);
workflowSelect.addEventListener('change', renderIntakeQuestions);
checklistsContainer.addEventListener('submit', handleChecklistInteraction);
checklistsContainer.addEventListener('change', handleChecklistInteraction);
checklistsContainer.addEventListener('input', handleChecklistInteraction);
checklistsContainer.addEventListener('click', handleChecklistInteraction);
clearAllButton.addEventListener('click', clearAllData);

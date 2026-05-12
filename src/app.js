import { buildChecklist, getWorkflowQuestions, workflows } from './workflows.js';

const STORAGE_KEY = 'workflow-task-checklists';

const form = document.querySelector('#checklist-form');
const workflowSelect = document.querySelector('#workflow');
const checklistsContainer = document.querySelector('#checklists');
const intakeQuestionnaire = document.querySelector('#intake-questionnaire');
const summary = document.querySelector('#summary');
const emptyStateTemplate = document.querySelector('#empty-state-template');
const clearAllButton = document.querySelector('#clear-all');

let checklists = loadChecklists();

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

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('\"', '&quot;')
    .replaceAll("'", '&#039;');
}

function formatDate(dateValue) {
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC'
  }).format(new Date(`${dateValue}T12:00:00Z`));
}

function populateWorkflowOptions() {
  workflowSelect.innerHTML = Object.entries(workflows)
    .map(([key, workflow]) => `<option value="${key}">${workflow.name}</option>`)
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
      ${questions
        .map(
          (question) => `
            <label>
              ${escapeHtml(question.label)}
              <select name="question:${escapeHtml(question.id)}">
                <option value="">No answer</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </label>
          `
        )
        .join('')}
    </div>
  `;
}

function getIntakeAnswers(formData, workflowKey) {
  return getWorkflowQuestions(workflowKey).reduce((answers, question) => {
    answers[question.id] = formData.get(`question:${question.id}`) ?? '';
    return answers;
  }, {});
}

function formatAudience(audience) {
  if (audience === 'client') {
    return 'Client-facing';
  }

  return 'Internal';
}

function groupTasksByCategory(tasks) {
  return tasks.reduce((groups, task) => {
    const category = task.category || 'General';

    if (!groups.has(category)) {
      groups.set(category, []);
    }

    groups.get(category).push(task);
    return groups;
  }, new Map());
}

function formatAnswer(value) {
  if (value === 'yes') {
    return 'Yes';
  }

  if (value === 'no') {
    return 'No';
  }

  return 'No answer';
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

function createChecklistCard(checklist) {
  const completedTasks = checklist.tasks.filter((task) => task.completed).length;
  const intakeAnswers = checklist.intakeAnswers ?? {};
  const workflowQuestions = getWorkflowQuestions(checklist.workflowKey);
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
        <p class="description">Due ${formatDate(checklist.dueDate)} • ${completedTasks}/${checklist.tasks.length} complete</p>
      </div>
      <button class="button button-danger" data-action="delete-checklist" type="button">Delete</button>
    </div>
    ${intakeSummary}
    <div class="task-groups"></div>
  `;

  const taskGroups = article.querySelector('.task-groups');

  groupTasksByCategory(checklist.tasks).forEach((tasks, category) => {
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
    answers: getIntakeAnswers(formData, workflowKey)
  });

  checklists = [checklist, ...checklists];
  saveChecklists();
  form.reset();
  renderIntakeQuestions();
  renderChecklists();
}

function handleChecklistInteraction(event) {
  const action = event.target.dataset.action;

  if (!action || (event.type === 'click' && action !== 'delete-checklist')) {
    return;
  }

  const checklistCard = event.target.closest('.checklist-card');
  const checklist = findChecklist(checklistCard.dataset.checklistId);

  if (!checklist) {
    return;
  }

  if (action === 'delete-checklist') {
    checklists = checklists.filter((savedChecklist) => savedChecklist.id !== checklist.id);
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

populateWorkflowOptions();
renderIntakeQuestions();
renderChecklists();

form.addEventListener('submit', handleSubmit);
workflowSelect.addEventListener('change', renderIntakeQuestions);
checklistsContainer.addEventListener('change', handleChecklistInteraction);
checklistsContainer.addEventListener('input', handleChecklistInteraction);
checklistsContainer.addEventListener('click', handleChecklistInteraction);
clearAllButton.addEventListener('click', clearAllData);

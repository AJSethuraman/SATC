import {
  escapeHtml,
  formatAnswer,
  generateClientRequestEmail,
  generateClientRequestPrintHtml,
  generateInternalChecklistPrintHtml,
  groupTasksByCategory
} from './outputs.js';
import {
  CLIENT_TYPES,
  RELATIONSHIP_TYPES,
  createBusinessClient,
  createId,
  createPersonClient,
  createRelationship,
  getLinkedClients,
  getRelationshipsForClient
} from './models.js';
import {
  buildEngagementForClient,
  getWorkflowKeysForClientType,
  getWorkflowQuestions,
  regenerateEngagementForClient,
  workflows
} from './workflows.js';

const STORAGE_KEY = 'satc-client-engagement-state';
const LEGACY_CHECKLIST_KEY = 'workflow-task-checklists';

const clientIndex = document.querySelector('#client-index');
const clientDetail = document.querySelector('#client-detail');
const engagementBuilder = document.querySelector('#engagement-builder');
const engagementList = document.querySelector('#engagement-list');
const summary = document.querySelector('#summary');
const emptyStateTemplate = document.querySelector('#empty-state-template');
const clearAllButton = document.querySelector('#clear-all');

let state = loadState();
let selectedClientId = state.clients[0]?.id ?? '';
let clientFilter = 'all';
let editingEngagementId = null;

function loadState() {
  const savedState = localStorage.getItem(STORAGE_KEY);

  if (savedState) {
    try {
      const parsed = JSON.parse(savedState);
      return {
        clients: parsed.clients ?? [],
        relationships: parsed.relationships ?? [],
        engagements: parsed.engagements ?? []
      };
    } catch (error) {
      console.warn('Unable to load saved client engagement state. Starting fresh.', error);
    }
  }

  const legacyChecklists = localStorage.getItem(LEGACY_CHECKLIST_KEY);

  if (!legacyChecklists) {
    return { clients: [], relationships: [], engagements: [] };
  }

  try {
    const checklists = JSON.parse(legacyChecklists);
    const clients = [];
    const engagements = checklists.map((checklist) => {
      const client = checklist.party?.id
        ? checklist.party
        : createPersonClient({ firstName: checklist.clientName, lastName: 'Client' });
      clients.push(client);
      return {
        ...checklist,
        clientId: client.id,
        engagementType: checklist.engagement?.engagementType ?? workflows[checklist.workflowKey]?.engagementType,
        taxYear: '',
        periodEnd: '',
        relatedClientIds: [],
        riskFlags: checklist.riskFlags ?? []
      };
    });

    return { clients, relationships: [], engagements };
  } catch (error) {
    console.warn('Unable to migrate legacy checklists. Starting fresh.', error);
    return { clients: [], relationships: [], engagements: [] };
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function formatDate(dateValue) {
  if (!dateValue) {
    return 'No date';
  }

  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC'
  }).format(new Date(`${dateValue}T12:00:00Z`));
}

function selectedClient() {
  return state.clients.find((client) => client.id === selectedClientId);
}

function relationshipsForSelectedClient() {
  return getRelationshipsForClient(state.relationships, selectedClientId);
}

function linkedClientsForSelectedClient() {
  return getLinkedClients(state.clients, state.relationships, selectedClientId);
}

function render() {
  if (!selectedClientId && state.clients.length) {
    selectedClientId = state.clients[0].id;
  }

  renderClientIndex();
  renderClientDetail();
  renderEngagementBuilder();
  renderEngagements();
  renderSummary();
}

function renderSummary() {
  summary.textContent = `${state.clients.length} client${state.clients.length === 1 ? '' : 's'} • ${state.relationships.length} relationship${state.relationships.length === 1 ? '' : 's'} • ${state.engagements.length} engagement${state.engagements.length === 1 ? '' : 's'}`;
}

function renderClientIndex() {
  const filteredClients = state.clients.filter((client) => clientFilter === 'all' || client.clientType === clientFilter);

  clientIndex.innerHTML = `
    <div class="filter-row" role="group" aria-label="Filter clients">
      ${['all', 'person', 'business']
        .map(
          (filter) =>
            `<button class="button ${clientFilter === filter ? 'button-primary' : 'button-ghost'}" data-action="filter-clients" data-filter="${filter}" type="button">${filter === 'all' ? 'All' : CLIENT_TYPES[filter]}</button>`
        )
        .join('')}
    </div>

    <div class="client-list">
      ${
        filteredClients.length
          ? filteredClients
              .map(
                (client) => `
                  <button class="client-card ${client.id === selectedClientId ? 'is-selected' : ''}" data-action="select-client" data-client-id="${client.id}" type="button">
                    <span class="tag">${CLIENT_TYPES[client.clientType]}</span>
                    <strong>${escapeHtml(client.displayName)}</strong>
                    <small>${escapeHtml(client.email || client.phone || 'No contact details')}</small>
                  </button>
                `
              )
              .join('')
          : '<div class="empty-state"><h3>No matching clients</h3><p>Create a person or business below.</p></div>'
      }
    </div>

    <details class="composer" open>
      <summary>Create new person</summary>
      <form data-action="create-person" class="stacked-form">
        <div class="edit-grid">
          <label>First name<input name="firstName" required /></label>
          <label>Last name<input name="lastName" required /></label>
        </div>
        <label>Email<input name="email" type="email" /></label>
        <label>Phone<input name="phone" /></label>
        <label>Notes<textarea name="notes" rows="2"></textarea></label>
        <button class="button button-primary" type="submit">Create person</button>
      </form>
    </details>

    <details class="composer">
      <summary>Create new business</summary>
      <form data-action="create-business" class="stacked-form">
        <label>Legal name<input name="legalName" required /></label>
        <label>DBA name<input name="dbaName" /></label>
        <div class="edit-grid">
          <label>Entity type<input name="entityType" placeholder="LLC, corporation, partnership" /></label>
          <label>Tax treatment
            <select name="taxTreatment">
              <option value="">Not set</option>
              <option value="soleProp">Disregarded / sole proprietor context</option>
              <option value="sCorp">S corporation</option>
              <option value="partnership">Partnership</option>
              <option value="cCorp">C corporation</option>
            </select>
          </label>
        </div>
        <label>EIN last 4<input name="einLast4" maxlength="4" /></label>
        <label>Email<input name="email" type="email" /></label>
        <label>Phone<input name="phone" /></label>
        <label>Notes<textarea name="notes" rows="2"></textarea></label>
        <button class="button button-primary" type="submit">Create business</button>
      </form>
    </details>
  `;
}

function renderClientDetail() {
  const client = selectedClient();

  if (!client) {
    clientDetail.innerHTML = emptyStateTemplate.innerHTML;
    return;
  }

  const linkedClients = linkedClientsForSelectedClient();
  const relationships = relationshipsForSelectedClient();
  const linkableClients = state.clients.filter((savedClient) => savedClient.id !== client.id);

  clientDetail.innerHTML = `
    <article class="detail-card">
      <span class="tag">${CLIENT_TYPES[client.clientType]}</span>
      <h3>${escapeHtml(client.displayName)}</h3>
      <p>${escapeHtml(client.email || 'No email')} • ${escapeHtml(client.phone || 'No phone')}</p>
      ${client.clientType === 'business' ? `<p>Entity: ${escapeHtml(client.entityType || 'Not set')} • Tax treatment: ${escapeHtml(client.taxTreatment || 'Not set')} • EIN last 4: ${escapeHtml(client.einLast4 || 'Not set')}</p>` : ''}
      ${client.notes ? `<p>${escapeHtml(client.notes)}</p>` : ''}
    </article>

    <details open>
      <summary>Linked clients</summary>
      <div class="linked-list">
        ${
          relationships.length
            ? relationships
                .map((relationship) => {
                  const linkedClient = state.clients.find((savedClient) =>
                    savedClient.id === (relationship.fromClientId === client.id ? relationship.toClientId : relationship.fromClientId)
                  );
                  return `
                    <div class="linked-row">
                      <div>
                        <strong>${escapeHtml(linkedClient?.displayName ?? 'Missing client')}</strong>
                        <span class="tag">${escapeHtml(RELATIONSHIP_TYPES[relationship.relationshipType] ?? relationship.relationshipType)}</span>
                        ${relationship.ownershipPercent ? `<span class="tag">${escapeHtml(relationship.ownershipPercent)}%</span>` : ''}
                        ${relationship.isPrimary ? '<span class="tag">Primary</span>' : ''}
                      </div>
                      <button class="button button-danger" data-action="delete-relationship" data-relationship-id="${relationship.id}" type="button">Delete link</button>
                    </div>
                  `;
                })
                .join('')
            : '<p>No linked clients yet.</p>'
        }
      </div>
    </details>

    <details class="composer">
      <summary>Add relationship to existing client</summary>
      <form data-action="create-relationship" class="stacked-form">
        <label>Linked client
          <select name="toClientId" required>
            ${linkableClients.map((linkedClient) => `<option value="${linkedClient.id}">${escapeHtml(linkedClient.displayName)} (${CLIENT_TYPES[linkedClient.clientType]})</option>`).join('')}
          </select>
        </label>
        <div class="edit-grid">
          <label>Relationship type
            <select name="relationshipType" required>
              ${Object.entries(RELATIONSHIP_TYPES).map(([key, label]) => `<option value="${key}">${label}</option>`).join('')}
            </select>
          </label>
          <label>Ownership %<input name="ownershipPercent" type="number" min="0" max="100" step="0.01" /></label>
        </div>
        <label><input name="isPrimary" type="checkbox" /> Primary contact / relationship</label>
        <label>Notes<textarea name="notes" rows="2"></textarea></label>
        <button class="button button-primary" type="submit" ${linkableClients.length ? '' : 'disabled'}>Add relationship</button>
      </form>
    </details>

    <details class="composer">
      <summary>Create a new linked client</summary>
      <form data-action="create-linked-client" class="stacked-form">
        <label>Client type
          <select name="clientType">
            <option value="person">Person</option>
            <option value="business">Business</option>
          </select>
        </label>
        <label>Name<input name="displayName" required /></label>
        <label>Relationship type
          <select name="relationshipType" required>
            ${Object.entries(RELATIONSHIP_TYPES).map(([key, label]) => `<option value="${key}">${label}</option>`).join('')}
          </select>
        </label>
        <button class="button button-primary" type="submit">Create and link</button>
      </form>
    </details>

    <details open>
      <summary>Engagements for this client</summary>
      ${renderEngagementSummaryList(client.id)}
    </details>
  `;
}

function renderEngagementSummaryList(clientId) {
  const engagements = state.engagements.filter((engagement) => engagement.clientId === clientId);

  if (!engagements.length) {
    return '<p>No engagements yet.</p>';
  }

  return engagements
    .map(
      (engagement) => `
        <div class="linked-row">
          <div>
            <strong>${escapeHtml(workflows[engagement.workflowKey]?.name ?? engagement.engagementType)}</strong>
            <span class="tag">Due ${formatDate(engagement.dueDate)}</span>
            ${engagement.taxYear ? `<span class="tag">Tax year ${escapeHtml(engagement.taxYear)}</span>` : ''}
          </div>
        </div>
      `
    )
    .join('');
}

function renderQuestionInput(question, answers = {}, namePrefix = 'question') {
  const value = answers[question.id] ?? '';
  const name = `${namePrefix}:${escapeHtml(question.id)}`;

  if (question.type === 'number') {
    return `<label>${escapeHtml(question.label)}<input name="${name}" type="number" value="${escapeHtml(value)}" /></label>`;
  }

  if (question.type === 'text') {
    return `<label>${escapeHtml(question.label)}<input name="${name}" value="${escapeHtml(value)}" /></label>`;
  }

  if (question.type === 'select') {
    return `<label>${escapeHtml(question.label)}<select name="${name}">${(question.options ?? []).map((option) => `<option value="${escapeHtml(option.value)}" ${value === option.value ? 'selected' : ''}>${escapeHtml(option.label)}</option>`).join('')}</select></label>`;
  }

  return `
    <label>${escapeHtml(question.label)}
      <select name="${name}">
        <option value="" ${!value ? 'selected' : ''}>No answer</option>
        <option value="yes" ${value === 'yes' ? 'selected' : ''}>Yes</option>
        <option value="no" ${value === 'no' ? 'selected' : ''}>No</option>
      </select>
    </label>
  `;
}

function renderQuestionFields(questions, answers = {}, namePrefix = 'question') {
  return questions.map((question) => renderQuestionInput(question, answers, namePrefix)).join('');
}

function renderEngagementBuilder() {
  const client = selectedClient();

  if (!client) {
    engagementBuilder.innerHTML = '<div class="empty-state"><h3>Select a client</h3><p>Create or select a client before building an engagement.</p></div>';
    return;
  }

  const workflowKeys = getWorkflowKeysForClientType(client.clientType);
  const selectedWorkflowKey = workflowKeys[0];
  const linkedClients = linkedClientsForSelectedClient();

  engagementBuilder.innerHTML = `
    <form data-action="create-engagement" class="engagement-form">
      <div class="edit-grid">
        <label>Engagement type
          <select name="workflowKey" data-action="change-builder-workflow">
            ${workflowKeys.map((workflowKey) => `<option value="${workflowKey}">${escapeHtml(workflows[workflowKey].name)}</option>`).join('')}
          </select>
        </label>
        <label>Tax year<input name="taxYear" placeholder="2026" /></label>
        <label>Period end<input name="periodEnd" type="date" /></label>
        <label>Due date<input name="dueDate" type="date" required /></label>
      </div>
      <details open>
        <summary>Linked-client context</summary>
        ${
          linkedClients.length
            ? linkedClients
                .map(
                  (linkedClient) => `
                    <label class="checkbox-row">
                      <input name="relatedClientIds" type="checkbox" value="${linkedClient.id}" checked />
                      Include ${escapeHtml(linkedClient.displayName)} (${CLIENT_TYPES[linkedClient.clientType]})
                    </label>
                  `
                )
                .join('')
            : '<p>No linked clients available for this engagement.</p>'
        }
      </details>
      <details open>
        <summary>Intake questions</summary>
        <div id="builder-questions" class="question-grid">
          ${renderQuestionFields(getWorkflowQuestions(selectedWorkflowKey))}
        </div>
      </details>
      <button class="button button-primary" type="submit">Generate engagement checklist</button>
    </form>
  `;
}

function renderEngagements() {
  const client = selectedClient();
  engagementList.innerHTML = '';

  if (!client) {
    return;
  }

  const clientEngagements = state.engagements.filter((engagement) => engagement.clientId === client.id);

  if (!clientEngagements.length) {
    engagementList.append(emptyStateTemplate.content.cloneNode(true));
    return;
  }

  clientEngagements
    .slice()
    .sort((a, b) => new Date(a.dueDate) - new Date(b.dueDate))
    .forEach((engagement) => engagementList.append(createEngagementCard(engagement)));
}

function createEngagementCard(engagement) {
  const client = state.clients.find((savedClient) => savedClient.id === engagement.clientId);
  const completedTasks = engagement.tasks.filter((task) => task.completed).length;
  const article = document.createElement('article');
  article.className = 'checklist-card';
  article.dataset.engagementId = engagement.id;
  article.innerHTML = `
    <div class="card-header">
      <div>
        <p class="eyebrow">${escapeHtml(workflows[engagement.workflowKey]?.name ?? engagement.engagementType)}</p>
        <h3>${escapeHtml(client?.displayName ?? 'Unknown client')}</h3>
        <p class="description">Due ${formatDate(engagement.dueDate)} • ${completedTasks}/${engagement.tasks.length} complete</p>
        <div class="tag-row">
          ${(engagement.riskFlags ?? []).map((flag) => `<span class="tag risk-tag">Risk: ${escapeHtml(flag)}</span>`).join('')}
        </div>
      </div>
      <div class="card-actions">
        <button class="button button-ghost" data-action="duplicate-engagement" type="button">Duplicate</button>
        <button class="button button-ghost" data-action="copy-client-email" type="button">Copy client request email</button>
        <button class="button button-ghost" data-action="print-client-list" type="button">Print client request list</button>
        <button class="button button-ghost" data-action="print-internal-checklist" type="button">Print internal checklist</button>
        <button class="button button-danger" data-action="delete-engagement" type="button">Delete</button>
      </div>
    </div>
    <details class="answer-summary">
      <summary>Intake answers and linked clients</summary>
      <dl>
        ${getWorkflowQuestions(engagement.workflowKey)
          .map((question) => `<div><dt>${escapeHtml(question.label)}</dt><dd>${formatAnswer(engagement.intakeAnswers[question.id])}</dd></div>`)
          .join('')}
      </dl>
    </details>
    <div class="task-groups"></div>
  `;

  const taskGroups = article.querySelector('.task-groups');
  groupTasksByCategory(engagement.tasks).forEach(({ category, tasks }) => {
    const section = document.createElement('section');
    section.className = 'task-category';
    section.innerHTML = `
      <div class="category-heading"><h4>${escapeHtml(category)}</h4><span>${tasks.length} task${tasks.length === 1 ? '' : 's'}</span></div>
      <ol class="task-list"></ol>
    `;
    const taskList = section.querySelector('.task-list');
    tasks.forEach((task) => {
      const item = document.createElement('li');
      item.className = task.completed ? 'task-item is-complete' : 'task-item';
      item.dataset.taskId = task.id;
      item.innerHTML = `
        <div class="task-main">
          <label class="task-check">
            <input type="checkbox" ${task.completed ? 'checked' : ''} data-action="toggle-task" />
            <span>${escapeHtml(task.title)}</span>
          </label>
          <div class="task-meta">
            <span class="audience-badge audience-${escapeHtml(task.audience)}">${escapeHtml(task.audienceLabel)}</span>
            ${task.relationshipGenerated ? '<span class="audience-badge">Relationship-generated</span>' : ''}
            <time datetime="${task.suggestedDate}">${formatDate(task.suggestedDate)}</time>
          </div>
        </div>
        ${task.clientRequestText ? `<p class="description">Client request: ${escapeHtml(task.clientRequestText)}</p>` : ''}
        ${task.internalInstructions ? `<p class="description">Internal: ${escapeHtml(task.internalInstructions)}</p>` : ''}
        <label class="notes-label">Notes<textarea data-action="update-notes" rows="2">${escapeHtml(task.notes)}</textarea></label>
      `;
      taskList.append(item);
    });
    taskGroups.append(section);
  });

  return article;
}

function getFormAnswers(formData, workflowKey, prefix = 'question') {
  return getWorkflowQuestions(workflowKey).reduce((answers, question) => {
    answers[question.id] = formData.get(`${prefix}:${question.id}`) ?? '';
    return answers;
  }, {});
}

function linkedContext(clientId, selectedIds = []) {
  const relationships = getRelationshipsForClient(state.relationships, clientId).filter((relationship) =>
    selectedIds.includes(relationship.fromClientId === clientId ? relationship.toClientId : relationship.fromClientId)
  );
  const linkedClients = state.clients.filter((client) => selectedIds.includes(client.id));
  return { relationships, linkedClients };
}

function buildEngagementFromForm(form) {
  const client = selectedClient();
  const formData = new FormData(form);
  const workflowKey = formData.get('workflowKey');
  const relatedClientIds = formData.getAll('relatedClientIds');
  const { relationships, linkedClients } = linkedContext(client.id, relatedClientIds);
  const engagement = buildEngagementForClient({
    client,
    workflowKey,
    taxYear: formData.get('taxYear'),
    periodEnd: formData.get('periodEnd'),
    dueDate: formData.get('dueDate'),
    relatedClientIds,
    intakeAnswers: getFormAnswers(formData, workflowKey),
    relationships,
    linkedClients,
    existingEngagements: state.engagements
  });

  return {
    ...engagement,
    clientName: client.displayName,
    linkedClients
  };
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

function findEngagementFromEvent(event) {
  const card = event.target.closest('.checklist-card');
  return state.engagements.find((engagement) => engagement.id === card?.dataset.engagementId);
}

function handleSubmit(event) {
  const action = event.target.dataset.action;

  if (!action) {
    return;
  }

  event.preventDefault();
  const formData = new FormData(event.target);

  if (action === 'create-person') {
    const client = createPersonClient({
      firstName: formData.get('firstName'),
      lastName: formData.get('lastName'),
      email: formData.get('email'),
      phone: formData.get('phone'),
      notes: formData.get('notes')
    });
    state.clients = [client, ...state.clients];
    selectedClientId = client.id;
  }

  if (action === 'create-business') {
    const client = createBusinessClient({
      legalName: formData.get('legalName'),
      dbaName: formData.get('dbaName'),
      entityType: formData.get('entityType'),
      taxTreatment: formData.get('taxTreatment'),
      einLast4: formData.get('einLast4'),
      email: formData.get('email'),
      phone: formData.get('phone'),
      notes: formData.get('notes')
    });
    state.clients = [client, ...state.clients];
    selectedClientId = client.id;
  }

  if (action === 'create-relationship') {
    state.relationships = [
      createRelationship({
        fromClientId: selectedClientId,
        toClientId: formData.get('toClientId'),
        relationshipType: formData.get('relationshipType'),
        ownershipPercent: formData.get('ownershipPercent'),
        isPrimary: formData.get('isPrimary') === 'on',
        notes: formData.get('notes')
      }),
      ...state.relationships
    ];
  }

  if (action === 'create-linked-client') {
    const displayName = formData.get('displayName');
    const linkedClient =
      formData.get('clientType') === 'business'
        ? createBusinessClient({ legalName: displayName })
        : createPersonClient({ firstName: displayName, lastName: 'Client' });
    state.clients = [linkedClient, ...state.clients];
    state.relationships = [
      createRelationship({
        fromClientId: selectedClientId,
        toClientId: linkedClient.id,
        relationshipType: formData.get('relationshipType')
      }),
      ...state.relationships
    ];
  }

  if (action === 'create-engagement') {
    state.engagements = [buildEngagementFromForm(event.target), ...state.engagements];
  }

  saveState();
  event.target.reset();
  render();
}

async function handleClick(event) {
  const action = event.target.dataset.action;

  if (!action) {
    return;
  }

  if (action === 'filter-clients') {
    clientFilter = event.target.dataset.filter;
    render();
    return;
  }

  if (action === 'select-client') {
    selectedClientId = event.target.closest('[data-client-id]').dataset.clientId;
    render();
    return;
  }

  if (action === 'delete-relationship') {
    state.relationships = state.relationships.filter((relationship) => relationship.id !== event.target.dataset.relationshipId);
    saveState();
    render();
    return;
  }

  const engagement = findEngagementFromEvent(event);

  if (!engagement) {
    return;
  }

  if (action === 'delete-engagement') {
    state.engagements = state.engagements.filter((savedEngagement) => savedEngagement.id !== engagement.id);
  }

  if (action === 'duplicate-engagement') {
    state.engagements = [
      {
        ...engagement,
        id: createId('engagement'),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        tasks: engagement.tasks.map((task) => ({ ...task, id: createId(`${engagement.workflowKey}-duplicate`) }))
      },
      ...state.engagements
    ];
  }

  if (action === 'copy-client-email') {
    await copyTextToClipboard(generateClientRequestEmail(engagement));
    event.target.textContent = 'Copied';
    window.setTimeout(() => {
      event.target.textContent = 'Copy client request email';
    }, 1200);
    return;
  }

  if (action === 'print-client-list') {
    printHtmlDocument(generateClientRequestPrintHtml(engagement));
    return;
  }

  if (action === 'print-internal-checklist') {
    printHtmlDocument(generateInternalChecklistPrintHtml(engagement));
    return;
  }

  saveState();
  render();
}

function handleChange(event) {
  const action = event.target.dataset.action;

  if (action === 'change-builder-workflow') {
    const questionContainer = document.querySelector('#builder-questions');
    questionContainer.innerHTML = renderQuestionFields(getWorkflowQuestions(event.target.value));
    return;
  }

  if (action !== 'toggle-task') {
    return;
  }

  const engagement = findEngagementFromEvent(event);
  const task = engagement.tasks.find((savedTask) => savedTask.id === event.target.closest('.task-item').dataset.taskId);
  task.completed = event.target.checked;
  engagement.updatedAt = new Date().toISOString();
  saveState();
  render();
}

function handleInput(event) {
  if (event.target.dataset.action !== 'update-notes') {
    return;
  }

  const engagement = findEngagementFromEvent(event);
  const task = engagement.tasks.find((savedTask) => savedTask.id === event.target.closest('.task-item').dataset.taskId);
  task.notes = event.target.value;
  engagement.updatedAt = new Date().toISOString();
  saveState();
}

function clearAllData() {
  const confirmed = window.confirm('Delete all saved clients, relationships, and engagements from this browser?');

  if (!confirmed) {
    return;
  }

  state = { clients: [], relationships: [], engagements: [] };
  selectedClientId = '';
  saveState();
  render();
}

clientIndex.addEventListener('submit', handleSubmit);
clientIndex.addEventListener('click', handleClick);
clientDetail.addEventListener('submit', handleSubmit);
clientDetail.addEventListener('click', handleClick);
engagementBuilder.addEventListener('submit', handleSubmit);
engagementBuilder.addEventListener('change', handleChange);
engagementList.addEventListener('click', handleClick);
engagementList.addEventListener('change', handleChange);
engagementList.addEventListener('input', handleInput);
clearAllButton.addEventListener('click', clearAllData);

render();

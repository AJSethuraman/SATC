import { getWorkflowQuestions } from './workflows.js';

export function getClientFacingTasks(tasks = []) {
  return tasks.filter((task) => task.audience === 'client');
}

export function groupTasksByCategory(tasks = []) {
  const groups = [];
  const groupIndexes = new Map();

  tasks.forEach((task) => {
    const category = task.category || 'General';

    if (!groupIndexes.has(category)) {
      groupIndexes.set(category, groups.length);
      groups.push({ category, tasks: [] });
    }

    groups[groupIndexes.get(category)].tasks.push(task);
  });

  return groups;
}

export function formatOutputDate(dateValue) {
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC'
  }).format(new Date(`${dateValue}T12:00:00Z`));
}

export function formatAnswer(value) {
  if (value === 'yes') {
    return 'Yes';
  }

  if (value === 'no') {
    return 'No';
  }

  return 'No answer';
}

export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

export function generateClientRequestEmail(checklist) {
  const clientTasks = getClientFacingTasks(checklist.tasks);
  const groupedTasks = groupTasksByCategory(clientTasks);
  const dueDate = formatOutputDate(checklist.dueDate);
  const lines = [
    `Subject: Requested items for ${checklist.clientName} - ${checklist.workflowName}`,
    '',
    `Hello ${checklist.clientName},`,
    '',
    `I hope you are well. SAT-C LLP is preparing your ${checklist.workflowName} checklist due ${dueDate}. Please provide or review the following client-facing items when convenient.`,
    ''
  ];

  if (!groupedTasks.length) {
    lines.push('There are no client-facing requests for this checklist right now.', '');
  }

  groupedTasks.forEach(({ category, tasks }) => {
    lines.push(category);
    tasks.forEach((task) => {
      lines.push(`- ${task.clientRequestText || task.title} (suggested by ${formatOutputDate(task.suggestedDate)})`);
    });
    lines.push('');
  });

  lines.push(
    'If you have questions about any item, please reply here and we will be happy to help.',
    '',
    'Thank you,',
    'SAT-C LLP'
  );

  return lines.join('\n');
}

function renderTaskList(tasks, { includeInternalDetails = false } = {}) {
  return groupTasksByCategory(tasks)
    .map(
      ({ category, tasks: categoryTasks }) => `
        <section class="print-category">
          <h2>${escapeHtml(category)}</h2>
          <ol>
            ${categoryTasks
              .map(
                (task) => `
                  <li>
                    <div class="task-title">${escapeHtml(includeInternalDetails ? task.title : task.clientRequestText || task.title)}</div>
                    <div class="task-details">
                      <span>Suggested: ${formatOutputDate(task.suggestedDate)}</span>
                      ${
                        includeInternalDetails
                          ? `<span>Audience: ${escapeHtml(task.audienceLabel)}</span><span>Status: ${
                              task.completed ? 'Complete' : 'Open'
                            }</span>`
                          : ''
                      }
                    </div>
                    ${includeInternalDetails && task.internalInstructions ? `<p class="notes">Internal instructions: ${escapeHtml(task.internalInstructions)}</p>` : ''}
                    ${includeInternalDetails && task.notes ? `<p class="notes">Notes: ${escapeHtml(task.notes)}</p>` : ''}
                  </li>
                `
              )
              .join('')}
          </ol>
        </section>
      `
    )
    .join('');
}

function renderRiskFlags(checklist) {
  const flags = checklist.riskFlags ?? [];

  if (!flags.length) {
    return '<p>No risk flags generated.</p>';
  }

  return `<ul>${flags.map((flag) => `<li>${escapeHtml(flag)}</li>`).join('')}</ul>`;
}

function renderLinkedClients(checklist) {
  const linkedClients = checklist.linkedClients ?? [];

  if (!linkedClients.length) {
    return '<p>No linked clients included.</p>';
  }

  return `<ul>${linkedClients.map((client) => `<li>${escapeHtml(client.displayName)} (${escapeHtml(client.clientType)})</li>`).join('')}</ul>`;
}

function renderIntakeAnswers(checklist) {
  const answers = checklist.intakeAnswers ?? {};
  const questions = getWorkflowQuestions(checklist.workflowKey);

  if (!questions.length) {
    return '<p>No intake questions for this workflow.</p>';
  }

  return `
    <dl class="intake-list">
      ${questions
        .map(
          (question) => `
            <div>
              <dt>${escapeHtml(question.label)}</dt>
              <dd>${formatAnswer(answers[question.id])}</dd>
            </div>
          `
        )
        .join('')}
    </dl>
  `;
}

function buildPrintDocument({ title, intro, body }) {
  return `<!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <title>${escapeHtml(title)}</title>
        <style>
          body { color: #1f2933; font-family: Arial, sans-serif; line-height: 1.5; margin: 32px; }
          h1 { margin-bottom: 4px; }
          h2 { border-bottom: 1px solid #cfd8e3; font-size: 1.05rem; margin-top: 28px; padding-bottom: 6px; }
          ol { padding-left: 24px; }
          li { margin-bottom: 14px; }
          .meta, .task-details, .notes { color: #536574; font-size: 0.92rem; }
          .task-details { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 3px; }
          .task-title { font-weight: 700; }
          .intake-list { display: grid; gap: 8px; }
          .intake-list div { border-bottom: 1px solid #e3e9ef; padding-bottom: 8px; }
          .intake-list dt { color: #536574; font-weight: 700; }
          .intake-list dd { margin: 2px 0 0; }
          @media print { body { margin: 20mm; } button { display: none; } }
        </style>
      </head>
      <body>
        <h1>${escapeHtml(title)}</h1>
        <p class="meta">${escapeHtml(intro)}</p>
        ${body}
      </body>
    </html>`;
}

export function generateClientRequestPrintHtml(checklist) {
  const title = `Client request list - ${checklist.clientName}`;
  const intro = `${checklist.workflowName} • Due ${formatOutputDate(checklist.dueDate)} • SAT-C LLP`;
  const tasks = getClientFacingTasks(checklist.tasks);
  const body = tasks.length
    ? renderTaskList(tasks)
    : '<p>There are no client-facing requests for this checklist right now.</p>';

  return buildPrintDocument({ title, intro, body });
}

export function generateInternalChecklistPrintHtml(checklist) {
  const title = `Internal checklist - ${checklist.clientName}`;
  const intro = `${checklist.workflowName} • Due ${formatOutputDate(checklist.dueDate)}`;
  const body = `
    <section>
      <h2>Risk flags</h2>
      ${renderRiskFlags(checklist)}
    </section>
    <section>
      <h2>Linked clients</h2>
      ${renderLinkedClients(checklist)}
    </section>
    <section>
      <h2>Intake answers</h2>
      ${renderIntakeAnswers(checklist)}
    </section>
    <section>
      <h2>Tasks</h2>
      ${renderTaskList(checklist.tasks, { includeInternalDetails: true })}
    </section>
  `;

  return buildPrintDocument({ title, intro, body });
}

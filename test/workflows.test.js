import test from 'node:test';
import assert from 'node:assert/strict';
import { generateClientRequestEmail, getClientFacingTasks, groupTasksByCategory } from '../src/outputs.js';
import { buildChecklist, calculateSuggestedDate, getWorkflowQuestions, regenerateChecklist, workflows } from '../src/workflows.js';

const matchingAnswers = {
  newTaxClientOnboarding: {
    hasPriorYearReturns: 'yes',
    hasIrsNotices: 'yes',
    multiStateFiling: 'yes',
    businessOwner: 'yes',
    needsBookkeepingSetup: 'yes'
  },
  monthlyBookkeeping: {
    usesPayroll: 'yes',
    hasLoanActivity: 'yes',
    inventoryActivity: 'yes',
    salesTaxFilingDue: 'yes',
    unclearedTransactions: 'yes'
  },
  yearEndCleanup: {
    newFixedAssets: 'yes',
    hasPayroll: 'yes',
    needs1099Review: 'yes',
    ownerContributions: 'yes',
    openSuspenseItems: 'yes'
  },
  rentalPropertyTaxPrep: {
    purchasedThisYear: 'yes',
    soldThisYear: 'yes',
    majorImprovements: 'yes',
    personalUseDays: 'yes',
    shortTermRentalActivity: 'yes',
    outOfStateProperty: 'yes',
    propertyManager: 'yes',
    refinanceOrNewMortgage: 'yes',
    casualtyLossOrInsuranceClaim: 'yes'
  }
};

const conditionalTaskTitles = {
  newTaxClientOnboarding: [
    'Request prior-year tax returns and carryforward details',
    'Request copies of IRS or state notices and response deadlines',
    'Map resident and nonresident state filing requirements',
    'Request entity documents, ownership details, and accounting access',
    'Create bookkeeping setup plan and chart-of-accounts checklist'
  ],
  monthlyBookkeeping: [
    'Request payroll reports and tie wages to payroll tax liabilities',
    'Review loan statements, interest, principal, and new financing entries',
    'Request inventory count or valuation report',
    'Prepare sales tax reconciliation and filing support',
    'Send transaction question list to client'
  ],
  yearEndCleanup: [
    'Request asset purchase invoices and disposal documentation',
    'Update fixed asset register and depreciation entries',
    'Request annual payroll reports and reconcile wages to payroll tax filings',
    'Request W-9s and confirm 1099 vendor payment totals',
    'Reconcile owner contributions, draws, and equity rollforward',
    'Send suspense item question list to client'
  ],
  rentalPropertyTaxPrep: [
    'Collect closing statement and purchase allocation details',
    'Collect sale closing statement and calculate rental property disposition details',
    'Request invoices and placed-in-service dates for major improvements',
    'Document personal-use days and allocate mixed-use expenses',
    'Review short-term rental days, services provided, and occupancy tax details',
    'Confirm nonresident state filing requirements for out-of-state property',
    'Request property manager annual statement and fee detail',
    'Collect refinance or new mortgage closing costs and loan terms',
    'Gather casualty loss records, insurance claim documents, and reimbursements'
  ]
};

function baseTaskCount(workflowKey) {
  return workflows[workflowKey].tasks.filter((task) => !task.condition).length;
}

function noAnswers(workflowKey) {
  return Object.fromEntries(getWorkflowQuestions(workflowKey).map((question) => [question.id, 'no']));
}

test('includes the required workflow templates', () => {
  assert.deepEqual(Object.keys(workflows), [
    'newTaxClientOnboarding',
    'monthlyBookkeeping',
    'yearEndCleanup',
    'rentalPropertyTaxPrep'
  ]);
});

test('calculates suggested dates before the due date', () => {
  assert.equal(calculateSuggestedDate('2026-04-15', 10), '2026-04-05');
});

test('builds checklist tasks from a selected workflow with category and audience metadata', () => {
  const checklist = buildChecklist({
    clientName: '  Acme LLC  ',
    dueDate: '2026-04-15',
    workflowKey: 'monthlyBookkeeping'
  });

  assert.equal(checklist.clientName, 'Acme LLC');
  assert.equal(checklist.workflowName, 'Monthly bookkeeping');
  assert.equal(checklist.tasks.length, baseTaskCount('monthlyBookkeeping'));
  assert.equal(checklist.tasks.at(-1).suggestedDate, '2026-04-15');
  assert.equal(checklist.tasks.every((task) => task.completed === false), true);
  assert.equal(checklist.tasks.every((task) => task.category && task.audience && task.audienceLabel), true);
});

test('all workflows expose optional intake questions', () => {
  Object.keys(workflows).forEach((workflowKey) => {
    assert.ok(getWorkflowQuestions(workflowKey).length > 0, `${workflowKey} should define intake questions`);
  });
});

test('all workflow templates include task categories and audience flags', () => {
  Object.entries(workflows).forEach(([workflowKey, workflow]) => {
    workflow.tasks.forEach((task) => {
      assert.ok(task.category, `${workflowKey} task should define a category: ${task.title}`);
      assert.match(task.audience, /^(internal|client)$/, `${workflowKey} task should define an audience: ${task.title}`);
    });
  });
});

test('every workflow task has a unique stable templateId', () => {
  const allTemplateIds = [];

  Object.entries(workflows).forEach(([workflowKey, workflow]) => {
    workflow.tasks.forEach((task) => {
      assert.ok(task.templateId, `${workflowKey} task should define a templateId: ${task.title}`);
      assert.match(task.templateId, /^[a-z0-9]+(?:-[a-z0-9]+)*$/);
      allTemplateIds.push(task.templateId);
    });
  });

  assert.equal(new Set(allTemplateIds).size, allTemplateIds.length);
});

test('generated checklist tasks include generated id and stable templateId', () => {
  const checklist = buildChecklist({
    clientName: 'Acme LLC',
    dueDate: '2026-04-15',
    workflowKey: 'monthlyBookkeeping',
    answers: matchingAnswers.monthlyBookkeeping
  });

  assert.equal(
    checklist.tasks.every((task) => task.id && task.templateId),
    true
  );
  assert.equal(checklist.tasks.some((task) => task.templateId === 'monthly-request-bank-statements'), true);
});

Object.keys(workflows).forEach((workflowKey) => {
  test(`omits conditional tasks when ${workflowKey} intake answers do not match`, () => {
    const checklist = buildChecklist({
      clientName: 'Example Client',
      dueDate: '2026-04-15',
      workflowKey,
      answers: noAnswers(workflowKey)
    });

    assert.equal(checklist.tasks.length, baseTaskCount(workflowKey));
    assert.equal(
      conditionalTaskTitles[workflowKey].every((title) => !checklist.tasks.some((task) => task.title === title)),
      true
    );
  });

  test(`adds matching conditional tasks and saves intake answers for ${workflowKey}`, () => {
    const checklist = buildChecklist({
      clientName: 'Example Client',
      dueDate: '2026-04-15',
      workflowKey,
      answers: matchingAnswers[workflowKey]
    });

    assert.equal(checklist.tasks.length, workflows[workflowKey].tasks.length);
    assert.deepEqual(checklist.intakeAnswers, matchingAnswers[workflowKey]);
    assert.equal(
      conditionalTaskTitles[workflowKey].every((title) => checklist.tasks.some((task) => task.title === title)),
      true
    );
  });
});


test('filters client-facing tasks for output', () => {
  const checklist = buildChecklist({
    clientName: 'Example Client',
    dueDate: '2026-04-15',
    workflowKey: 'monthlyBookkeeping',
    answers: matchingAnswers.monthlyBookkeeping
  });
  const clientTasks = getClientFacingTasks(checklist.tasks);

  assert.ok(clientTasks.length > 0);
  assert.equal(clientTasks.every((task) => task.audience === 'client'), true);
  assert.equal(clientTasks.some((task) => task.title === 'Import transactions and refresh bank feeds'), false);
  assert.equal(clientTasks.some((task) => task.title === 'Send transaction question list to client'), true);
});

test('generates client request email text with only client-facing grouped requests', () => {
  const checklist = buildChecklist({
    clientName: 'Acme LLC',
    dueDate: '2026-04-15',
    workflowKey: 'monthlyBookkeeping',
    answers: matchingAnswers.monthlyBookkeeping
  });
  const email = generateClientRequestEmail(checklist);

  assert.match(email, /Subject: Requested items for Acme LLC - Monthly bookkeeping/);
  assert.match(email, /Hello Acme LLC,/);
  assert.match(email, /SAT-C LLP is preparing your Monthly bookkeeping checklist due Apr 15, 2026/);
  assert.match(email, /Document requests\n- Request bank, credit card, and loan statements/);
  assert.match(email, /Client follow-up\n- Send transaction question list to client/);
  assert.doesNotMatch(email, /Import transactions and refresh bank feeds/);
  assert.match(email, /Thank you,\nSAT-C LLP/);
});

test('groups tasks by category for output', () => {
  const groupedTasks = groupTasksByCategory([
    { title: 'First request', category: 'Document requests', audience: 'client' },
    { title: 'Internal review', category: 'Review', audience: 'internal' },
    { title: 'Second request', category: 'Document requests', audience: 'client' }
  ]);

  assert.deepEqual(
    groupedTasks.map((group) => ({ category: group.category, titles: group.tasks.map((task) => task.title) })),
    [
      { category: 'Document requests', titles: ['First request', 'Second request'] },
      { category: 'Review', titles: ['Internal review'] }
    ]
  );
});


test('regenerates a checklist while preserving matching task notes and completion status by templateId', () => {
  const checklist = buildChecklist({
    clientName: 'Acme LLC',
    dueDate: '2026-04-15',
    workflowKey: 'monthlyBookkeeping',
    answers: {
      usesPayroll: 'yes',
      hasLoanActivity: 'yes',
      inventoryActivity: 'no',
      salesTaxFilingDue: 'no',
      unclearedTransactions: 'no'
    }
  });

  const baseRequest = checklist.tasks.find((task) => task.title === 'Request bank, credit card, and loan statements');
  baseRequest.completed = true;
  baseRequest.notes = 'Client uploaded March statements.';

  const payrollRequest = checklist.tasks.find(
    (task) => task.title === 'Request payroll reports and tie wages to payroll tax liabilities'
  );
  payrollRequest.completed = true;
  payrollRequest.notes = 'Payroll report is in the portal.';

  const updatedChecklist = regenerateChecklist(checklist, {
    clientName: 'Acme LLC Updated',
    dueDate: '2026-04-30',
    answers: {
      usesPayroll: 'yes',
      hasLoanActivity: 'no',
      inventoryActivity: 'yes',
      salesTaxFilingDue: 'no',
      unclearedTransactions: 'no'
    }
  });

  const preservedBaseRequest = updatedChecklist.tasks.find(
    (task) => task.title === 'Request bank, credit card, and loan statements'
  );
  const preservedPayrollRequest = updatedChecklist.tasks.find(
    (task) => task.title === 'Request payroll reports and tie wages to payroll tax liabilities'
  );
  const removedLoanTask = updatedChecklist.tasks.find(
    (task) => task.title === 'Review loan statements, interest, principal, and new financing entries'
  );
  const newInventoryTask = updatedChecklist.tasks.find((task) => task.title === 'Request inventory count or valuation report');

  assert.equal(updatedChecklist.clientName, 'Acme LLC Updated');
  assert.equal(updatedChecklist.dueDate, '2026-04-30');
  assert.equal(preservedBaseRequest.completed, true);
  assert.equal(preservedBaseRequest.notes, 'Client uploaded March statements.');
  assert.equal(preservedPayrollRequest.completed, true);
  assert.equal(preservedPayrollRequest.notes, 'Payroll report is in the portal.');
  assert.equal(removedLoanTask, undefined);
  assert.equal(newInventoryTask.completed, false);
  assert.equal(newInventoryTask.notes, '');
});


test('regeneration preserves task data when title changes but templateId remains the same', () => {
  const taskTemplate = workflows.monthlyBookkeeping.tasks.find(
    (task) => task.templateId === 'monthly-request-bank-statements'
  );
  const originalTitle = taskTemplate.title;

  try {
    const checklist = buildChecklist({
      clientName: 'Acme LLC',
      dueDate: '2026-04-15',
      workflowKey: 'monthlyBookkeeping',
      answers: matchingAnswers.monthlyBookkeeping
    });
    const trackedTask = checklist.tasks.find((task) => task.templateId === 'monthly-request-bank-statements');
    trackedTask.completed = true;
    trackedTask.notes = 'Preserve these notes even if wording changes.';

    taskTemplate.title = 'Request operating account, credit card, and loan statements';

    const updatedChecklist = regenerateChecklist(checklist, {
      clientName: 'Acme LLC',
      dueDate: '2026-04-30',
      answers: matchingAnswers.monthlyBookkeeping
    });
    const updatedTask = updatedChecklist.tasks.find((task) => task.templateId === 'monthly-request-bank-statements');

    assert.equal(updatedTask.title, 'Request operating account, credit card, and loan statements');
    assert.equal(updatedTask.completed, true);
    assert.equal(updatedTask.notes, 'Preserve these notes even if wording changes.');
  } finally {
    taskTemplate.title = originalTitle;
  }
});

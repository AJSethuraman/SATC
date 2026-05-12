export const workflows = {
  newTaxClientOnboarding: {
    name: 'New tax client onboarding',
    description: 'Collect authorization, prior-year details, entity information, and engagement documents.',
    questions: [],
    tasks: [
      { title: 'Send welcome email and secure portal invitation', daysBeforeDue: 21 },
      { title: 'Request signed engagement letter', daysBeforeDue: 20 },
      { title: 'Collect prior-year tax returns and notices', daysBeforeDue: 18 },
      { title: 'Gather client intake questionnaire and contact details', daysBeforeDue: 16 },
      { title: 'Confirm filing status, dependents, entities, and state obligations', daysBeforeDue: 14 },
      { title: 'Set up client folder and document checklist', daysBeforeDue: 12 },
      { title: 'Schedule kickoff or discovery call', daysBeforeDue: 10 },
      { title: 'Review open questions and assign next steps', daysBeforeDue: 7 }
    ]
  },
  monthlyBookkeeping: {
    name: 'Monthly bookkeeping',
    description: 'Close the month with reconciliations, reviews, reports, and client follow-up.',
    questions: [],
    tasks: [
      { title: 'Request bank, credit card, payroll, and loan statements', daysBeforeDue: 10 },
      { title: 'Import transactions and refresh bank feeds', daysBeforeDue: 9 },
      { title: 'Categorize income and expenses', daysBeforeDue: 7 },
      { title: 'Reconcile bank and credit card accounts', daysBeforeDue: 5 },
      { title: 'Review accounts receivable and accounts payable', daysBeforeDue: 4 },
      { title: 'Post depreciation, accruals, and recurring journal entries', daysBeforeDue: 3 },
      { title: 'Prepare financial statements and management notes', daysBeforeDue: 2 },
      { title: 'Send monthly close package to client', daysBeforeDue: 0 }
    ]
  },
  yearEndCleanup: {
    name: 'Year-end cleanup',
    description: 'Prepare books for tax-ready year-end review and reporting.',
    questions: [],
    tasks: [
      { title: 'Lock prior reviewed periods and backup accounting file', daysBeforeDue: 30 },
      { title: 'Reconcile all cash, credit card, and loan accounts', daysBeforeDue: 25 },
      { title: 'Review uncategorized, suspense, and owner draw accounts', daysBeforeDue: 20 },
      { title: 'Confirm fixed assets, disposals, and depreciation entries', daysBeforeDue: 16 },
      { title: 'Tie payroll reports to wage and tax expense accounts', daysBeforeDue: 12 },
      { title: 'Review 1099 vendor list and W-9 gaps', daysBeforeDue: 10 },
      { title: 'Prepare adjusting journal entries', daysBeforeDue: 7 },
      { title: 'Deliver tax-ready trial balance and cleanup notes', daysBeforeDue: 0 }
    ]
  },
  rentalPropertyTaxPrep: {
    name: 'Rental property tax prep',
    description: 'Collect rental income, expense, asset, and ownership details for tax preparation.',
    questions: [
      { id: 'purchasedThisYear', label: 'Was the property purchased this year?', type: 'yesNo' },
      { id: 'soldThisYear', label: 'Was the property sold this year?', type: 'yesNo' },
      { id: 'majorImprovements', label: 'Were there major improvements?', type: 'yesNo' },
      { id: 'personalUseDays', label: 'Were there personal-use days?', type: 'yesNo' },
      { id: 'shortTermRentalActivity', label: 'Was there short-term rental activity?', type: 'yesNo' },
      { id: 'outOfStateProperty', label: 'Is the property out of state?', type: 'yesNo' },
      { id: 'propertyManager', label: 'Was a property manager used?', type: 'yesNo' },
      { id: 'refinanceOrNewMortgage', label: 'Was there a refinance or new mortgage?', type: 'yesNo' },
      { id: 'casualtyLossOrInsuranceClaim', label: 'Was there a casualty loss or insurance claim?', type: 'yesNo' }
    ],
    tasks: [
      { title: 'Request rent roll and annual income summary', daysBeforeDue: 18 },
      { title: 'Collect mortgage interest and property tax statements', daysBeforeDue: 16 },
      { title: 'Gather repair, maintenance, utility, and insurance expenses', daysBeforeDue: 14 },
      { title: 'Identify improvements versus repairs', daysBeforeDue: 12 },
      { title: 'Confirm personal-use days and rental-use days', daysBeforeDue: 10 },
      { title: 'Review mileage, travel, and management fees', daysBeforeDue: 8 },
      { title: 'Update depreciation schedule for new assets or disposals', daysBeforeDue: 5 },
      { title: 'Prepare rental property tax summary for review', daysBeforeDue: 0 },
      {
        title: 'Collect closing statement and purchase allocation details',
        daysBeforeDue: 15,
        condition: { questionId: 'purchasedThisYear', equals: 'yes' }
      },
      {
        title: 'Collect sale closing statement and calculate rental property disposition details',
        daysBeforeDue: 15,
        condition: { questionId: 'soldThisYear', equals: 'yes' }
      },
      {
        title: 'Request invoices and placed-in-service dates for major improvements',
        daysBeforeDue: 13,
        condition: { questionId: 'majorImprovements', equals: 'yes' }
      },
      {
        title: 'Document personal-use days and allocate mixed-use expenses',
        daysBeforeDue: 9,
        condition: { questionId: 'personalUseDays', equals: 'yes' }
      },
      {
        title: 'Review short-term rental days, services provided, and occupancy tax details',
        daysBeforeDue: 9,
        condition: { questionId: 'shortTermRentalActivity', equals: 'yes' }
      },
      {
        title: 'Confirm nonresident state filing requirements for out-of-state property',
        daysBeforeDue: 8,
        condition: { questionId: 'outOfStateProperty', equals: 'yes' }
      },
      {
        title: 'Request property manager annual statement and fee detail',
        daysBeforeDue: 7,
        condition: { questionId: 'propertyManager', equals: 'yes' }
      },
      {
        title: 'Collect refinance or new mortgage closing costs and loan terms',
        daysBeforeDue: 6,
        condition: { questionId: 'refinanceOrNewMortgage', equals: 'yes' }
      },
      {
        title: 'Gather casualty loss records, insurance claim documents, and reimbursements',
        daysBeforeDue: 6,
        condition: { questionId: 'casualtyLossOrInsuranceClaim', equals: 'yes' }
      }
    ]
  }
};

export function calculateSuggestedDate(dueDateValue, daysBeforeDue) {
  const dueDate = new Date(`${dueDateValue}T12:00:00`);

  if (Number.isNaN(dueDate.getTime())) {
    throw new Error('A valid due date is required.');
  }

  const suggestedDate = new Date(dueDate);
  suggestedDate.setDate(suggestedDate.getDate() - daysBeforeDue);
  return suggestedDate.toISOString().slice(0, 10);
}

export function shouldIncludeTask(task, answers = {}) {
  if (!task.condition) {
    return true;
  }

  return answers[task.condition.questionId] === task.condition.equals;
}

export function getWorkflowQuestions(workflowKey) {
  return workflows[workflowKey]?.questions ?? [];
}

export function buildChecklist({ clientName, dueDate, workflowKey, answers = {} }) {
  const workflow = workflows[workflowKey];

  if (!workflow) {
    throw new Error('A valid workflow is required.');
  }

  const cleanClientName = clientName.trim();

  if (!cleanClientName) {
    throw new Error('Client name is required.');
  }

  const workflowQuestions = workflow.questions ?? [];
  const intakeAnswers = workflowQuestions.reduce((savedAnswers, question) => {
    savedAnswers[question.id] = answers[question.id] ?? '';
    return savedAnswers;
  }, {});

  return {
    id: crypto.randomUUID(),
    clientName: cleanClientName,
    dueDate,
    workflowKey,
    workflowName: workflow.name,
    intakeAnswers,
    createdAt: new Date().toISOString(),
    tasks: workflow.tasks.filter((task) => shouldIncludeTask(task, intakeAnswers)).map((task, index) => ({
      id: `${workflowKey}-${index}-${crypto.randomUUID()}`,
      title: task.title,
      suggestedDate: calculateSuggestedDate(dueDate, task.daysBeforeDue),
      completed: false,
      notes: ''
    }))
  };
}

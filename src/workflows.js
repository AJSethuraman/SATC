export const TASK_AUDIENCES = {
  internal: 'Internal',
  client: 'Client-facing'
};

export const workflows = {
  newTaxClientOnboarding: {
    name: 'New tax client onboarding',
    description: 'Collect authorization, prior-year details, entity information, and engagement documents.',
    questions: [
      { id: 'hasPriorYearReturns', label: 'Does the client have prior-year tax returns to provide?', type: 'yesNo' },
      { id: 'hasIrsNotices', label: 'Does the client have IRS or state notices?', type: 'yesNo' },
      { id: 'multiStateFiling', label: 'Will the client need multi-state filing review?', type: 'yesNo' },
      { id: 'businessOwner', label: 'Does the client own a business or rental entity?', type: 'yesNo' },
      { id: 'needsBookkeepingSetup', label: 'Does the client need bookkeeping setup?', type: 'yesNo' }
    ],
    tasks: [
      { templateId: 'onboarding-send-welcome-email', title: 'Send welcome email and secure portal invitation', daysBeforeDue: 21, category: 'Kickoff', audience: 'client' },
      { templateId: 'onboarding-request-engagement-letter', title: 'Request signed engagement letter', daysBeforeDue: 20, category: 'Authorization', audience: 'client' },
      { templateId: 'onboarding-gather-intake-questionnaire', title: 'Gather client intake questionnaire and contact details', daysBeforeDue: 16, category: 'Client information', audience: 'client' },
      { templateId: 'onboarding-confirm-filing-details', title: 'Confirm filing status, dependents, entities, and state obligations', daysBeforeDue: 14, category: 'Review', audience: 'internal' },
      { templateId: 'onboarding-set-up-client-folder', title: 'Set up client folder and document checklist', daysBeforeDue: 12, category: 'Internal setup', audience: 'internal' },
      { templateId: 'onboarding-schedule-kickoff-call', title: 'Schedule kickoff or discovery call', daysBeforeDue: 10, category: 'Kickoff', audience: 'client' },
      { templateId: 'onboarding-review-open-questions', title: 'Review open questions and assign next steps', daysBeforeDue: 7, category: 'Review', audience: 'internal' },
      {
        templateId: 'onboarding-request-prior-year-returns',
        title: 'Request prior-year tax returns and carryforward details',
        daysBeforeDue: 18,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'hasPriorYearReturns', equals: 'yes' }
      },
      {
        templateId: 'onboarding-request-tax-notices',
        title: 'Request copies of IRS or state notices and response deadlines',
        daysBeforeDue: 17,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'hasIrsNotices', equals: 'yes' }
      },
      {
        templateId: 'onboarding-map-state-filing-requirements',
        title: 'Map resident and nonresident state filing requirements',
        daysBeforeDue: 13,
        category: 'Review',
        audience: 'internal',
        condition: { questionId: 'multiStateFiling', equals: 'yes' }
      },
      {
        templateId: 'onboarding-request-entity-documents',
        title: 'Request entity documents, ownership details, and accounting access',
        daysBeforeDue: 13,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'businessOwner', equals: 'yes' }
      },
      {
        templateId: 'onboarding-create-bookkeeping-setup-plan',
        title: 'Create bookkeeping setup plan and chart-of-accounts checklist',
        daysBeforeDue: 11,
        category: 'Internal setup',
        audience: 'internal',
        condition: { questionId: 'needsBookkeepingSetup', equals: 'yes' }
      }
    ]
  },
  monthlyBookkeeping: {
    name: 'Monthly bookkeeping',
    description: 'Close the month with reconciliations, reviews, reports, and client follow-up.',
    questions: [
      { id: 'usesPayroll', label: 'Did the client run payroll this month?', type: 'yesNo' },
      { id: 'hasLoanActivity', label: 'Was there loan or financing activity?', type: 'yesNo' },
      { id: 'inventoryActivity', label: 'Did inventory change materially?', type: 'yesNo' },
      { id: 'salesTaxFilingDue', label: 'Is a sales tax filing due?', type: 'yesNo' },
      { id: 'unclearedTransactions', label: 'Are there uncleared or uncategorized transactions?', type: 'yesNo' }
    ],
    tasks: [
      { templateId: 'monthly-request-bank-statements', title: 'Request bank, credit card, and loan statements', daysBeforeDue: 10, category: 'Document requests', audience: 'client' },
      { templateId: 'monthly-import-transactions', title: 'Import transactions and refresh bank feeds', daysBeforeDue: 9, category: 'Data entry', audience: 'internal' },
      { templateId: 'monthly-categorize-transactions', title: 'Categorize income and expenses', daysBeforeDue: 7, category: 'Data entry', audience: 'internal' },
      { templateId: 'monthly-reconcile-bank-credit-cards', title: 'Reconcile bank and credit card accounts', daysBeforeDue: 5, category: 'Reconciliation', audience: 'internal' },
      { templateId: 'monthly-review-ar-ap', title: 'Review accounts receivable and accounts payable', daysBeforeDue: 4, category: 'Review', audience: 'internal' },
      { templateId: 'monthly-post-adjusting-entries', title: 'Post depreciation, accruals, and recurring journal entries', daysBeforeDue: 3, category: 'Adjustments', audience: 'internal' },
      { templateId: 'monthly-prepare-financial-statements', title: 'Prepare financial statements and management notes', daysBeforeDue: 2, category: 'Reporting', audience: 'internal' },
      { templateId: 'monthly-send-close-package', title: 'Send monthly close package to client', daysBeforeDue: 0, category: 'Reporting', audience: 'client' },
      {
        templateId: 'monthly-request-payroll-reports',
        title: 'Request payroll reports and tie wages to payroll tax liabilities',
        daysBeforeDue: 6,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'usesPayroll', equals: 'yes' }
      },
      {
        templateId: 'monthly-review-loan-activity',
        title: 'Review loan statements, interest, principal, and new financing entries',
        daysBeforeDue: 5,
        category: 'Reconciliation',
        audience: 'internal',
        condition: { questionId: 'hasLoanActivity', equals: 'yes' }
      },
      {
        templateId: 'monthly-request-inventory-report',
        title: 'Request inventory count or valuation report',
        daysBeforeDue: 5,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'inventoryActivity', equals: 'yes' }
      },
      {
        templateId: 'monthly-prepare-sales-tax-support',
        title: 'Prepare sales tax reconciliation and filing support',
        daysBeforeDue: 3,
        category: 'Compliance',
        audience: 'internal',
        condition: { questionId: 'salesTaxFilingDue', equals: 'yes' }
      },
      {
        templateId: 'monthly-send-transaction-questions',
        title: 'Send transaction question list to client',
        daysBeforeDue: 4,
        category: 'Client follow-up',
        audience: 'client',
        condition: { questionId: 'unclearedTransactions', equals: 'yes' }
      }
    ]
  },
  yearEndCleanup: {
    name: 'Year-end cleanup',
    description: 'Prepare books for tax-ready year-end review and reporting.',
    questions: [
      { id: 'newFixedAssets', label: 'Were fixed assets purchased or disposed?', type: 'yesNo' },
      { id: 'hasPayroll', label: 'Did the client have payroll during the year?', type: 'yesNo' },
      { id: 'needs1099Review', label: 'Does the client need 1099 vendor review?', type: 'yesNo' },
      { id: 'ownerContributions', label: 'Were there owner contributions or distributions?', type: 'yesNo' },
      { id: 'openSuspenseItems', label: 'Are there suspense or uncategorized items?', type: 'yesNo' }
    ],
    tasks: [
      { templateId: 'year-end-lock-periods-backup-file', title: 'Lock prior reviewed periods and backup accounting file', daysBeforeDue: 30, category: 'Preparation', audience: 'internal' },
      { templateId: 'year-end-reconcile-cash-credit-loans', title: 'Reconcile all cash, credit card, and loan accounts', daysBeforeDue: 25, category: 'Reconciliation', audience: 'internal' },
      { templateId: 'year-end-review-suspense-accounts', title: 'Review uncategorized and suspense accounts', daysBeforeDue: 20, category: 'Cleanup', audience: 'internal' },
      { templateId: 'year-end-prepare-adjusting-entries', title: 'Prepare adjusting journal entries', daysBeforeDue: 7, category: 'Adjustments', audience: 'internal' },
      { templateId: 'year-end-deliver-tax-ready-trial-balance', title: 'Deliver tax-ready trial balance and cleanup notes', daysBeforeDue: 0, category: 'Reporting', audience: 'client' },
      {
        templateId: 'year-end-request-asset-documents',
        title: 'Request asset purchase invoices and disposal documentation',
        daysBeforeDue: 18,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'newFixedAssets', equals: 'yes' }
      },
      {
        templateId: 'year-end-update-fixed-assets',
        title: 'Update fixed asset register and depreciation entries',
        daysBeforeDue: 16,
        category: 'Adjustments',
        audience: 'internal',
        condition: { questionId: 'newFixedAssets', equals: 'yes' }
      },
      {
        templateId: 'year-end-request-annual-payroll-reports',
        title: 'Request annual payroll reports and reconcile wages to payroll tax filings',
        daysBeforeDue: 12,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'hasPayroll', equals: 'yes' }
      },
      {
        templateId: 'year-end-review-1099-vendor-list',
        title: 'Request W-9s and confirm 1099 vendor payment totals',
        daysBeforeDue: 10,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'needs1099Review', equals: 'yes' }
      },
      {
        templateId: 'year-end-reconcile-owner-equity',
        title: 'Reconcile owner contributions, draws, and equity rollforward',
        daysBeforeDue: 9,
        category: 'Review',
        audience: 'internal',
        condition: { questionId: 'ownerContributions', equals: 'yes' }
      },
      {
        templateId: 'year-end-send-suspense-questions',
        title: 'Send suspense item question list to client',
        daysBeforeDue: 8,
        category: 'Client follow-up',
        audience: 'client',
        condition: { questionId: 'openSuspenseItems', equals: 'yes' }
      }
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
      { templateId: 'rental-request-rent-roll', title: 'Request rent roll and annual income summary', daysBeforeDue: 18, category: 'Document requests', audience: 'client' },
      { templateId: 'rental-collect-mortgage-tax-statements', title: 'Collect mortgage interest and property tax statements', daysBeforeDue: 16, category: 'Document requests', audience: 'client' },
      { templateId: 'rental-gather-expense-documents', title: 'Gather repair, maintenance, utility, and insurance expenses', daysBeforeDue: 14, category: 'Document requests', audience: 'client' },
      { templateId: 'rental-identify-improvements-repairs', title: 'Identify improvements versus repairs', daysBeforeDue: 12, category: 'Review', audience: 'internal' },
      { templateId: 'rental-confirm-personal-use-days', title: 'Confirm personal-use days and rental-use days', daysBeforeDue: 10, category: 'Client follow-up', audience: 'client' },
      { templateId: 'rental-review-mileage-travel-management', title: 'Review mileage, travel, and management fees', daysBeforeDue: 8, category: 'Review', audience: 'internal' },
      { templateId: 'rental-update-depreciation-schedule', title: 'Update depreciation schedule for new assets or disposals', daysBeforeDue: 5, category: 'Adjustments', audience: 'internal' },
      { templateId: 'rental-prepare-tax-summary', title: 'Prepare rental property tax summary for review', daysBeforeDue: 0, category: 'Reporting', audience: 'internal' },
      {
        templateId: 'rental-collect-purchase-closing-statement',
        title: 'Collect closing statement and purchase allocation details',
        daysBeforeDue: 15,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'purchasedThisYear', equals: 'yes' }
      },
      {
        templateId: 'rental-collect-sale-closing-statement',
        title: 'Collect sale closing statement and calculate rental property disposition details',
        daysBeforeDue: 15,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'soldThisYear', equals: 'yes' }
      },
      {
        templateId: 'rental-request-improvement-invoices',
        title: 'Request invoices and placed-in-service dates for major improvements',
        daysBeforeDue: 13,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'majorImprovements', equals: 'yes' }
      },
      {
        templateId: 'rental-review-personal-use-days',
        title: 'Document personal-use days and allocate mixed-use expenses',
        daysBeforeDue: 9,
        category: 'Review',
        audience: 'internal',
        condition: { questionId: 'personalUseDays', equals: 'yes' }
      },
      {
        templateId: 'rental-review-short-term-rental-activity',
        title: 'Review short-term rental days, services provided, and occupancy tax details',
        daysBeforeDue: 9,
        category: 'Compliance',
        audience: 'internal',
        condition: { questionId: 'shortTermRentalActivity', equals: 'yes' }
      },
      {
        templateId: 'rental-confirm-out-of-state-filing',
        title: 'Confirm nonresident state filing requirements for out-of-state property',
        daysBeforeDue: 8,
        category: 'Compliance',
        audience: 'internal',
        condition: { questionId: 'outOfStateProperty', equals: 'yes' }
      },
      {
        templateId: 'rental-request-property-manager-statement',
        title: 'Request property manager annual statement and fee detail',
        daysBeforeDue: 7,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'propertyManager', equals: 'yes' }
      },
      {
        templateId: 'rental-collect-refinance-mortgage-documents',
        title: 'Collect refinance or new mortgage closing costs and loan terms',
        daysBeforeDue: 6,
        category: 'Document requests',
        audience: 'client',
        condition: { questionId: 'refinanceOrNewMortgage', equals: 'yes' }
      },
      {
        templateId: 'rental-gather-casualty-insurance-documents',
        title: 'Gather casualty loss records, insurance claim documents, and reimbursements',
        daysBeforeDue: 6,
        category: 'Document requests',
        audience: 'client',
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

function cleanClientName(clientName) {
  const cleanedName = clientName.trim();

  if (!cleanedName) {
    throw new Error('Client name is required.');
  }

  return cleanedName;
}

function normalizeIntakeAnswers(workflow, answers = {}) {
  return (workflow.questions ?? []).reduce((savedAnswers, question) => {
    savedAnswers[question.id] = answers[question.id] ?? '';
    return savedAnswers;
  }, {});
}

function createId(prefix) {
  if (globalThis.crypto?.randomUUID) {
    return `${prefix}-${globalThis.crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function buildTasks({ workflowKey, dueDate, intakeAnswers, existingTasks = [] }) {
  const workflow = workflows[workflowKey];
  const existingTasksByTemplateId = new Map(
    existingTasks.filter((task) => task.templateId).map((task) => [task.templateId, task])
  );
  const legacyExistingTasksByTitle = new Map(existingTasks.map((task) => [task.title, task]));

  return workflow.tasks.filter((task) => shouldIncludeTask(task, intakeAnswers)).map((task, index) => {
    const existingTask = existingTasksByTemplateId.get(task.templateId) ?? legacyExistingTasksByTitle.get(task.title);

    return {
      id: existingTask?.id ?? createId(`${workflowKey}-${index}`),
      templateId: task.templateId,
      title: task.title,
      category: task.category,
      audience: task.audience,
      audienceLabel: TASK_AUDIENCES[task.audience],
      suggestedDate: calculateSuggestedDate(dueDate, task.daysBeforeDue),
      completed: existingTask?.completed ?? false,
      notes: existingTask?.notes ?? ''
    };
  });
}

export function buildChecklist({ clientName, dueDate, workflowKey, answers = {} }) {
  const workflow = workflows[workflowKey];

  if (!workflow) {
    throw new Error('A valid workflow is required.');
  }

  const intakeAnswers = normalizeIntakeAnswers(workflow, answers);

  return {
    id: createId('checklist'),
    clientName: cleanClientName(clientName),
    dueDate,
    workflowKey,
    workflowName: workflow.name,
    intakeAnswers,
    createdAt: new Date().toISOString(),
    tasks: buildTasks({ workflowKey, dueDate, intakeAnswers })
  };
}

export function regenerateChecklist(checklist, { clientName, dueDate, answers = {} }) {
  const workflow = workflows[checklist.workflowKey];

  if (!workflow) {
    throw new Error('A valid workflow is required.');
  }

  const intakeAnswers = normalizeIntakeAnswers(workflow, answers);

  return {
    ...checklist,
    clientName: cleanClientName(clientName),
    dueDate,
    intakeAnswers,
    updatedAt: new Date().toISOString(),
    tasks: buildTasks({
      workflowKey: checklist.workflowKey,
      dueDate,
      intakeAnswers,
      existingTasks: checklist.tasks
    })
  };
}

export function duplicateChecklist(checklist) {
  return {
    ...checklist,
    id: createId('checklist'),
    clientName: `${checklist.clientName} (Copy)`,
    createdAt: new Date().toISOString(),
    updatedAt: undefined,
    tasks: checklist.tasks.map((task) => ({
      ...task,
      id: createId(`${checklist.workflowKey}-duplicate`)
    }))
  };
}

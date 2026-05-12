import { createEngagement, createId, createParty } from './models.js';

export const TASK_AUDIENCES = {
  internal: 'Internal',
  client: 'Client-facing'
};

export const workflows = {
  newTaxClientOnboarding: {
    name: 'New tax client onboarding',
    description: 'Collect authorization, prior-year details, entity information, and engagement documents.',
    engagementType: 'clientOnboarding',
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
    engagementType: 'businessMonthlyBookkeeping',
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
    engagementType: 'businessYearEndCleanup',
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
    engagementType: 'personalRentalScheduleE',
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

Object.assign(workflows, {
  personal1040Core: {
    name: 'Personal 1040 core',
    description: 'Core individual return intake with precise document branches and relationship-aware K-1 reminders.',
    engagementType: 'personal1040Core',
    clientType: 'person',
    questions: [
      { id: 'newSatcClient', label: 'New SAT-C client?', type: 'boolean' },
      { id: 'householdChanges', label: 'Filing status, spouse, dependent, custody, or childcare changes?', type: 'boolean' },
      { id: 'movedStates', label: 'Moved states during the year?', type: 'boolean' },
      { id: 'marketplaceInsurance', label: 'Marketplace health insurance coverage?', type: 'boolean', riskFlag: 'Marketplace Form 1095-A required' },
      { id: 'educationExpenses', label: 'Education expenses or scholarship activity?', type: 'boolean' },
      { id: 'retirementDistributions', label: 'Retirement distributions or IRA activity?', type: 'boolean' },
      { id: 'hsaActivity', label: 'HSA or MSA activity?', type: 'boolean' },
      { id: 'brokerageActivity', label: 'Brokerage sales or investment activity?', type: 'boolean' },
      { id: 'digitalAssets', label: 'Digital asset or crypto activity?', type: 'boolean', riskFlag: 'Crypto / digital asset activity' },
      { id: 'foreignAccounts', label: 'Foreign accounts or foreign financial assets?', type: 'boolean', riskFlag: 'Foreign accounts / FBAR review' },
      { id: 'homeTransaction', label: 'Home purchase, sale, or refinance?', type: 'boolean' },
      { id: 'expectedK1s', label: 'Expected S-corp or partnership K-1s?', type: 'boolean' }
    ],
    tasks: [
      { templateId: 'personal-1040-upload-w2-1099-core', title: 'Collect core income documents', daysBeforeDue: 21, category: 'Core documents', audience: 'client', clientRequestText: 'Upload Forms W-2, 1099-INT, 1099-DIV, 1099-B, 1099-G, and any other income forms received.', acceptedAlternatives: 'Organizer upload or secure portal batch upload.', whyNeeded: 'Core tax reporting documents are needed to prepare the Form 1040.', internalInstructions: 'Reconcile uploaded tax forms to organizer income sections.' },
      { templateId: 'personal-1040-request-prior-year-returns', title: 'Request prior-year returns', daysBeforeDue: 20, category: 'Prior year', audience: 'client', condition: { questionId: 'newSatcClient', equals: 'yes' }, clientRequestText: 'Upload prior-year federal and state tax returns, carryforward schedules, and any IRS or state notices received during the year.', internalInstructions: 'Map carryforwards, state residency, depreciation, capital loss, passive loss, and open notice issues.' },
      { templateId: 'personal-1040-household-change-documents', title: 'Request household change support', daysBeforeDue: 18, category: 'Household', audience: 'client', condition: { questionId: 'householdChanges', equals: 'yes' }, clientRequestText: 'Provide spouse and dependent names, SSNs, dates of birth, childcare provider tax ID details, and any divorce, separation, custody, or support documents affecting filing.' },
      { templateId: 'personal-1040-state-move-support', title: 'Request state move support', daysBeforeDue: 18, category: 'State filing', audience: 'client', condition: { questionId: 'movedStates', equals: 'yes' }, clientRequestText: 'Provide move dates, state-by-state wage or income breakdowns, and copies of any state tax notices.', internalInstructions: 'Review part-year and nonresident filing requirements.' },
      { templateId: 'personal-1040-marketplace-1095a', title: 'Request Marketplace Form 1095-A', daysBeforeDue: 16, category: 'Credits', audience: 'client', condition: { questionId: 'marketplaceInsurance', equals: 'yes' }, clientRequestText: 'Upload Form 1095-A for Marketplace coverage.', internalInstructions: 'Reconcile premium tax credit and flag missing 1095-A before filing.' },
      { templateId: 'personal-1040-education-1098t', title: 'Request education support', daysBeforeDue: 16, category: 'Credits', audience: 'client', condition: { questionId: 'educationExpenses', equals: 'yes' }, clientRequestText: 'Upload Form 1098-T, scholarship or grant details, and proof of out-of-pocket qualified education expenses.' },
      { templateId: 'personal-1040-retirement-hsa-documents', title: 'Request retirement and HSA forms', daysBeforeDue: 15, category: 'Retirement and HSA', audience: 'client', condition: { any: [{ questionId: 'retirementDistributions', equals: 'yes' }, { questionId: 'hsaActivity', equals: 'yes' }] }, clientRequestText: 'Upload Forms 1099-R and 5498 for retirement activity, plus Forms 1099-SA and 5498-SA for HSA or MSA activity.' },
      { templateId: 'personal-1040-brokerage-crypto-documents', title: 'Request brokerage and digital asset support', daysBeforeDue: 14, category: 'Investments', audience: 'client', condition: { any: [{ questionId: 'brokerageActivity', equals: 'yes' }, { questionId: 'digitalAssets', equals: 'yes' }] }, clientRequestText: 'Upload your consolidated brokerage 1099 package, realized gain detail, basis support, and crypto exchange transaction exports or CSV files.' },
      { templateId: 'personal-1040-foreign-account-details', title: 'Request foreign account details', daysBeforeDue: 14, category: 'Foreign reporting', audience: 'client', condition: { questionId: 'foreignAccounts', equals: 'yes' }, clientRequestText: 'Provide foreign account institution names, countries, account types, account numbers, and maximum balances during the year.', internalInstructions: 'Evaluate FBAR and Form 8938 thresholds.' },
      { templateId: 'personal-1040-home-closing-disclosure', title: 'Request home closing support', daysBeforeDue: 14, category: 'Home activity', audience: 'client', condition: { questionId: 'homeTransaction', equals: 'yes' }, clientRequestText: 'Upload closing disclosure for any home purchase, sale, or refinance, including Form 1098 or Form 1099-S if received.' },
      { templateId: 'personal-1040-request-k1s', title: 'Request passthrough K-1s', daysBeforeDue: 12, category: 'Passthrough income', audience: 'client', condition: { questionId: 'expectedK1s', equals: 'yes' }, clientRequestText: 'Upload all S-corp and partnership K-1s as they become available.', internalInstructions: 'Review passive activity, state K-1s, and basis support needs.' }
    ]
  },
  personalScheduleC: {
    name: 'Personal Schedule C', description: 'Sole proprietor business activity reported on an individual return.', engagementType: 'personalScheduleC', clientType: 'person',
    questions: [
      { id: 'newBusiness', label: 'New business activity started this year?', type: 'boolean' },
      { id: 'received1099Nec', label: 'Received Forms 1099-NEC?', type: 'boolean' },
      { id: 'received1099K', label: 'Received Forms 1099-K?', type: 'boolean' },
      { id: 'inventorySales', label: 'Inventory or product sales?', type: 'boolean' },
      { id: 'vehicleUse', label: 'Vehicle used for business?', type: 'boolean' },
      { id: 'homeOffice', label: 'Home office used?', type: 'boolean' },
      { id: 'contractorsPaid', label: 'Independent contractors paid?', type: 'boolean', riskFlag: 'Missing W-9s' },
      { id: 'assetPurchases', label: 'Equipment, software, furniture, or other asset purchases?', type: 'boolean' },
      { id: 'businessDigitalAssets', label: 'Digital assets used in the business?', type: 'boolean', riskFlag: 'Crypto / digital asset activity' }
    ],
    tasks: [
      { templateId: 'schedule-c-gross-receipts-summary', title: 'Request Schedule C gross receipts support', daysBeforeDue: 18, category: 'Income', audience: 'client', clientRequestText: 'Provide gross receipts summary from books, invoices, bank deposits, or payment platforms.' },
      { templateId: 'schedule-c-new-business-details', title: 'Request new business setup details', daysBeforeDue: 17, category: 'Business setup', audience: 'client', condition: { questionId: 'newBusiness', equals: 'yes' }, clientRequestText: 'Provide business start date, EIN if obtained, DBA or formation documents, business bank and credit card details, and accounting method or bookkeeping setup information.' },
      { templateId: 'schedule-c-upload-1099-nec', title: 'Request Forms 1099-NEC', daysBeforeDue: 16, category: 'Income', audience: 'client', condition: { questionId: 'received1099Nec', equals: 'yes' }, clientRequestText: 'Upload each Form 1099-NEC received.' },
      { templateId: 'schedule-c-upload-1099-k', title: 'Request Forms 1099-K', daysBeforeDue: 16, category: 'Income', audience: 'client', condition: { questionId: 'received1099K', equals: 'yes' }, clientRequestText: 'Upload each Form 1099-K received plus payment-platform gross receipts and fee detail.' },
      { templateId: 'schedule-c-inventory-cogs-support', title: 'Request inventory and COGS support', daysBeforeDue: 14, category: 'COGS', audience: 'client', condition: { questionId: 'inventorySales', equals: 'yes' }, clientRequestText: 'Upload ending inventory count, valuation method, purchase records, and COGS support.' },
      { templateId: 'schedule-c-mileage-log', title: 'Request mileage log', daysBeforeDue: 14, category: 'Vehicle', audience: 'client', condition: { questionId: 'vehicleUse', equals: 'yes' }, clientRequestText: 'Upload mileage log with business, commuting, and personal miles.' },
      { templateId: 'schedule-c-home-office-details', title: 'Request home office details', daysBeforeDue: 14, category: 'Home office', audience: 'client', condition: { questionId: 'homeOffice', equals: 'yes' }, clientRequestText: 'Provide home office square footage, total home square footage, and related home expense support.' },
      { templateId: 'schedule-c-contractor-w9-payments', title: 'Request contractor W-9s and totals', daysBeforeDue: 13, category: 'Contractors', audience: 'client', condition: { questionId: 'contractorsPaid', equals: 'yes' }, clientRequestText: 'Upload contractor W-9s and annual payment totals by vendor.' },
      { templateId: 'schedule-c-asset-purchase-invoices', title: 'Request asset purchase invoices', daysBeforeDue: 13, category: 'Assets', audience: 'client', condition: { questionId: 'assetPurchases', equals: 'yes' }, clientRequestText: 'Upload equipment, software, furniture, or asset purchase invoices with purchase dates and business-use percentage.' },
      { templateId: 'schedule-c-business-crypto-exports', title: 'Request business digital asset exports', daysBeforeDue: 13, category: 'Digital assets', audience: 'client', condition: { questionId: 'businessDigitalAssets', equals: 'yes' }, clientRequestText: 'Upload business digital asset transaction exports and basis support.', internalInstructions: 'Review ordinary income, capital gain, and payment treatment.' }
    ]
  },
  personalRentalScheduleE: { ...workflows.rentalPropertyTaxPrep, name: 'Personal rental Schedule E', engagementType: 'personalRentalScheduleE', clientType: 'person' },
  businessMonthlyBookkeeping: { ...workflows.monthlyBookkeeping, name: 'Business monthly bookkeeping', engagementType: 'businessMonthlyBookkeeping', clientType: 'business' },
  businessYearEndCleanup: { ...workflows.yearEndCleanup, name: 'Business year-end cleanup', engagementType: 'businessYearEndCleanup', clientType: 'business' },
  businessSCorpTax: {
    name: 'Business S corporation tax', description: 'S corporation tax return and owner spillover checklist.', engagementType: 'businessSCorpTax', clientType: 'business',
    questions: [
      { id: 'ownershipChanges', label: 'Ownership changes during the year?', type: 'boolean', riskFlag: 'Ownership change' },
      { id: 'shareholderDistributions', label: 'Shareholder distributions?', type: 'boolean', riskFlag: 'S-corp shareholder basis review' },
      { id: 'shareholderLoans', label: 'Shareholder loans or repayments?', type: 'boolean', riskFlag: 'S-corp shareholder basis review' },
      { id: 'shareholderPayroll', label: 'Shareholder payroll or W-2 items?', type: 'boolean' },
      { id: 'fixedAssets', label: 'Fixed asset additions or disposals?', type: 'boolean' },
      { id: 'inventory', label: 'Inventory or COGS activity?', type: 'boolean' },
      { id: 'foreignActivity', label: 'Foreign or international items?', type: 'boolean', riskFlag: 'K-2/K-3 foreign activity review' }
    ],
    tasks: [
      { templateId: 's-corp-upload-trial-balance', title: 'Request year-end trial balance', daysBeforeDue: 25, category: 'Core financials', audience: 'client', clientRequestText: 'Upload year-end trial balance, balance sheet, income statement, and general ledger.' },
      { templateId: 's-corp-ownership-change-documents', title: 'Request stock ledger and ownership change documents', daysBeforeDue: 20, category: 'Ownership', audience: 'client', condition: { questionId: 'ownershipChanges', equals: 'yes' }, clientRequestText: 'Upload stock ledger updates, ownership change documents, transfer agreements, or buy-sell support.' },
      { templateId: 's-corp-shareholder-distribution-detail', title: 'Request shareholder distribution detail', daysBeforeDue: 18, category: 'Shareholder basis', audience: 'client', condition: { questionId: 'shareholderDistributions', equals: 'yes' }, clientRequestText: 'Upload shareholder distribution detail by owner and date.' },
      { templateId: 's-corp-shareholder-loan-support', title: 'Request shareholder loan support', daysBeforeDue: 18, category: 'Shareholder basis', audience: 'client', condition: { questionId: 'shareholderLoans', equals: 'yes' }, clientRequestText: 'Upload shareholder loan balances, advances, repayments, and notes.' },
      { templateId: 's-corp-shareholder-payroll-support', title: 'Request shareholder payroll support', daysBeforeDue: 18, category: 'Payroll', audience: 'client', condition: { questionId: 'shareholderPayroll', equals: 'yes' }, clientRequestText: 'Upload shareholder W-2 and payroll support, including fringe benefit details.' },
      { templateId: 's-corp-fixed-asset-support', title: 'Request fixed asset documents', daysBeforeDue: 16, category: 'Assets', audience: 'client', condition: { questionId: 'fixedAssets', equals: 'yes' }, clientRequestText: 'Upload fixed asset additions, disposal documents, placed-in-service dates, and sale proceeds.' },
      { templateId: 's-corp-inventory-cogs-support', title: 'Request inventory and COGS support', daysBeforeDue: 16, category: 'COGS', audience: 'client', condition: { questionId: 'inventory', equals: 'yes' }, clientRequestText: 'Upload ending inventory, cost support, and COGS workpapers.' },
      { templateId: 's-corp-foreign-activity-support', title: 'Request foreign activity support', daysBeforeDue: 16, category: 'Foreign reporting', audience: 'client', condition: { questionId: 'foreignActivity', equals: 'yes' }, clientRequestText: 'Upload foreign activity support for K-2/K-3 review if applicable.' }
    ]
  },
  businessPartnershipTax: {
    name: 'Business partnership tax', description: 'Partnership tax return and partner K-1 checklist.', engagementType: 'businessPartnershipTax', clientType: 'business',
    questions: [
      { id: 'partnerChanges', label: 'Partner ownership changes?', type: 'boolean', riskFlag: 'Ownership change' },
      { id: 'agreementAmendments', label: 'Operating agreement amendments?', type: 'boolean' },
      { id: 'capitalActivity', label: 'Capital contributions or distributions?', type: 'boolean', riskFlag: 'Partnership capital / loan review' },
      { id: 'partnerLoans', label: 'Partner loans?', type: 'boolean', riskFlag: 'Partnership capital / loan review' },
      { id: 'multiStateActivity', label: 'Multi-state activity?', type: 'boolean', riskFlag: 'Multi-state filing' },
      { id: 'foreignActivity', label: 'Foreign activity?', type: 'boolean', riskFlag: 'K-2/K-3 foreign activity review' },
      { id: 'assetActivity', label: 'Asset acquisitions or disposals?', type: 'boolean' }
    ],
    tasks: [
      { templateId: 'partnership-upload-trial-balance', title: 'Request year-end trial balance', daysBeforeDue: 25, category: 'Core financials', audience: 'client', clientRequestText: 'Upload year-end trial balance, balance sheet, income statement, and general ledger.' },
      { templateId: 'partnership-ownership-change-documents', title: 'Request partner ownership change documents', daysBeforeDue: 20, category: 'Ownership', audience: 'client', condition: { questionId: 'partnerChanges', equals: 'yes' }, clientRequestText: 'Upload partner ownership change documents and updated ownership schedules.' },
      { templateId: 'partnership-operating-agreement-amendments', title: 'Request operating agreement amendments', daysBeforeDue: 20, category: 'Legal agreements', audience: 'client', condition: { questionId: 'agreementAmendments', equals: 'yes' }, clientRequestText: 'Upload operating agreement amendments.' },
      { templateId: 'partnership-capital-distribution-detail', title: 'Request capital activity detail', daysBeforeDue: 18, category: 'Partner capital', audience: 'client', condition: { questionId: 'capitalActivity', equals: 'yes' }, clientRequestText: 'Upload partner capital contribution and distribution detail by partner and date.' },
      { templateId: 'partnership-partner-loan-support', title: 'Request partner loan support', daysBeforeDue: 18, category: 'Partner loans', audience: 'client', condition: { questionId: 'partnerLoans', equals: 'yes' }, clientRequestText: 'Upload partner loan balances, advances, repayments, and notes.' },
      { templateId: 'partnership-multistate-apportionment-support', title: 'Request multi-state support', daysBeforeDue: 16, category: 'State filing', audience: 'client', condition: { questionId: 'multiStateActivity', equals: 'yes' }, clientRequestText: 'Upload multi-state income, payroll, property, sales, or apportionment support.' },
      { templateId: 'partnership-foreign-activity-support', title: 'Request foreign activity support', daysBeforeDue: 16, category: 'Foreign reporting', audience: 'client', condition: { questionId: 'foreignActivity', equals: 'yes' }, clientRequestText: 'Upload foreign activity support for K-2/K-3 review if applicable.' },
      { templateId: 'partnership-asset-acquisition-disposal-support', title: 'Request asset acquisition or disposition documents', daysBeforeDue: 16, category: 'Assets', audience: 'client', condition: { questionId: 'assetActivity', equals: 'yes' }, clientRequestText: 'Upload asset acquisition or disposition documents, placed-in-service dates, and sale proceeds.' }
    ]
  }
});

delete workflows.newTaxClientOnboarding;
delete workflows.monthlyBookkeeping;
delete workflows.yearEndCleanup;
delete workflows.rentalPropertyTaxPrep;

export function calculateSuggestedDate(dueDateValue, daysBeforeDue) {
  const dueDate = new Date(`${dueDateValue}T12:00:00`);

  if (Number.isNaN(dueDate.getTime())) {
    throw new Error('A valid due date is required.');
  }

  const suggestedDate = new Date(dueDate);
  suggestedDate.setDate(suggestedDate.getDate() - daysBeforeDue);
  return suggestedDate.toISOString().slice(0, 10);
}

export function evaluateCondition(condition, answers = {}) {
  if (!condition) {
    return true;
  }

  if (condition.all) {
    return condition.all.every((childCondition) => evaluateCondition(childCondition, answers));
  }

  if (condition.any) {
    return condition.any.some((childCondition) => evaluateCondition(childCondition, answers));
  }

  const value = answers[condition.questionId];

  if (Object.hasOwn(condition, 'equals')) {
    return value === condition.equals;
  }

  if (Object.hasOwn(condition, 'notEquals')) {
    return value !== condition.notEquals;
  }

  if (Object.hasOwn(condition, 'includes')) {
    return Array.isArray(value) ? value.includes(condition.includes) : String(value ?? '').includes(condition.includes);
  }

  if (Object.hasOwn(condition, 'greaterThan')) {
    return Number(value) > Number(condition.greaterThan);
  }

  if (Object.hasOwn(condition, 'lessThan')) {
    return Number(value) < Number(condition.lessThan);
  }

  return true;
}

export function shouldIncludeTask(task, answers = {}) {
  return evaluateCondition(task.condition, answers);
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
      clientRequestText: task.clientRequestText ?? '',
      acceptedAlternatives: task.acceptedAlternatives ?? '',
      whyNeeded: task.whyNeeded ?? '',
      internalInstructions: task.internalInstructions ?? '',
      suggestedDate: calculateSuggestedDate(dueDate, task.daysBeforeDue),
      completed: existingTask?.completed ?? false,
      notes: existingTask?.notes ?? ''
    };
  });
}


export const WORKFLOW_KEYS_BY_CLIENT_TYPE = {
  person: ['personal1040Core', 'personalScheduleC', 'personalRentalScheduleE'],
  business: ['businessMonthlyBookkeeping', 'businessYearEndCleanup', 'businessSCorpTax', 'businessPartnershipTax']
};

export function getWorkflowKeysForClientType(clientType) {
  return WORKFLOW_KEYS_BY_CLIENT_TYPE[clientType] ?? [];
}

export function getWorkflowsForClientType(clientType) {
  return getWorkflowKeysForClientType(clientType).map((workflowKey) => [workflowKey, workflows[workflowKey]]);
}

function isTruthyAnswer(value) {
  return value === true || value === 'yes' || value === 'true' || Number(value) > 0;
}

export function generateRiskFlags({ workflowKey, answers = {}, linkedClients = [], relationships = [] }) {
  const workflow = workflows[workflowKey];
  const flags = new Set();

  (workflow?.questions ?? []).forEach((question) => {
    if (question.riskFlag && isTruthyAnswer(answers[question.id])) {
      flags.add(question.riskFlag);
    }
  });

  if (workflowKey === 'personal1040Core') {
    linkedClients.forEach((client) => {
      if (client.taxTreatment === 'sCorp') {
        flags.add('S-corp shareholder basis review');
      }

      if (client.taxTreatment === 'partnership') {
        flags.add('Partnership K-1 receipt review');
      }
    });
  }

  if (['businessSCorpTax', 'businessPartnershipTax'].includes(workflowKey)) {
    const hasOwners = relationships.some((relationship) =>
      ['owner', 'shareholder', 'partner'].includes(relationship.relationshipType)
    );

    if (hasOwners) {
      flags.add('Linked owner K-1 delivery');
    }
  }

  return [...flags];
}

function createRelationshipGeneratedTasks({ workflowKey, dueDate, linkedClients = [], relationships = [], existingTasks = [], taxYear = '', existingEngagements = [] }) {
  const existingTasksByTemplateId = new Map(existingTasks.map((task) => [task.templateId, task]));
  const templates = [];

  if (workflowKey === 'personal1040Core') {
    linkedClients.forEach((client) => {
      if (client.clientType !== 'business') {
        return;
      }

      if (['sCorp', 'partnership'].includes(client.taxTreatment)) {
        templates.push({
          templateId: `relationship-personal-1040-k1-${client.id}`,
          title: `Track expected K-1 from ${client.displayName}`,
          category: 'Linked client reminders',
          audience: 'internal',
          daysBeforeDue: 10,
          internalInstructions: `Confirm final ${client.taxTreatment === 'sCorp' ? 'S-corp' : 'partnership'} K-1 is received from ${client.displayName}.`
        });
      }

      if (client.taxTreatment === 'sCorp') {
        templates.push({
          templateId: `relationship-personal-1040-7203-${client.id}`,
          title: `Review shareholder basis support for ${client.displayName}`,
          category: 'Linked client reminders',
          audience: 'internal',
          daysBeforeDue: 9,
          internalInstructions: `Review whether Form 7203/shareholder basis support is needed for ${client.displayName}.`
        });
      }

      if (client.taxTreatment === 'partnership') {
        templates.push({
          templateId: `relationship-personal-1040-partnership-k1-${client.id}`,
          title: `Confirm partnership K-1 reporting for ${client.displayName}`,
          category: 'Linked client reminders',
          audience: 'internal',
          daysBeforeDue: 9,
          internalInstructions: `Confirm partnership K-1 state and passive activity details for ${client.displayName}.`
        });
      }
    });
  }

  if (['businessSCorpTax', 'businessPartnershipTax'].includes(workflowKey)) {
    relationships
      .filter((relationship) => ['owner', 'shareholder', 'partner'].includes(relationship.relationshipType))
      .forEach((relationship) => {
        const owner = linkedClients.find((client) => [relationship.fromClientId, relationship.toClientId].includes(client.id));

        if (!owner || owner.clientType !== 'person') {
          return;
        }

        const linkedPersonalReturn = existingEngagements.some(
          (engagement) =>
            engagement.clientId === owner.id &&
            engagement.engagementType === 'personal1040Core' &&
            String(engagement.taxYear ?? '') === String(taxYear ?? '')
        );

        templates.push({
          templateId: `relationship-business-deliver-k1-${owner.id}`,
          title: `Deliver final K-1 to ${owner.displayName}`,
          category: 'Linked owner reminders',
          audience: 'internal',
          daysBeforeDue: 5,
          internalInstructions: linkedPersonalReturn
            ? `Feeds linked personal return for ${owner.displayName}. Deliver final K-1 and mark owner follow-up complete.`
            : `Deliver final K-1 to ${owner.displayName} and note whether a linked personal return is needed.`
        });
      });
  }

  return templates.map((task, index) => {
    const existingTask = existingTasksByTemplateId.get(task.templateId);

    return {
      id: existingTask?.id ?? createId(`${workflowKey}-relationship-${index}`),
      templateId: task.templateId,
      title: task.title,
      category: task.category,
      audience: task.audience,
      audienceLabel: TASK_AUDIENCES[task.audience],
      clientRequestText: task.clientRequestText ?? '',
      acceptedAlternatives: task.acceptedAlternatives ?? '',
      whyNeeded: task.whyNeeded ?? '',
      internalInstructions: task.internalInstructions ?? '',
      suggestedDate: calculateSuggestedDate(dueDate, task.daysBeforeDue),
      clientRequestText: task.clientRequestText ?? '',
      acceptedAlternatives: task.acceptedAlternatives ?? '',
      whyNeeded: task.whyNeeded ?? '',
      internalInstructions: task.internalInstructions ?? '',
      relationshipGenerated: true,
      completed: existingTask?.completed ?? false,
      notes: existingTask?.notes ?? ''
    };
  });
}

export function buildChecklist({ clientName, dueDate, workflowKey, answers = {}, partyType = 'person' }) {
  const workflow = workflows[workflowKey];

  if (!workflow) {
    throw new Error('A valid workflow is required.');
  }

  const intakeAnswers = normalizeIntakeAnswers(workflow, answers);
  const party = createParty({ displayName: clientName, partyType });
  const engagement = createEngagement({
    partyId: party.id,
    engagementType: workflow.engagementType,
    dueDate
  });

  return {
    id: createId('checklist'),
    clientName: party.displayName,
    party,
    engagement,
    dueDate,
    workflowKey,
    workflowName: workflow.name,
    intakeAnswers,
    createdAt: new Date().toISOString(),
    tasks: buildTasks({ workflowKey, dueDate, intakeAnswers })
  };
}

export function regenerateChecklist(checklist, { clientName, dueDate, answers = {}, partyType = checklist.party?.partyType ?? 'person' }) {
  const workflow = workflows[checklist.workflowKey];

  if (!workflow) {
    throw new Error('A valid workflow is required.');
  }

  const intakeAnswers = normalizeIntakeAnswers(workflow, answers);
  const party = createParty({ displayName: clientName, partyType });
  const engagement = createEngagement({
    partyId: party.id,
    engagementType: workflow.engagementType,
    dueDate
  });

  return {
    ...checklist,
    clientName: party.displayName,
    party,
    engagement,
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


export function buildEngagementForClient({
  client,
  workflowKey,
  dueDate,
  taxYear = '',
  periodEnd = '',
  relatedClientIds = [],
  intakeAnswers = {},
  linkedClients = [],
  relationships = [],
  existingTasks = [],
  existingEngagements = []
}) {
  const workflow = workflows[workflowKey];

  if (!workflow) {
    throw new Error('A valid workflow is required.');
  }

  if (workflow.clientType && workflow.clientType !== client.clientType) {
    throw new Error('Workflow is not available for this client type.');
  }

  const normalizedAnswers = normalizeIntakeAnswers(workflow, intakeAnswers);
  const workflowTasks = buildTasks({ workflowKey, dueDate, intakeAnswers: normalizedAnswers, existingTasks });
  const relationshipTasks = createRelationshipGeneratedTasks({
    workflowKey,
    dueDate,
    linkedClients,
    relationships,
    existingTasks,
    taxYear,
    existingEngagements
  });
  const riskFlags = generateRiskFlags({ workflowKey, answers: normalizedAnswers, linkedClients, relationships });

  return createEngagement({
    clientId: client.id,
    engagementType: workflow.engagementType,
    workflowKey,
    taxYear,
    periodEnd,
    dueDate,
    relatedClientIds,
    intakeAnswers: normalizedAnswers,
    riskFlags,
    tasks: [...workflowTasks, ...relationshipTasks]
  });
}

export function regenerateEngagementForClient(engagement, context) {
  const regeneratedEngagement = buildEngagementForClient({
    ...context,
    workflowKey: engagement.workflowKey,
    dueDate: context.dueDate ?? engagement.dueDate,
    taxYear: context.taxYear ?? engagement.taxYear,
    periodEnd: context.periodEnd ?? engagement.periodEnd,
    relatedClientIds: context.relatedClientIds ?? engagement.relatedClientIds,
    intakeAnswers: context.intakeAnswers ?? engagement.intakeAnswers,
    existingTasks: engagement.tasks,
    existingEngagements: context.existingEngagements ?? []
  });

  return {
    ...engagement,
    ...regeneratedEngagement,
    id: engagement.id,
    createdAt: engagement.createdAt,
    updatedAt: new Date().toISOString()
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

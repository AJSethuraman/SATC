import test from 'node:test';
import assert from 'node:assert/strict';
import { buildChecklist, calculateSuggestedDate, getWorkflowQuestions, workflows } from '../src/workflows.js';

const baseRentalTaskCount = workflows.rentalPropertyTaxPrep.tasks.filter((task) => !task.condition).length;

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

test('builds checklist tasks from a selected workflow', () => {
  const checklist = buildChecklist({
    clientName: '  Acme LLC  ',
    dueDate: '2026-04-15',
    workflowKey: 'monthlyBookkeeping'
  });

  assert.equal(checklist.clientName, 'Acme LLC');
  assert.equal(checklist.workflowName, 'Monthly bookkeeping');
  assert.equal(checklist.tasks.length, workflows.monthlyBookkeeping.tasks.length);
  assert.equal(checklist.tasks.at(-1).suggestedDate, '2026-04-15');
  assert.equal(checklist.tasks.every((task) => task.completed === false), true);
});

test('rental property workflow exposes optional intake questions', () => {
  assert.deepEqual(
    getWorkflowQuestions('rentalPropertyTaxPrep').map((question) => question.id),
    [
      'purchasedThisYear',
      'soldThisYear',
      'majorImprovements',
      'personalUseDays',
      'shortTermRentalActivity',
      'outOfStateProperty',
      'propertyManager',
      'refinanceOrNewMortgage',
      'casualtyLossOrInsuranceClaim'
    ]
  );
});

test('omits conditional rental tasks when intake answers do not match', () => {
  const checklist = buildChecklist({
    clientName: 'Lake House',
    dueDate: '2026-04-15',
    workflowKey: 'rentalPropertyTaxPrep',
    answers: {
      purchasedThisYear: 'no',
      soldThisYear: 'no',
      majorImprovements: 'no'
    }
  });

  assert.equal(checklist.tasks.length, baseRentalTaskCount);
  assert.equal(
    checklist.tasks.some((task) => task.title.includes('closing statement and purchase allocation')),
    false
  );
});

test('adds matching conditional rental tasks and saves intake answers', () => {
  const checklist = buildChecklist({
    clientName: 'Lake House',
    dueDate: '2026-04-15',
    workflowKey: 'rentalPropertyTaxPrep',
    answers: {
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
  });

  assert.equal(checklist.tasks.length, workflows.rentalPropertyTaxPrep.tasks.length);
  assert.equal(checklist.intakeAnswers.propertyManager, 'yes');
  assert.equal(checklist.intakeAnswers.soldThisYear, 'yes');
  assert.deepEqual(
    [
      'Collect closing statement and purchase allocation details',
      'Collect sale closing statement and calculate rental property disposition details',
      'Request invoices and placed-in-service dates for major improvements',
      'Document personal-use days and allocate mixed-use expenses',
      'Review short-term rental days, services provided, and occupancy tax details',
      'Confirm nonresident state filing requirements for out-of-state property',
      'Request property manager annual statement and fee detail',
      'Collect refinance or new mortgage closing costs and loan terms',
      'Gather casualty loss records, insurance claim documents, and reimbursements'
    ].every((title) => checklist.tasks.some((task) => task.title === title)),
    true
  );
});

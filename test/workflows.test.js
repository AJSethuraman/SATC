import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createBusinessClient,
  createEngagement,
  createPersonClient,
  createRelationship,
  getLinkedClients
} from '../src/models.js';
import { generateClientRequestEmail, getClientFacingTasks, groupTasksByCategory } from '../src/outputs.js';
import {
  buildEngagementForClient,
  buildChecklist,
  calculateSuggestedDate,
  getWorkflowKeysForClientType,
  regenerateEngagementForClient,
  workflows
} from '../src/workflows.js';

function yesAnswers(workflowKey) {
  return Object.fromEntries((workflows[workflowKey].questions ?? []).map((question) => [question.id, 'yes']));
}

test('creates person clients', () => {
  const client = createPersonClient({ firstName: 'Jane', lastName: 'Client', email: 'jane@example.com' });

  assert.equal(client.clientType, 'person');
  assert.equal(client.displayName, 'Jane Client');
  assert.equal(client.email, 'jane@example.com');
});

test('creates business clients', () => {
  const client = createBusinessClient({ legalName: 'Client Co LLC', taxTreatment: 'sCorp', einLast4: '1234' });

  assert.equal(client.clientType, 'business');
  assert.equal(client.displayName, 'Client Co LLC');
  assert.equal(client.taxTreatment, 'sCorp');
  assert.equal(client.einLast4, '1234');
});

test('links people and businesses many-to-many', () => {
  const jane = createPersonClient({ firstName: 'Jane', lastName: 'Client' });
  const alex = createPersonClient({ firstName: 'Alex', lastName: 'Owner' });
  const scorp = createBusinessClient({ legalName: 'SATC Ops Inc', taxTreatment: 'sCorp' });
  const partnership = createBusinessClient({ legalName: 'Rental Partners LP', taxTreatment: 'partnership' });
  const relationships = [
    createRelationship({ fromClientId: jane.id, toClientId: scorp.id, relationshipType: 'shareholder', ownershipPercent: '60' }),
    createRelationship({ fromClientId: jane.id, toClientId: partnership.id, relationshipType: 'partner', ownershipPercent: '50' }),
    createRelationship({ fromClientId: alex.id, toClientId: scorp.id, relationshipType: 'officer' })
  ];

  assert.deepEqual(
    getLinkedClients([jane, alex, scorp, partnership], relationships, jane.id).map((client) => client.displayName).sort(),
    ['Rental Partners LP', 'SATC Ops Inc']
  );
  assert.deepEqual(
    getLinkedClients([jane, alex, scorp, partnership], relationships, scorp.id).map((client) => client.displayName).sort(),
    ['Alex Owner', 'Jane Client']
  );
});

test('filters workflows by client type', () => {
  assert.deepEqual(getWorkflowKeysForClientType('person'), [
    'personal1040Core',
    'personalScheduleC',
    'personalRentalScheduleE'
  ]);
  assert.deepEqual(getWorkflowKeysForClientType('business'), [
    'businessMonthlyBookkeeping',
    'businessYearEndCleanup',
    'businessSCorpTax',
    'businessPartnershipTax'
  ]);
});

test('creates engagements from saved client records', () => {
  const client = createBusinessClient({ legalName: 'Client Co LLC', taxTreatment: 'sCorp' });
  const engagement = buildEngagementForClient({
    client,
    workflowKey: 'businessSCorpTax',
    taxYear: '2026',
    dueDate: '2027-03-15',
    intakeAnswers: yesAnswers('businessSCorpTax')
  });

  assert.equal(engagement.clientId, client.id);
  assert.equal(engagement.engagementType, 'businessSCorpTax');
  assert.equal(engagement.workflowKey, 'businessSCorpTax');
  assert.ok(engagement.tasks.length > 1);
});

test('calculates suggested dates before the due date', () => {
  assert.equal(calculateSuggestedDate('2026-04-15', 10), '2026-04-05');
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

test('generated tasks include id and templateId', () => {
  const client = createPersonClient({ firstName: 'Jane', lastName: 'Client' });
  const engagement = buildEngagementForClient({
    client,
    workflowKey: 'personal1040Core',
    dueDate: '2027-04-15',
    intakeAnswers: yesAnswers('personal1040Core')
  });

  assert.equal(engagement.tasks.every((task) => task.id && task.templateId), true);
});

test('regenerating engagement preserves notes and completion by templateId', () => {
  const client = createPersonClient({ firstName: 'Jane', lastName: 'Client' });
  const engagement = buildEngagementForClient({
    client,
    workflowKey: 'personalScheduleC',
    dueDate: '2027-04-15',
    intakeAnswers: { ...yesAnswers('personalScheduleC'), vehicleUse: 'no' }
  });
  const trackedTask = engagement.tasks.find((task) => task.templateId === 'schedule-c-upload-1099-nec');
  trackedTask.completed = true;
  trackedTask.notes = 'Uploaded by client.';

  const regenerated = regenerateEngagementForClient(engagement, {
    client,
    dueDate: '2027-04-20',
    intakeAnswers: { ...yesAnswers('personalScheduleC'), vehicleUse: 'yes' }
  });
  const preservedTask = regenerated.tasks.find((task) => task.templateId === 'schedule-c-upload-1099-nec');
  const newTask = regenerated.tasks.find((task) => task.templateId === 'schedule-c-mileage-log');

  assert.equal(preservedTask.completed, true);
  assert.equal(preservedTask.notes, 'Uploaded by client.');
  assert.equal(newTask.completed, false);
  assert.equal(newTask.notes, '');
});

test('relationship-generated K-1 reminders appear for linked businesses on personal 1040 engagements', () => {
  const person = createPersonClient({ firstName: 'Jane', lastName: 'Client' });
  const scorp = createBusinessClient({ legalName: 'Client S Corp', taxTreatment: 'sCorp' });
  const partnership = createBusinessClient({ legalName: 'Client Partnership', taxTreatment: 'partnership' });
  const relationships = [
    createRelationship({ fromClientId: person.id, toClientId: scorp.id, relationshipType: 'shareholder' }),
    createRelationship({ fromClientId: person.id, toClientId: partnership.id, relationshipType: 'partner' })
  ];
  const engagement = buildEngagementForClient({
    client: person,
    workflowKey: 'personal1040Core',
    taxYear: '2026',
    dueDate: '2027-04-15',
    intakeAnswers: { expectedK1s: 'yes' },
    linkedClients: [scorp, partnership],
    relationships
  });

  assert.equal(engagement.tasks.some((task) => task.templateId === `relationship-personal-1040-k1-${scorp.id}`), true);
  assert.equal(engagement.tasks.some((task) => task.templateId === `relationship-personal-1040-7203-${scorp.id}`), true);
  assert.equal(engagement.tasks.some((task) => task.templateId === `relationship-personal-1040-partnership-k1-${partnership.id}`), true);
  assert.equal(engagement.riskFlags.includes('S-corp shareholder basis review'), true);
});

test('linked owner reminders appear on S-corp and partnership engagements', () => {
  const owner = createPersonClient({ firstName: 'Jane', lastName: 'Client' });
  const scorp = createBusinessClient({ legalName: 'Client S Corp', taxTreatment: 'sCorp' });
  const relationship = createRelationship({ fromClientId: owner.id, toClientId: scorp.id, relationshipType: 'shareholder' });
  const personalEngagement = createEngagement({
    clientId: owner.id,
    engagementType: 'personal1040Core',
    workflowKey: 'personal1040Core',
    taxYear: '2026',
    dueDate: '2027-04-15'
  });
  const engagement = buildEngagementForClient({
    client: scorp,
    workflowKey: 'businessSCorpTax',
    taxYear: '2026',
    dueDate: '2027-03-15',
    intakeAnswers: yesAnswers('businessSCorpTax'),
    linkedClients: [owner],
    relationships: [relationship],
    existingEngagements: [personalEngagement]
  });

  const reminder = engagement.tasks.find((task) => task.templateId === `relationship-business-deliver-k1-${owner.id}`);
  assert.ok(reminder);
  assert.match(reminder.internalInstructions, /Feeds linked personal return/);
  assert.equal(engagement.riskFlags.includes('Linked owner K-1 delivery'), true);
});

test('risk flags are generated from intake answers', () => {
  const client = createPersonClient({ firstName: 'Jane', lastName: 'Client' });
  const engagement = buildEngagementForClient({
    client,
    workflowKey: 'personal1040Core',
    dueDate: '2027-04-15',
    intakeAnswers: { marketplaceInsurance: 'yes', digitalAssets: 'yes', foreignAccounts: 'yes' }
  });

  assert.deepEqual(engagement.riskFlags.sort(), [
    'Crypto / digital asset activity',
    'Foreign accounts / FBAR review',
    'Marketplace Form 1095-A required'
  ]);
});

test('client-facing request filtering and grouped output still work', () => {
  const client = createBusinessClient({ legalName: 'Client Co LLC', taxTreatment: 'sCorp' });
  const engagement = buildEngagementForClient({
    client,
    workflowKey: 'businessSCorpTax',
    dueDate: '2027-03-15',
    intakeAnswers: yesAnswers('businessSCorpTax')
  });
  const clientTasks = getClientFacingTasks(engagement.tasks);
  const grouped = groupTasksByCategory(clientTasks);

  assert.equal(clientTasks.every((task) => task.audience === 'client'), true);
  assert.ok(grouped.some((group) => group.category === 'Core financials'));
});

test('client request email uses clientRequestText and excludes internal tasks', () => {
  const client = createPersonClient({ firstName: 'Jane', lastName: 'Client' });
  const engagement = buildEngagementForClient({
    client,
    workflowKey: 'personal1040Core',
    dueDate: '2027-04-15',
    intakeAnswers: { marketplaceInsurance: 'yes', foreignAccounts: 'yes' }
  });
  const email = generateClientRequestEmail({ ...engagement, clientName: client.displayName });

  assert.match(email, /Upload Form 1095-A for Marketplace coverage/);
  assert.match(email, /Provide foreign account institution names/);
  assert.doesNotMatch(email, /Evaluate FBAR/);
});

test('business and person client records persist separately from engagements', () => {
  const person = createPersonClient({ firstName: 'Jane', lastName: 'Client' });
  const business = createBusinessClient({ legalName: 'Client Co LLC', taxTreatment: 'partnership' });
  const engagement = buildEngagementForClient({
    client: business,
    workflowKey: 'businessPartnershipTax',
    dueDate: '2027-03-15',
    intakeAnswers: yesAnswers('businessPartnershipTax')
  });
  const persistedState = { clients: [person, business], relationships: [], engagements: [engagement] };

  assert.equal(persistedState.clients.length, 2);
  assert.equal(persistedState.engagements[0].clientId, business.id);
  assert.notDeepEqual(persistedState.clients[1], persistedState.engagements[0]);
});

export const CLIENT_TYPES = {
  person: 'Person',
  business: 'Business'
};

export const PARTY_TYPES = CLIENT_TYPES;

export const RELATIONSHIP_TYPES = {
  spouse: 'Spouse',
  dependent: 'Dependent',
  owner: 'Owner',
  shareholder: 'Shareholder',
  partner: 'Partner',
  officer: 'Officer',
  authorizedContact: 'Authorized contact',
  payrollContact: 'Payroll contact',
  bookkeeper: 'Bookkeeper'
};

export const ENGAGEMENT_TYPES = {
  personal1040Core: 'Personal 1040 core',
  personalScheduleC: 'Personal Schedule C',
  personalRentalScheduleE: 'Personal rental Schedule E',
  businessMonthlyBookkeeping: 'Business monthly bookkeeping',
  businessYearEndCleanup: 'Business year-end cleanup',
  businessSCorpTax: 'Business S corporation tax',
  businessPartnershipTax: 'Business partnership tax',
  clientOnboarding: 'Client onboarding'
};

export function createId(prefix) {
  if (globalThis.crypto?.randomUUID) {
    return `${prefix}-${globalThis.crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function requireText(value, message) {
  const cleanValue = String(value ?? '').trim();

  if (!cleanValue) {
    throw new Error(message);
  }

  return cleanValue;
}

export function createPersonClient({ firstName, lastName, email = '', phone = '', notes = '' }) {
  const cleanFirstName = requireText(firstName, 'First name is required.');
  const cleanLastName = requireText(lastName, 'Last name is required.');

  return {
    id: createId('client'),
    clientType: 'person',
    firstName: cleanFirstName,
    lastName: cleanLastName,
    displayName: `${cleanFirstName} ${cleanLastName}`,
    email: email.trim(),
    phone: phone.trim(),
    notes: notes.trim(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
}

export function createBusinessClient({
  legalName,
  dbaName = '',
  entityType = '',
  taxTreatment = '',
  einLast4 = '',
  email = '',
  phone = '',
  notes = ''
}) {
  const cleanLegalName = requireText(legalName, 'Legal name is required.');

  return {
    id: createId('client'),
    clientType: 'business',
    legalName: cleanLegalName,
    dbaName: dbaName.trim(),
    displayName: dbaName.trim() || cleanLegalName,
    entityType: entityType.trim(),
    taxTreatment: taxTreatment.trim(),
    einLast4: einLast4.trim(),
    email: email.trim(),
    phone: phone.trim(),
    notes: notes.trim(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
}

export function createParty({ displayName, partyType = 'person' }) {
  if (partyType === 'business') {
    return createBusinessClient({ legalName: displayName });
  }

  const [firstName = displayName, ...lastParts] = String(displayName).trim().split(/\s+/);
  return createPersonClient({ firstName, lastName: lastParts.join(' ') || 'Client' });
}

export function createRelationship({
  fromClientId,
  toClientId,
  fromPartyId,
  toPartyId,
  relationshipType,
  ownershipPercent = '',
  isPrimary = false,
  notes = '',
  details = {}
}) {
  return {
    id: createId('relationship'),
    fromClientId: fromClientId ?? fromPartyId,
    toClientId: toClientId ?? toPartyId,
    relationshipType,
    ownershipPercent: ownershipPercent || details.ownershipPercent || '',
    isPrimary: Boolean(isPrimary || details.primaryContact),
    notes: notes.trim?.() ?? '',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
}

export function getRelationshipsForClient(relationships, clientId) {
  return relationships.filter(
    (relationship) => relationship.fromClientId === clientId || relationship.toClientId === clientId
  );
}

export function getLinkedClients(clients, relationships, clientId) {
  const linkedIds = new Set(
    getRelationshipsForClient(relationships, clientId).map((relationship) =>
      relationship.fromClientId === clientId ? relationship.toClientId : relationship.fromClientId
    )
  );

  return clients.filter((client) => linkedIds.has(client.id));
}

export function createEngagement({
  clientId,
  partyId,
  engagementType,
  workflowKey,
  taxYear = '',
  periodEnd = '',
  dueDate,
  relatedClientIds = [],
  relatedPartyIds = [],
  intakeAnswers = {},
  riskFlags = [],
  tasks = []
}) {
  const linkedIds = relatedClientIds.length ? relatedClientIds : relatedPartyIds;

  return {
    id: createId('engagement'),
    clientId: clientId ?? partyId,
    engagementType,
    workflowKey,
    taxYear,
    periodEnd,
    dueDate,
    relatedClientIds: linkedIds,
    intakeAnswers,
    riskFlags,
    tasks,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
}

export function updateEngagementTasks(engagement, tasks, riskFlags = engagement.riskFlags ?? []) {
  return {
    ...engagement,
    tasks,
    riskFlags,
    updatedAt: new Date().toISOString()
  };
}

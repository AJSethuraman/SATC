export const PARTY_TYPES = {
  person: 'Person',
  business: 'Business'
};

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
  clientOnboarding: 'Client onboarding',
  personal1040: 'Personal 1040',
  personalRentalScheduleE: 'Personal rental Schedule E',
  personalScheduleC: 'Personal Schedule C',
  businessMonthlyBookkeeping: 'Business monthly bookkeeping',
  businessYearEndCleanup: 'Business year-end cleanup',
  businessSCorpTax: 'Business S corporation tax',
  businessPartnershipTax: 'Business partnership tax'
};

export function createId(prefix) {
  if (globalThis.crypto?.randomUUID) {
    return `${prefix}-${globalThis.crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function createParty({ displayName, partyType = 'person' }) {
  const cleanName = displayName.trim();

  if (!cleanName) {
    throw new Error('Client name is required.');
  }

  return {
    id: createId('party'),
    partyType,
    displayName: cleanName,
    legalName: cleanName,
    preferredName: partyType === 'person' ? cleanName : '',
    dba: partyType === 'business' ? '' : undefined,
    entityType: partyType === 'business' ? '' : undefined,
    taxTreatment: partyType === 'business' ? '' : undefined,
    email: '',
    phone: ''
  };
}

export function createRelationship({ fromPartyId, toPartyId, relationshipType, details = {} }) {
  return {
    id: createId('relationship'),
    fromPartyId,
    toPartyId,
    relationshipType,
    ownershipPercent: details.ownershipPercent ?? '',
    startDate: details.startDate ?? '',
    endDate: details.endDate ?? '',
    primaryContact: Boolean(details.primaryContact)
  };
}

export function createEngagement({ partyId, engagementType, dueDate, relatedPartyIds = [], taxYear = '', periodEnd = '' }) {
  return {
    id: createId('engagement'),
    partyId,
    engagementType,
    taxYear,
    periodEnd,
    dueDate,
    relatedPartyIds
  };
}

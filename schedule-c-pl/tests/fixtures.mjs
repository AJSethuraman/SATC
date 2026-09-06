/* Returns the tests and the browser walk both use, so a scenario that is
   asserted in Node is the same scenario a person clicks through. */

import { emptyReturn } from '../src/engine.mjs';

const c = (dollars) => Math.round(dollars * 100);

/** A photographer. Services only, no stock, mileage and the square-foot
    home office method — the shape most Schedule C filers are. */
export function freelancer() {
  const r = emptyReturn(2025);
  r.business = { name: 'Rowan Vale Photography', activity: 'Portrait photography' };
  r.materiallyParticipated = true;
  r.atRisk = 'all';
  r.homeOfficeMethod = 'simplified';
  r.entries = {
    1: c(94_250), 2: c(1_100), 6: c(420),
    8: c(2_340.75), 9: c(3_857), 10: c(1_180), 15: c(1_425),
    17: c(900), 18: c(612.40), 22: c(3_910.55), 23: c(485),
    24: undefined, '24a': c(1_204.18), '24b': c(311.50), 25: c(1_860), 30: c(1_100),
  };
  delete r.entries[24];
  r.details = {
    other: [
      { label: 'Editing software', cents: c(599.88) },
      { label: 'Website hosting', cents: c(214.20) },
      { label: 'Professional body membership', cents: c(325) },
    ],
  };
  r.vehicle = {
    placedInService: '2022-03-14', businessMiles: 5510, commutingMiles: 1200, otherMiles: 3400,
    personalUse: true, anotherVehicle: false, evidence: true, evidenceWritten: true,
  };
  return r;
}

/** A reseller. Part III does real work here and line 4 is not zero. */
export function reseller() {
  const r = emptyReturn(2025);
  r.business = { name: 'Halden Trading Co', activity: 'Online resale of vintage tools' };
  r.materiallyParticipated = true;
  r.atRisk = 'all';
  r.accountingMethod = 'accrual';
  r.inventory = { method: 'cost', changed: false };
  r.entries = {
    1: c(211_480.33), 2: c(6_215.10),
    8: c(9_400), 10: c(14_622.85), 15: c(2_100), 18: c(1_045.60),
    '20b': c(8_000), 21: c(760.25), 22: c(4_115), 23: c(2_940), 26: c(31_000),
    35: c(42_800), 36: c(96_215.44), 37: c(3_200), 38: c(1_845.10), 39: c(2_610), 41: c(38_950.25),
  };
  r.details = { other: [{ label: 'Shipping supplies', cents: c(6_412.75) }, { label: 'Marketplace fees', cents: c(11_038.40) }] };
  return r;
}

/** A first year that lost money, with line 32 left unanswered — the case the
    tool has to notice rather than quietly produce a document for. */
export function firstYearLoss() {
  const r = emptyReturn(2025);
  r.business = { name: 'Sable Lane Bakery', activity: 'Baking' };
  r.materiallyParticipated = true;
  r.atRisk = null;
  r.entries = {
    1: c(18_400), 8: c(4_200), 13: c(9_800), '20b': c(14_400), 22: c(6_150), 25: c(2_980), 23: c(410),
  };
  return r;
}

/** Almost nothing filled in. Everything downstream must stay blank rather
    than printing a column of zeros. */
export function sparse() {
  const r = emptyReturn(2025);
  r.business = { name: 'One Line Only' };
  r.entries = { 1: c(1_000) };
  return r;
}

/** Cents chosen so that rounding each figure and adding the rounded ones does
    NOT give the same answer as adding first and rounding once. */
export function roundingTrap() {
  const r = emptyReturn(2025);
  r.business = { name: 'Footing Trap Ltd' };
  r.materiallyParticipated = true;
  r.atRisk = 'all';
  r.entries = { 1: c(10_000) };
  for (const id of ['8', '10', '11', '12', '14', '15', '17', '18', '21', '22']) r.entries[id] = 49; // $0.49 each
  return r;
}

/** A prior year, to prove other expenses move to line 27a and stay there. */
export function priorYear() {
  const r = freelancer();
  r.year = 2023;
  return r;
}

/** Big enough to catch a float, small enough to be a real business somewhere. */
export function large() {
  const r = emptyReturn(2025);
  r.business = { name: 'Large Figures Inc' };
  r.materiallyParticipated = true;
  r.atRisk = 'all';
  r.entries = { 1: 987_654_321_09, 8: 123_456_789_01, 26: 111_111_111_11 };
  return r;
}

export const ALL = { freelancer, reseller, firstYearLoss, sparse, roundingTrap, priorYear, large };

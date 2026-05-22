import { AUTOMATION_STORAGE_KEY, automationStarterPlans } from "./automationGenerator.js";

export function loadSavedAutomationPlans(storage = localStorage) {
  const saved = JSON.parse(storage.getItem(AUTOMATION_STORAGE_KEY) || "[]");
  if (Array.isArray(saved) && saved.length) return saved;
  const starters = automationStarterPlans();
  storage.setItem(AUTOMATION_STORAGE_KEY, JSON.stringify(starters));
  return starters;
}

export function saveAutomationPlans(plans, storage = localStorage) {
  storage.setItem(AUTOMATION_STORAGE_KEY, JSON.stringify(plans));
  return plans;
}

import { STORAGE_KEY, starterProcesses } from "./processGenerator.js";

export function loadSavedProcesses(storage = localStorage) {
  const saved = JSON.parse(storage.getItem(STORAGE_KEY) || "[]");
  if (Array.isArray(saved) && saved.length) return saved;
  const starters = starterProcesses();
  storage.setItem(STORAGE_KEY, JSON.stringify(starters));
  return starters;
}

export function saveProcesses(processes, storage = localStorage) {
  storage.setItem(STORAGE_KEY, JSON.stringify(processes));
  return processes;
}

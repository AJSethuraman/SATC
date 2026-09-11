const state = {
  matches: [],
  replay: null,
  frames: [],
  frameIndex: 0,
  timer: null,
  audioEnabled: false,
  voiceEnabled: false,
  audioContext: null,
  ambienceTimer: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {"Content-Type": "application/json"},
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.remove("hidden");
  window.setTimeout(() => node.classList.add("hidden"), 2600);
}

function ensureAudio() {
  if (!state.audioContext) {
    state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (state.audioContext.state === "suspended") state.audioContext.resume();
  return state.audioContext;
}

function soundCue(kind = "step") {
  if (!state.audioEnabled) return;
  const context = ensureAudio();
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  const now = context.currentTime;
  const settings = {
    step: [95, 0.06, "sine"],
    attack: [145, 0.1, "sawtooth"],
    death: [55, 0.28, "square"],
    crown: [440, 0.45, "sine"],
    lever: [260, 0.18, "triangle"],
  }[kind] || [100, 0.05, "sine"];
  oscillator.type = settings[2];
  oscillator.frequency.setValueAtTime(settings[0], now);
  if (kind === "death") oscillator.frequency.exponentialRampToValueAtTime(35, now + settings[1]);
  if (kind === "crown") oscillator.frequency.exponentialRampToValueAtTime(880, now + settings[1]);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.055, now + 0.015);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + settings[1]);
  oscillator.connect(gain).connect(context.destination);
  oscillator.start(now);
  oscillator.stop(now + settings[1] + 0.02);
}

function startAmbience() {
  if (!state.audioEnabled || state.ambienceTimer) return;
  ensureAudio();
  soundCue("crown");
  state.ambienceTimer = window.setInterval(() => {
    if (!state.audioEnabled) return;
    const context = ensureAudio();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.value = 42 + Math.random() * 8;
    gain.gain.value = 0.012;
    oscillator.connect(gain).connect(context.destination);
    oscillator.start();
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 2.8);
    oscillator.stop(context.currentTime + 2.9);
  }, 3200);
}

function stopAmbience() {
  if (state.ambienceTimer) window.clearInterval(state.ambienceTimer);
  state.ambienceTimer = null;
}

function speakNarration(text) {
  if (!state.voiceEnabled || !("speechSynthesis" in window) || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.93;
  utterance.pitch = 0.78;
  utterance.volume = 0.85;
  window.speechSynthesis.speak(utterance);
}

function cueRoundEvents(roundNo) {
  const events = state.replay.events.filter((event) => event.round_no === roundNo);
  if (events.some((event) => ["crown_extracted", "crown_unlocked", "crown_taken"].includes(event.event_type))) soundCue("crown");
  else if (events.some((event) => event.event_type === "agent_eliminated")) soundCue("death");
  else if (events.some((event) => event.event_type.includes("attack"))) soundCue("attack");
  else if (events.some((event) => ["seal_activated", "room_sealed"].includes(event.event_type))) soundCue("lever");
  else soundCue("step");
  const narration = events.find((event) => event.event_type === "round_narration");
  if (narration) speakNarration(narration.public_text);
}

async function loadMatches(selectLatest = true) {
  const payload = await api("/api/matches");
  state.matches = payload.matches;
  const picker = $("#matchSelect");
  picker.innerHTML = "";
  if (!state.matches.length) {
    $("#emptyState").classList.remove("hidden");
    $("#arena").classList.add("hidden");
    picker.innerHTML = "<option>No matches yet</option>";
    return;
  }
  $("#emptyState").classList.add("hidden");
  $("#arena").classList.remove("hidden");
  state.matches.forEach((match) => {
    const option = document.createElement("option");
    option.value = match.id;
    option.textContent = `${match.id} · ${match.status}`;
    picker.appendChild(option);
  });
  if (selectLatest) picker.value = state.matches[0].id;
  await loadReplay(picker.value);
}

async function loadReplay(matchId) {
  stopPlayback();
  state.replay = await api(`/api/matches/${encodeURIComponent(matchId)}/replay`);
  const audit = await api(`/api/matches/${encodeURIComponent(matchId)}/audit`);
  const badge = $("#auditBadge");
  badge.textContent = audit.valid ? `VERIFIED · ${audit.entries} RECORDS` : "AUDIT FAILED";
  badge.className = `badge ${audit.valid ? "good" : "hot"}`;

  const endFrames = state.replay.snapshots.filter((shot) =>
    (shot.round_no === 0 && shot.phase === "start") || shot.phase === "end"
  );
  const finalFrame = state.replay.snapshots.find((shot) => shot.phase === "final");
  state.frames = finalFrame ? [...endFrames, finalFrame] : endFrames;
  state.frameIndex = state.frames.length - 1;
  const slider = $("#timeline");
  slider.max = Math.max(0, state.frames.length - 1);
  slider.value = state.frameIndex;
  render();
}

function currentFrame() {
  return state.frames[state.frameIndex] || null;
}

function agentColorIndex(agentId) {
  return state.replay.participants.findIndex((p) => p.manifest.id === agentId);
}

function render() {
  const frame = currentFrame();
  if (!frame) return;
  const world = frame.state;
  $("#ruleset").textContent = state.replay.match.ruleset_version;
  // the seed is withheld while a match is live so nobody can precompute rolls
  $("#seed").textContent = state.replay.match.seed ?? "sealed until final";
  $("#roundLabel").textContent = frame.phase === "final"
    ? `FINAL · ${frame.round_no}`
    : `${frame.round_no} / ${world.max_rounds}`;
  $("#stateHash").textContent = frame.state_hash.slice(0, 16);
  $("#timeline").value = state.frameIndex;

  renderAgents(world);
  renderMap(world);
  renderEvents(frame.round_no);
  renderScores();
  renderPrompts();
}

function renderAgents(world) {
  const container = $("#agentCards");
  container.innerHTML = state.replay.participants.map((participant, index) => {
    const agent = world.agents[participant.manifest.id];
    const hpPercent = Math.max(0, 100 * agent.hp / agent.max_hp);
    return `
      <article class="agent-card ${escapeHtml(agent.status)}">
        <div class="agent-head">
          <div>
            <div class="agent-name">${escapeHtml(agent.name)}</div>
            <div class="agent-build">${escapeHtml(agent.build)} · seat ${index + 1}</div>
          </div>
          <div class="score">${agent.score}<small>POINTS</small></div>
        </div>
        <div class="hp-line">
          <div class="hp-bar"><span style="width:${hpPercent}%"></span></div>
          <div class="hp-text">${agent.hp}/${agent.max_hp} HP</div>
        </div>
        <div class="agent-foot">
          <span>${escapeHtml(world.rooms[agent.room].name)}</span>
          <span>${escapeHtml(agent.status.toUpperCase())}</span>
        </div>
      </article>
    `;
  }).join("");
}

function renderMap(world) {
  const livingRooms = new Set(
    Object.values(world.agents).filter((a) => a.status === "active").map((a) => a.room)
  );
  $$(".room").forEach((roomNode) => {
    const roomId = roomNode.dataset.room;
    roomNode.classList.toggle("active", livingRooms.has(roomId));
    const occupants = roomNode.querySelector(".occupants");
    const agents = Object.values(world.agents).filter((a) => a.room === roomId);
    occupants.innerHTML = agents.map((agent) => {
      const index = agentColorIndex(agent.id);
      return `<span class="occupant" title="${escapeHtml(agent.name)}" style="--agent:var(--agent-${index})">${escapeHtml(agent.name[0])}</span>`;
    }).join("");
  });
  const seals = Object.values(world.seals || {});
  const unlocked = seals.length > 0 && seals.every((status) => status === "active" || status === "voided");
  const vaultBadge = $("#vaultStatus");
  vaultBadge.textContent = unlocked ? "OPEN" : "SEALED";
  vaultBadge.className = `badge ${unlocked ? "good" : "hot"}`;
  $("#monsterRow").innerHTML = Object.values(world.monsters).map((monster) =>
    `<span class="monster ${monster.hp <= 0 ? "dead" : ""}">${escapeHtml(monster.name)} · ${monster.hp}/${monster.max_hp} HP · ${escapeHtml(world.rooms[monster.room].name)}</span>`
  ).join("");
}

function renderEvents(roundNo) {
  const events = state.replay.events.filter((event) => event.round_no === roundNo);
  const narration = events.find((event) => event.event_type === "round_narration");
  $("#narration").textContent = narration?.public_text ||
    (roundNo === 0 ? "Four rivals cross the threshold." : "The record is silent.");
  $("#eventFeed").innerHTML = events
    .filter((event) => event.event_type !== "round_narration")
    .map((event) => `
      <li class="${event.phase === "dice" ? "dice" : ""}">
        <span class="type">${escapeHtml(event.event_type.replaceAll("_", " "))}</span>
        <span>${escapeHtml(event.public_text)}</span>
      </li>
    `).join("");
}

function renderScores() {
  const participants = [...state.replay.participants].sort(
    (a, b) => (a.placement || 99) - (b.placement || 99)
  );
  $("#scoreboard").innerHTML = participants.map((participant) => {
    const breakdown = state.replay.scores.filter((score) => score.agent_id === participant.manifest.id);
    const summary = breakdown.map((score) => `${score.category.replaceAll("_", " ")} ${score.points > 0 ? "+" : ""}${score.points}`).join(" · ");
    return `
      <div class="score-row">
        <div class="place">${participant.placement ? `#${participant.placement}` : "—"}</div>
        <div><strong>${escapeHtml(participant.manifest.name)}</strong><span>${escapeHtml(summary || "Match in progress")}</span></div>
        <div class="score-total">${participant.final_score ?? "—"}</div>
      </div>`;
  }).join("");
}

function renderPrompts() {
  $("#promptReveal").innerHTML = state.replay.participants.map((participant) => {
    const m = participant.manifest;
    if (!m.system_prompt) {
      return `<details><summary>${escapeHtml(m.name)} · sealed</summary><div class="prompt-content">Prompt reveals after elimination or match completion.</div></details>`;
    }
    return `
      <details>
        <summary>${escapeHtml(m.name)} · ${escapeHtml(m.secret_objective.replaceAll("_", " "))}</summary>
        <div class="prompt-content"><b>SYSTEM PROMPT</b>\n${escapeHtml(m.system_prompt)}\n\n<b>PERSONALITY</b>\n${escapeHtml(m.personality)}\n\n<b>STRATEGY</b>\n${escapeHtml(m.strategy)}\n\n<b>PROMPT HASH</b>\n${escapeHtml(participant.prompt_hash)}</div>
      </details>`;
  }).join("");
}

function step(delta) {
  state.frameIndex = Math.max(0, Math.min(state.frames.length - 1, state.frameIndex + delta));
  render();
  cueRoundEvents(currentFrame()?.round_no ?? 0);
  if (state.frameIndex === state.frames.length - 1) stopPlayback();
}

function startPlayback() {
  if (state.frameIndex >= state.frames.length - 1) state.frameIndex = 0;
  $("#playButton").textContent = "Ⅱ";
  state.timer = window.setInterval(() => step(1), 1500);
  render();
  cueRoundEvents(currentFrame()?.round_no ?? 0);
}

function stopPlayback() {
  if (state.timer) window.clearInterval(state.timer);
  state.timer = null;
  $("#playButton").textContent = "▶";
}

async function runDemo() {
  stopPlayback();
  toast("Agents released. Resolving the dungeon…");
  const result = await api("/api/demo", {
    method: "POST",
    body: JSON.stringify({seed: Math.floor(Math.random() * 1_000_000), provider: "mock"}),
  });
  await loadMatches();
  $("#matchSelect").value = result.match_id;
  await loadReplay(result.match_id);
  toast("Trial complete. Replay verified.");
}

const manifestTemplate = {
  id: "new_agent",
  name: "New Challenger",
  system_prompt: "Play to win while staying in character. Make decisive choices and adapt when another agent changes the board.",
  personality: "Clever, theatrical, and a little dangerous.",
  strategy: "Help open the vault, preserve health, and seize the Crown when a safe opportunity appears.",
  build: "scout",
  secret_objective: "treasure_hoarder",
};

async function openLab() {
  $("#manifestInput").value = JSON.stringify(manifestTemplate, null, 2);
  $("#labMessage").textContent = "";
  await refreshRoster();
  $("#agentLab").showModal();
}

async function refreshRoster() {
  const payload = await api("/api/agents");
  $("#roster").innerHTML = payload.agents.map((agent) =>
    `<label><input type="checkbox" value="${escapeHtml(agent.id)}"> <span>${escapeHtml(agent.name)} <small>(${escapeHtml(agent.manifest.build)})</small></span></label>`
  ).join("") || "<p class='muted'>Run the demo once to seed the sample roster.</p>";
}

async function saveAgent() {
  try {
    const manifest = JSON.parse($("#manifestInput").value);
    await api("/api/agents", {method: "POST", body: JSON.stringify(manifest)});
    $("#labMessage").textContent = "Agent saved.";
    await refreshRoster();
  } catch (error) {
    $("#labMessage").textContent = error.message;
  }
}

async function runRoster() {
  const selected = $$("#roster input:checked").map((input) => input.value);
  if (selected.length < 4 || selected.length > 8) {
    $("#labMessage").textContent = "Select four to eight agents.";
    return;
  }
  $("#labMessage").textContent = "Resolving match…";
  try {
    const result = await api("/api/matches", {
      method: "POST",
      body: JSON.stringify({
        agent_ids: selected,
        seed: Math.floor(Math.random() * 1_000_000),
        provider: "mock",
      }),
    });
    $("#agentLab").close();
    await loadMatches();
    $("#matchSelect").value = result.match_id;
    await loadReplay(result.match_id);
  } catch (error) {
    $("#labMessage").textContent = error.message;
  }
}

$("#matchSelect").addEventListener("change", (event) => loadReplay(event.target.value));
$("#timeline").addEventListener("input", (event) => {
  stopPlayback();
  state.frameIndex = Number(event.target.value);
  render();
});
$("#previousButton").addEventListener("click", () => { stopPlayback(); step(-1); });
$("#nextButton").addEventListener("click", () => { stopPlayback(); step(1); });
$("#playButton").addEventListener("click", () => state.timer ? stopPlayback() : startPlayback());
$("#demoButton").addEventListener("click", runDemo);
$("#emptyDemoButton").addEventListener("click", runDemo);
$("#labButton").addEventListener("click", openLab);
$("#saveAgentButton").addEventListener("click", saveAgent);
$("#runRosterButton").addEventListener("click", runRoster);
$("#audioButton").addEventListener("click", () => {
  state.audioEnabled = !state.audioEnabled;
  $("#audioButton").textContent = state.audioEnabled ? "Audio On" : "Audio Off";
  $("#audioButton").setAttribute("aria-pressed", String(state.audioEnabled));
  if (state.audioEnabled) startAmbience(); else stopAmbience();
});
$("#voiceButton").addEventListener("click", () => {
  state.voiceEnabled = !state.voiceEnabled;
  $("#voiceButton").textContent = state.voiceEnabled ? "Narrator On" : "Narrator Off";
  $("#voiceButton").setAttribute("aria-pressed", String(state.voiceEnabled));
  if (state.voiceEnabled) {
    ensureAudio();
    speakNarration($("#narration").textContent);
  } else if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
});

loadMatches().catch((error) => toast(error.message));

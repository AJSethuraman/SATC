/* ============================================================================
   SATC INTAKE — ENGINE
   ----------------------------------------------------------------------------
   Renders the steps defined in intake-config.js one at a time, keeps the
   answers, and submits them. Questions live in the config; this file should
   rarely need editing.

   The one idea worth knowing: a step's `showIf` decides BOTH whether it is
   rendered AND whether its answer may exist. prune() deletes answers whose
   step no longer applies, and runs to a fixpoint so cascades resolve — remove
   "rental property" and rental_count goes with it, remove the business and its
   whole subtree goes. Visibility and retention cannot drift apart, so a stale
   answer can never reach the payload.

   Depends on: intake-config.js (INTAKE_STEPS) and SATC_CONFIG in index.html.
   ========================================================================== */

(function () {
  'use strict';

  const STEPS  = window.INTAKE_STEPS || [];
  const mount  = document.getElementById('intakeMount');
  if (!mount || !STEPS.length) return;

  const STORAGE_KEY = 'satc_intake_v1';

  const state = {
    answers:   {},
    currentId: STEPS[0].id,
    submitting: false,
    moved:     false,   // suppresses focus-stealing on first paint
    back:      false,   // last move was backwards (lets the progress bar recede)
    pct:       0,
  };

  /* ---------------------------------------------------------------- state */

  const KNOWN_IDS = new Set(STEPS.map(s => s.id));

  /**
   * Delete answers that may no longer exist. Two passes:
   *
   *  1. Orphans — answers whose step id is not in the config at all. A restored
   *     session predates an edit to intake-config.js, and without this they
   *     would ride along into the payload forever, invisible to every showIf.
   *  2. Inapplicable — answers whose step's showIf no longer passes. Loops to a
   *     fixpoint, because removing one answer can strand a step downstream of
   *     it (drop rentals -> rental_count goes; drop the business -> structure,
   *     entity_count, complexity and headcount all go).
   *
   * A showIf that throws is treated as "does not apply", so one bad predicate
   * cannot wedge the form.
   */
  function prune() {
    for (const key of Object.keys(state.answers)) {
      if (!KNOWN_IDS.has(key)) delete state.answers[key];
    }
    let changed = true;
    while (changed) {
      changed = false;
      for (const step of STEPS) {
        if (!step.showIf || !(step.id in state.answers)) continue;
        let applies;
        try { applies = step.showIf(state.answers); } catch (e) { applies = false; }
        if (!applies) { delete state.answers[step.id]; changed = true; }
      }
    }
  }

  const visible = () => STEPS.filter(s => {
    if (!s.showIf) return true;
    try { return !!s.showIf(state.answers); } catch (e) { return false; }
  });

  /** Answers restored from storage are untrusted — shape them or drop them. */
  function coerce(answers) {
    const clean = {};
    for (const step of STEPS) {
      const v = answers[step.id];
      if (v === undefined || v === null) continue;
      if (step.type === 'multi') {
        if (Array.isArray(v)) {
          const valid = v.filter(x => step.options.some(o => o.value === x));
          if (valid.length) clean[step.id] = valid;
        }
      } else if (step.type === 'single') {
        if (typeof v === 'string' && step.options.some(o => o.value === v)) clean[step.id] = v;
      } else if (step.type === 'text' || step.type === 'textarea') {
        if (typeof v === 'string' && v.trim()) clean[step.id] = v;
      } else if (step.type === 'contact') {
        if (v && typeof v === 'object' && !Array.isArray(v)) {
          clean[step.id] = {
            name: str(v.name), email: str(v.email), phone: str(v.phone),
            preferred: str(v.preferred), location: str(v.location), consent: !!v.consent,
          };
        }
      }
    }
    return clean;
  }

  const str = v => (typeof v === 'string' ? v : '');
  const indexOfCurrent = () => visible().findIndex(s => s.id === state.currentId);

  function save() {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
        answers: state.answers, currentId: state.currentId,
      }));
    } catch (e) { /* private mode — carry on without resume */ }
  }

  function restore() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (saved && saved.answers && typeof saved.answers === 'object') {
        state.answers = coerce(saved.answers);      // wrong types can't reach render()
        prune();                                    // config may have changed since
        const still = visible().some(s => s.id === saved.currentId);
        if (still) state.currentId = saved.currentId;
      }
    } catch (e) {
      state.answers = {};                           // corrupt payload — start fresh
      clearSaved();
    }
  }

  function clearSaved() {
    try { sessionStorage.removeItem(STORAGE_KEY); } catch (e) {}
  }

  /**
   * Back to a blank form. Answers survive reloads by design, so without this
   * there is no way out of a half-filled form and the thank-you screen is a
   * dead end. Confirms first when there is work to lose — but not when the
   * form is already empty, and not after a send, when nothing is at stake.
   */
  function reset(force) {
    if (!force && Object.keys(state.answers).length &&
        !window.confirm('Start over? This clears everything you’ve entered.')) return;
    state.answers = {};
    state.currentId = STEPS[0].id;
    state.submitting = false;
    state.back = false;
    state.pct = 0;
    state.moved = true;
    clearSaved();
    render();
  }

  /* ----------------------------------------------------------- label help */

  const titleCase = id =>
    id.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());

  const labelOf = step => step.label || titleCase(step.id);

  /** Map stored value(s) back to their human option labels. */
  function readable(step, value) {
    if (!step.options) return String(value);
    const list = Array.isArray(value) ? value : [value];
    return list
      .map(v => {
        const opt = step.options.find(o => o.value === v);
        return opt ? opt.label : v;
      })
      .join(', ');
  }

  /* -------------------------------------------------------------- markup */

  const esc = s => String(s).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));

  function controlsFor(step) {
    const a = state.answers[step.id];

    if (step.type === 'multi' || step.type === 'single') {
      // Rendered as chips, but each one is still a real checkbox/radio inside
      // its label — visually hidden, not replaced. Buttons with aria-pressed
      // would look identical and lose checked-state announcement, arrow-key
      // movement within a radio group, and the input:checked reads in collect().
      const inputType = step.type === 'multi' ? 'checkbox' : 'radio';
      const chosen = step.type === 'multi' ? (a || []) : (a ? [a] : []);
      const role = step.type === 'multi' ? 'group' : 'radiogroup';
      return '<div class="chips" role="' + role + '" ' +
             'aria-label="' + esc(step.question) + '">' + step.options.map(o => {
        const on = chosen.indexOf(o.value) !== -1;
        return '<label class="chip' + (on ? ' on' : '') + '">' +
          '<input type="' + inputType + '" name="' + esc(step.id) + '" ' +
                 'value="' + esc(o.value) + '"' + (on ? ' checked' : '') +
                 (o.exclusive ? ' data-exclusive="1"' : '') + ' />' +
          '<span>' + esc(o.label) + '</span>' +
        '</label>';
      }).join('') + '</div>';
    }

    if (step.type === 'text') {
      return '<label class="field"><span class="sr-only">' + esc(step.question) + '</span>' +
        '<input type="text" name="' + esc(step.id) + '" value="' + esc(a || '') + '" ' +
        'placeholder="' + esc(step.placeholder || '') + '" /></label>';
    }

    if (step.type === 'textarea') {
      return '<label class="field"><span class="sr-only">' + esc(step.question) + '</span>' +
        '<textarea name="' + esc(step.id) + '" rows="5" ' +
        'placeholder="' + esc(step.placeholder || '') + '">' + esc(a || '') + '</textarea></label>';
    }

    if (step.type === 'contact') {
      const c = a || {};
      return '' +
        '<div class="two">' +
          field('Full name', 'name',  'text',  c.name,  'name',  true) +
          field('Email',     'email', 'email', c.email, 'email', true) +
        '</div>' +
        '<div class="two">' +
          field('Phone', 'phone', 'tel', c.phone, 'tel') +
          '<label class="field"><span class="lab">Best way to reach you</span>' +
            '<select name="preferred">' +
              ['', 'Email', 'Phone call', 'Text message'].map(v =>
                '<option' + (c.preferred === v ? ' selected' : '') + '>' + (v || 'Select…') + '</option>'
              ).join('') +
            '</select>' +
          '</label>' +
        '</div>' +
        field('City & state', 'location', 'text', c.location, 'address-level2') +
        '<div class="consent"><label class="check">' +
          '<input type="checkbox" name="consent"' + (c.consent ? ' checked' : '') + ' />' +
          '<span>I understand that sending this does not create ' +
          'a client engagement. SATC is engaged only when we both sign an engagement letter.</span>' +
        '</label></div>';
    }

    return '';
  }

  function field(label, name, type, value, autocomplete, required) {
    return '<label class="field"><span class="lab">' + esc(label) +
      (required ? ' <span class="req">*</span>' : '') + '</span>' +
      '<input type="' + type + '" name="' + esc(name) + '" value="' + esc(value || '') + '"' +
      (required ? ' required aria-required="true"' : '') +
      (autocomplete ? ' autocomplete="' + autocomplete + '"' : '') + ' /></label>';
  }

  /* -------------------------------------------------------------- render */

  function render() {
    const steps = visible();
    let i = indexOfCurrent();
    if (i === -1) { state.currentId = steps[0].id; i = 0; }
    const step = steps[i];

    // The denominator grows as answers reveal more steps, so a raw
    // position/total ratio can move BACKWARDS while going forwards (25% on
    // step 1 -> 20% on step 2). Let it fall only when the user goes back.
    const raw = Math.round(((i + 1) / steps.length) * 100);
    state.pct = state.back ? raw : Math.max(state.pct, raw);
    state.back = false;
    const pct = state.pct;

    mount.innerHTML =
      '<div class="wiz-bar" role="presentation"><span style="width:' + pct + '%"></span></div>' +
      // Only offered once there is something to clear, and kept quiet: it is an
      // escape hatch sitting next to the primary flow, not a peer of Continue.
      (Object.keys(state.answers).length
        ? '<p class="wiz-reset"><button type="button" class="linkish" data-reset>Start over</button></p>'
        : '') +
      '<form class="wiz-form" id="intakeForm" novalidate>' +
        '<fieldset class="wiz-step">' +
          '<legend class="wiz-q">' + esc(step.question) + '</legend>' +
          (step.help ? '<p class="fs-note">' + esc(step.help) + '</p>' : '') +
          // Chips look identical whether one or many may be picked, so say which.
          (step.type === 'multi'  ? '<p class="wiz-hint">Select all that apply</p>' :
           step.type === 'single' ? '<p class="wiz-hint">Choose one</p>' : '') +
          controlsFor(step) +
        '</fieldset>' +
        '<input type="text" name="_gotcha" tabindex="-1" autocomplete="off" aria-hidden="true" ' +
          'style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0;" />' +
        '<p class="form-status" id="formStatus" role="status" aria-live="polite"></p>' +
        '<div class="wiz-nav">' +
          (i > 0 ? '<button type="button" class="btn-link" data-back>Back</button>' : '<span></span>') +
          '<button type="submit" class="btn gold">' +
            (i === steps.length - 1 ? 'Send to SATC' : 'Continue') +
          '</button>' +
        '</div>' +
      '</form>';

    const resetBtn = mount.querySelector('[data-reset]');
    if (resetBtn) resetBtn.addEventListener('click', () => reset(false));

    wire(step);

    if (state.moved) {
      const first = mount.querySelector('input:not([name="_gotcha"]), textarea, select');
      if (first) first.focus({ preventScroll: true });
      const top = mount.getBoundingClientRect().top + window.scrollY - 90;
      if (window.scrollY > top) window.scrollTo({ top: top, behavior: 'smooth' });
    }
  }

  function wire(step) {
    const form = document.getElementById('intakeForm');

    // "None of these" clears the rest, and the rest clear it.
    if (step.type === 'multi') {
      form.querySelectorAll('input[type=checkbox][name="' + step.id + '"]').forEach(box => {
        box.addEventListener('change', () => {
          if (!box.checked) return;
          const isExclusive = box.hasAttribute('data-exclusive');
          form.querySelectorAll('input[type=checkbox][name="' + step.id + '"]').forEach(other => {
            if (other === box) return;
            const otherExclusive = other.hasAttribute('data-exclusive');
            if (isExclusive || otherExclusive) other.checked = false;
          });
        });
      });
    }

    // The chip carries the visual state; its input carries the real state. Sync
    // on the bubbled change so this runs AFTER the exclusive handler above has
    // cleared any inputs programmatically (which fires no change event itself).
    if (step.type === 'multi' || step.type === 'single') {
      const syncChips = () => {
        form.querySelectorAll('.chip').forEach(label => {
          const input = label.querySelector('input');
          if (input) label.classList.toggle('on', input.checked);
        });
      };
      form.addEventListener('change', syncChips);
      syncChips();
    }

    // Persist as they go. Saving only on navigation meant a reload mid-step
    // silently discarded whatever was on screen, including the whole contact
    // block after a failed send.
    const persist = () => { collect(step); save(); };
    form.addEventListener('input', persist);
    form.addEventListener('change', persist);

    const back = form.querySelector('[data-back]');
    if (back) back.addEventListener('click', () => {
      collect(step);                 // keep what they typed before stepping away
      const steps = visible();
      const i = indexOfCurrent();
      if (i > 0) {
        state.currentId = steps[i - 1].id;
        state.moved = true;
        state.back = true;
        save();
        render();
      }
    });

    form.addEventListener('submit', e => { e.preventDefault(); advance(step); });
  }

  /* ------------------------------------------------------- collect + move */

  function collect(step) {
    const form = document.getElementById('intakeForm');
    if (!form) return;

    if (step.type === 'multi') {
      const picked = Array.from(
        form.querySelectorAll('input[name="' + step.id + '"]:checked')
      ).map(el => el.value);
      if (picked.length) state.answers[step.id] = picked;
      else delete state.answers[step.id];

    } else if (step.type === 'single') {
      const el = form.querySelector('input[name="' + step.id + '"]:checked');
      if (el) state.answers[step.id] = el.value;
      else delete state.answers[step.id];

    } else if (step.type === 'text' || step.type === 'textarea') {
      const el = form.querySelector('[name="' + step.id + '"]');
      const v = el ? el.value.trim() : '';
      if (v) state.answers[step.id] = v;
      else delete state.answers[step.id];

    } else if (step.type === 'contact') {
      const get = n => {
        const el = form.querySelector('[name="' + n + '"]');
        return el ? (el.type === 'checkbox' ? el.checked : el.value.trim()) : '';
      };
      state.answers.contact = {
        name: get('name'), email: get('email'), phone: get('phone'),
        preferred: get('preferred') === 'Select…' ? '' : get('preferred'),
        location: get('location'), consent: get('consent'),
      };
    }

    prune();   // an earlier answer may have just invalidated a later one
  }

  function validate(step) {
    const a = state.answers[step.id];

    if (step.type === 'contact') {
      const c = a || {};
      if (!c.name)  return 'Please add your name.';
      if (!c.email) return 'Please add an email.';
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(c.email))
        return 'That email address doesn’t look right.';
      if (!c.consent) return 'Please tick the acknowledgement before sending.';
      return null;
    }

    if (!step.required) return null;

    if (step.type === 'multi')  return (a && a.length) ? null : 'Pick at least one to continue.';
    if (step.type === 'single') return a ? null : 'Choose one to continue.';
    return a ? null : 'Please fill this in to continue.';
  }

  function status(msg, isError) {
    const el = document.getElementById('formStatus');
    if (!el) return;
    el.className = 'form-status' + (isError ? ' err' : '');
    el.textContent = msg || '';
  }

  function advance(step) {
    collect(step);
    const problem = validate(step);
    if (problem) { status(problem, true); return; }

    const steps = visible();
    const i = indexOfCurrent();

    if (i < steps.length - 1) {
      state.currentId = steps[i + 1].id;
      state.moved = true;
      save();
      render();
    } else {
      submit();
    }
  }

  /* -------------------------------------------------------------- submit */

  /** Readable "Label: value" lines, in step order, for the notification email. */
  function summary() {
    const lines = [];
    for (const step of visible()) {
      const a = state.answers[step.id];
      if (a === undefined || a === null || a === '') continue;
      if (step.type === 'contact') {
        if (a.phone)     lines.push('Phone: ' + a.phone);
        if (a.preferred) lines.push('Preferred contact: ' + a.preferred);
        if (a.location)  lines.push('Location: ' + a.location);
      } else {
        lines.push(labelOf(step) + ': ' + readable(step, a));
      }
    }
    return lines;
  }

  function submit() {
    if (state.submitting) return;                    // no double-fire on fast clicks

    const form = document.getElementById('intakeForm');
    const btn  = form.querySelector('button[type=submit]');

    // Honeypot check BEFORE anything is disabled. Doing it after left a tripped
    // form stuck on "Sending…" forever with no way back.
    const gotcha = form.querySelector('[name="_gotcha"]');
    if (gotcha && gotcha.value !== '') { done(); return; }

    state.submitting = true;
    if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }

    const cfg   = window.SATC_CONFIG || { contact: {} };
    const email = cfg.contact.email;
    const fid   = cfg.contact.formspreeId;
    const c     = state.answers.contact || {};

    const payload = new FormData();
    payload.set('Name',  c.name);
    payload.set('Email', c.email);
    summary().forEach(line => {
      const at = line.indexOf(': ');
      payload.append(line.slice(0, at), line.slice(at + 2));
    });
    payload.set('_subject',  'New intake — ' + c.name);
    payload.set('_replyto',  c.email);
    payload.set('_gotcha',   '');   // Formspree runs its own check on this field
    // Single-line normalized copy, so a Power Automate / Apps Script flow can
    // turn a submission into a spreadsheet row without parsing prose.
    payload.set('_json', JSON.stringify(state.answers));

    if (!fid) {
      // summary() covers the questions but deliberately skips the contact
      // name/email, which the Formspree path sets as its own fields — so the
      // mailto body has to add them back or the enquiry has no reply address.
      const body = ['Name: ' + c.name, 'Email: ' + c.email]
        .concat(summary())
        .join('\n') + '\n\n— sent from the SATC website';
      window.location.href = 'mailto:' + (email || '') +
        '?subject=' + encodeURIComponent('New intake — ' + c.name) +
        '&body='    + encodeURIComponent(body);
      status('Opening your email app — press send to finish.');
      state.submitting = false;
      if (btn) { btn.disabled = false; btn.textContent = 'Send to SATC'; }
      return;
    }

    fetch('https://formspree.io/f/' + fid, {
      method: 'POST', body: payload, headers: { Accept: 'application/json' },
    })
      .then(res => {
        if (!res.ok) throw new Error('rejected');
        clearSaved();
        done();
      })
      .catch(() => {
        state.submitting = false;
        if (btn) { btn.disabled = false; btn.textContent = 'Send to SATC'; btn.focus(); }
        status('That didn’t go through. Please email ' + (email || 'us') +
               ' and we’ll pick it up from there.', true);
      });
  }

  function done() {
    mount.innerHTML =
      '<div class="intake-done">' +
        '<h3>Thanks — that’s everything for now.</h3>' +
        '<p>We’ll read it and be in touch to set up a time.</p>' +
        // No confirm here: the answers are already sent, so there is nothing to lose.
        '<p class="done-again"><button type="button" class="linkish" data-restart>' +
        'Send another</button></p>' +
      '</div>';
    const again = mount.querySelector('[data-restart]');
    if (again) again.addEventListener('click', () => reset(true));
    mount.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  /* ---------------------------------------------------------------- boot */

  restore();
  render();
})();

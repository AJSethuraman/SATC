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
  };

  /* ---------------------------------------------------------------- state */

  /**
   * Delete answers whose step no longer applies. Loops until nothing changes,
   * because removing one answer can strand a step that depended on it.
   */
  function prune() {
    let changed = true;
    while (changed) {
      changed = false;
      for (const step of STEPS) {
        if (step.showIf && !step.showIf(state.answers) && step.id in state.answers) {
          delete state.answers[step.id];
          changed = true;
        }
      }
    }
  }

  const visible = () => STEPS.filter(s => !s.showIf || s.showIf(state.answers));
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
      if (saved && typeof saved.answers === 'object') {
        state.answers = saved.answers || {};
        prune();                                    // config may have changed since
        const still = visible().some(s => s.id === saved.currentId);
        if (still) state.currentId = saved.currentId;
      }
    } catch (e) { /* corrupt payload — start fresh */ }
  }

  function clearSaved() {
    try { sessionStorage.removeItem(STORAGE_KEY); } catch (e) {}
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
      const inputType = step.type === 'multi' ? 'checkbox' : 'radio';
      const chosen = step.type === 'multi' ? (a || []) : (a ? [a] : []);
      const cols = step.options.length > 6 ? '' : ' one-col';
      return '<div class="checks' + cols + '" role="group">' + step.options.map((o, i) => {
        const on = chosen.indexOf(o.value) !== -1;
        return '<label class="check">' +
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
          '<span>I understand that sending this starts a conversation and does not create ' +
          'a client engagement. SATC is engaged only when we both sign an engagement letter. ' +
          'See our <a href="privacy.html">Privacy Policy</a> and <a href="terms.html">Terms</a>.</span>' +
        '</label></div>';
    }

    return '';
  }

  function field(label, name, type, value, autocomplete, required) {
    return '<label class="field"><span class="lab">' + esc(label) +
      (required ? ' <span class="req">*</span>' : '') + '</span>' +
      '<input type="' + type + '" name="' + esc(name) + '" value="' + esc(value || '') + '"' +
      (autocomplete ? ' autocomplete="' + autocomplete + '"' : '') + ' /></label>';
  }

  /* -------------------------------------------------------------- render */

  function render() {
    const steps = visible();
    let i = indexOfCurrent();
    if (i === -1) { state.currentId = steps[0].id; i = 0; }
    const step = steps[i];
    const pct = Math.round(((i + 1) / steps.length) * 100);

    mount.innerHTML =
      '<div class="wiz-bar" role="presentation"><span style="width:' + pct + '%"></span></div>' +
      '<form class="wiz-form" id="intakeForm" novalidate>' +
        '<fieldset class="wiz-step">' +
          '<legend class="wiz-q">' + esc(step.question) + '</legend>' +
          (step.help ? '<p class="fs-note">' + esc(step.help) + '</p>' : '') +
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

    const back = form.querySelector('[data-back]');
    if (back) back.addEventListener('click', () => {
      collect(step);                 // keep what they typed before stepping away
      const steps = visible();
      const i = indexOfCurrent();
      if (i > 0) { state.currentId = steps[i - 1].id; state.moved = true; save(); render(); }
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
      if (!c.name)  return 'Please add your name so we know who we’re talking to.';
      if (!c.email) return 'Please add an email so we can reply.';
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(c.email))
        return 'That email address doesn’t look right — mind checking it?';
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
    state.submitting = true;

    const form = document.getElementById('intakeForm');
    const btn  = form.querySelector('button[type=submit]');
    if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }

    const gotcha = form.querySelector('[name="_gotcha"]');
    if (gotcha && gotcha.value !== '') { state.submitting = false; return; }   // bot

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
    // Single-line normalized copy, so a Power Automate / Apps Script flow can
    // turn a submission into a spreadsheet row without parsing prose.
    payload.set('_json', JSON.stringify(state.answers));

    if (!fid) {
      const body = summary().join('\n') + '\n\n— sent from the SATC website';
      window.location.href = 'mailto:' + email +
        '?subject=' + encodeURIComponent('New intake — ' + c.name) +
        '&body='    + encodeURIComponent(body);
      status('Opening your email app — press send and it’s on its way.');
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
        if (btn) { btn.disabled = false; btn.textContent = 'Send to SATC'; }
        status('That didn’t go through. Please email ' + email +
               ' and we’ll pick it up from there.', true);
      });
  }

  function done() {
    mount.innerHTML =
      '<div class="intake-done">' +
        '<h3>Thank you — that’s everything we need for now.</h3>' +
        '<p>Arjun will read this personally and reply within one business day. ' +
        'If we need documents from you, that reply will include a secure upload ' +
        'link — we’ll never ask you to email or text them.</p>' +
      '</div>';
    mount.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  /* ---------------------------------------------------------------- boot */

  restore();
  render();
})();

/* The page.

   Built from the line table rather than hand-written, so a form field cannot
   exist that the engine does not know about, and a line cannot be added to the
   table without appearing on the page.

   Three things here are deliberate and easily lost:

   1. A field that has never been touched stays empty. It is never given a
      helpful 0, because the whole document depends on blank meaning blank.
   2. Bad input is refused where it was typed, next to the field, and the total
      simply does not move. The tool never quietly reads "12.345" as 12.34.
   3. Nothing is remembered unless the person ticks the box that says so. The
      warning next to that box is about the library computer, and it means it. */

import { parseMoney, formatCents, formatDollars } from './money.mjs';
import { compute, emptyReturn } from './engine.mjs';
import { loadYear, supportedYears } from './years.mjs';
import { mileage, simplifiedHomeOffice, mealsHalf, netPurchases, REFUSALS } from './helpers.mjs';
import { pdfFor, xlsxFor, FIRM } from './document.mjs';
import { EXPENSE_LINES, COGS_LINES } from './lines.mjs';

const STORAGE_KEY = 'satc.schedule-c.draft.v1';
const HANDOFF = 'https://satcllp.com/?from=schedule-c#intake';

const el = (tag, attrs = {}, kids = []) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? '' : String(v));
  }
  for (const kid of [].concat(kids)) if (kid) node.append(kid);
  return node;
};

export function start(root) {
  const state = {
    ret: emptyReturn(2025),
    raw: {},          // what is literally in each box, so a refusal is visible
    errors: {},
    otherRows: [{ label: '', raw: '' }],
    remember: false,
    include: 'both',
    showCogs: false,
  };

  restore(state);

  const summary = el('aside', { class: 'summary', id: 'summary' });
  const form = el('form', { class: 'sheet', autocomplete: 'off', onsubmit: (e) => e.preventDefault() });
  root.append(form, summary);

  // ── reading and writing the state ───────────────────────────────────
  function setMoney(id, text) {
    state.raw[id] = text;
    const parsed = parseMoney(text);
    if (!parsed.ok) { state.errors[id] = parsed.error; delete state.ret.entries[id]; }
    else {
      delete state.errors[id];
      if (parsed.cents === null) delete state.ret.entries[id];
      else state.ret.entries[id] = parsed.cents;
    }
    refresh();
  }

  function syncOtherRows() {
    const rows = [];
    for (const row of state.otherRows) {
      const parsed = parseMoney(row.raw);
      if (parsed.ok && parsed.cents !== null) rows.push({ label: row.label.trim() || 'Other', cents: parsed.cents });
    }
    state.ret.details = rows.length ? { other: rows } : {};
  }

  // ── the form ────────────────────────────────────────────────────────
  function moneyField(id, label, hint, helper) {
    const input = el('input', {
      type: 'text', inputmode: 'decimal', id: `f${id}`, value: state.raw[id] || '',
      'aria-describedby': `h${id}`,
      oninput: (e) => setMoney(id, e.target.value),
    });
    const error = el('p', { class: 'error', id: `e${id}`, role: 'alert' });
    const field = el('div', { class: 'field' }, [
      el('label', { for: `f${id}` }, [
        el('span', { class: 'line-no', text: id }),
        el('span', { class: 'line-label', text: label }),
      ]),
      el('div', { class: 'entry' }, [el('span', { class: 'currency', text: '$' }), input]),
      hint ? el('p', { class: 'hint', id: `h${id}`, text: hint }) : null,
      error,
      helper || null,
    ]);
    field.dataset.line = id;
    return field;
  }

  function helperBox(title, build) {
    const out = el('p', { class: 'helper-out' });
    const box = el('details', { class: 'helper' }, [el('summary', { text: title })]);
    build(box, out);
    box.append(out);
    return box;
  }

  function mileageHelper() {
    return helperBox('Work it out from miles', (box, out) => {
      const input = el('input', { type: 'text', inputmode: 'numeric', 'aria-label': 'Business miles' });
      const apply = el('button', { type: 'button', class: 'ghost', text: 'Use this figure' });
      const run = () => {
        const y = loadYear(state.ret.year);
        const r = mileage({ miles: input.value.replace(/[\s,]/g, ''), yearData: y });
        if (!r.ok) { out.textContent = r.error; apply.disabled = true; return null; }
        out.textContent = `${formatDollars(r.cents)} — ${r.basis}. Source: ${r.cite}.`;
        apply.disabled = false;
        return r;
      };
      input.addEventListener('input', run);
      apply.addEventListener('click', () => {
        const r = run();
        if (!r) return;
        const miles = Number(input.value.replace(/[\s,]/g, ''));
        state.ret.vehicle.businessMiles = miles;
        setMoney('9', formatCents(r.cents));
        document.getElementById('f9').value = formatCents(r.cents);
        // Line 44a asks for the same miles. Fill it in rather than making the
        // person type them twice and risk two different answers.
        const milesField = document.getElementById('businessMiles');
        if (milesField) milesField.value = String(miles);
      });
      box.append(
        el('p', { class: 'hint', text: 'Only if you are using the standard mileage rate. If you are claiming what the vehicle actually cost you, enter that figure instead — this tool does not work that out.' }),
        el('div', { class: 'helper-row' }, [input, apply]),
      );
    });
  }

  function mealsHelper() {
    return helperBox('Take half of what I spent', (box, out) => {
      const input = el('input', { type: 'text', inputmode: 'decimal', 'aria-label': 'Total spent on meals' });
      const apply = el('button', { type: 'button', class: 'ghost', text: 'Use this figure' });
      const run = () => {
        const parsed = parseMoney(input.value);
        if (!parsed.ok || parsed.cents === null) { out.textContent = parsed.error || ''; apply.disabled = true; return null; }
        const r = mealsHalf({ spentCents: parsed.cents, yearData: loadYear(state.ret.year) });
        out.textContent = `${formatDollars(r.cents)} — ${r.basis}. ${r.caveat}`;
        apply.disabled = false;
        return r;
      };
      input.addEventListener('input', run);
      apply.addEventListener('click', () => {
        const r = run();
        if (!r) return;
        setMoney('24b', formatCents(r.cents));
        document.getElementById('f24b').value = formatCents(r.cents);
      });
      box.append(el('div', { class: 'helper-row' }, [input, apply]));
    });
  }

  function homeHelper() {
    return helperBox('Work it out from the square feet', (box, out) => {
      const input = el('input', { type: 'text', inputmode: 'numeric', 'aria-label': 'Square feet used for business' });
      const apply = el('button', { type: 'button', class: 'ghost', text: 'Use this figure' });
      const run = () => {
        const r = simplifiedHomeOffice({ sqft: input.value.replace(/[\s,]/g, ''), yearData: loadYear(state.ret.year) });
        if (!r.ok) { out.textContent = r.error; apply.disabled = true; return null; }
        out.textContent = `${formatDollars(r.cents)} — ${r.basis}. Source: ${r.cite}.`;
        apply.disabled = false;
        return r;
      };
      input.addEventListener('input', run);
      apply.addEventListener('click', () => {
        const r = run();
        if (!r) return;
        state.ret.homeOfficeMethod = 'simplified';
        setMoney('30', formatCents(r.cents));
        document.getElementById('f30').value = formatCents(r.cents);
      });
      box.append(
        el('p', { class: 'hint', text: 'This is the square-foot method. If you worked yours out the detailed way on Form 8829, enter that figure instead.' }),
        el('div', { class: 'helper-row' }, [input, apply]),
      );
    });
  }

  function purchasesHelper() {
    return helperBox('Take off what I used myself', (box, out) => {
      const bought = el('input', { type: 'text', inputmode: 'decimal', 'aria-label': 'What you bought' });
      const own = el('input', { type: 'text', inputmode: 'decimal', 'aria-label': 'What you took for yourself' });
      const apply = el('button', { type: 'button', class: 'ghost', text: 'Use this figure' });
      const run = () => {
        const a = parseMoney(bought.value); const b = parseMoney(own.value);
        if (!a.ok || a.cents === null) { out.textContent = a.error || ''; apply.disabled = true; return null; }
        const r = netPurchases({ purchasesCents: a.cents, personalUseCents: b.ok ? b.cents : 0 });
        out.textContent = `${formatDollars(r.cents)} — ${r.basis}.`;
        apply.disabled = false;
        return r;
      };
      bought.addEventListener('input', run); own.addEventListener('input', run);
      apply.addEventListener('click', () => {
        const r = run();
        if (!r) return;
        setMoney('36', formatCents(r.cents));
        document.getElementById('f36').value = formatCents(r.cents);
      });
      box.append(el('div', { class: 'helper-row' }, [bought, own, apply]));
    });
  }

  function section(title, blurb, kids) {
    return el('section', { class: 'block' }, [
      el('h2', { text: title }),
      blurb ? el('p', { class: 'blurb', text: blurb }) : null,
      ...kids,
    ]);
  }

  function choice(name, label, options, get, set) {
    return el('fieldset', { class: 'choice' }, [
      el('legend', { text: label }),
      ...options.map(([value, text]) => {
        const input = el('input', {
          type: 'radio', name, id: `${name}-${value}`, value,
          checked: get() === value,
          onchange: () => { set(value); refresh(); },
        });
        return el('label', { class: 'radio', for: `${name}-${value}` }, [input, el('span', { text })]);
      }),
    ]);
  }

  function otherExpensesBlock() {
    const list = el('div', { class: 'rows' });
    const draw = () => {
      list.replaceChildren();
      state.otherRows.forEach((row, i) => {
        const label = el('input', {
          type: 'text', value: row.label, 'aria-label': `What it was, item ${i + 1}`, placeholder: 'What it was',
          oninput: (e) => { row.label = e.target.value; syncOtherRows(); refresh(); },
        });
        const amount = el('input', {
          type: 'text', inputmode: 'decimal', value: row.raw, 'aria-label': `Amount, item ${i + 1}`, placeholder: '0.00',
          oninput: (e) => { row.raw = e.target.value; syncOtherRows(); refresh(); },
        });
        const remove = el('button', {
          type: 'button', class: 'ghost', text: 'Remove', 'aria-label': `Remove item ${i + 1}`,
          onclick: () => {
            state.otherRows.splice(i, 1);
            if (!state.otherRows.length) state.otherRows.push({ label: '', raw: '' });
            syncOtherRows(); draw(); refresh();
          },
        });
        list.append(el('div', { class: 'row' }, [label, el('div', { class: 'entry' }, [el('span', { class: 'currency', text: '$' }), amount]), remove]));
      });
    };
    draw();
    return section('Anything else you spent money on', 'Things with no line of their own — software, bank charges, a licence. Schedule C has room for nine; more than that goes on an attached list.', [
      list,
      el('button', {
        type: 'button', class: 'ghost', text: 'Add another',
        onclick: () => { state.otherRows.push({ label: '', raw: '' }); draw(); refresh(); },
      }),
    ]);
  }

  function buildForm() {
    const y = loadYear(state.ret.year);
    const L = (id) => y.byId.get(id).plLabel;
    form.replaceChildren();

    form.append(section('Which year, and whose business', null, [
      el('div', { class: 'field' }, [
        el('label', { for: 'year', text: 'Tax year' }),
        el('select', {
          id: 'year',
          onchange: (e) => { state.ret.year = Number(e.target.value); buildForm(); refresh(); },
        }, supportedYears().map((yr) => el('option', { value: yr, selected: yr === state.ret.year, text: String(yr) }))),
      ]),
      el('div', { class: 'field' }, [
        el('label', { for: 'bizname', text: 'Business name (goes at the top of the page)' }),
        el('input', { type: 'text', id: 'bizname', value: state.ret.business.name, oninput: (e) => { state.ret.business.name = e.target.value; refresh(); } }),
      ]),
      el('div', { class: 'field' }, [
        el('label', { for: 'bizwhat', text: 'What the business does' }),
        el('input', { type: 'text', id: 'bizwhat', value: state.ret.business.activity, oninput: (e) => { state.ret.business.activity = e.target.value; refresh(); } }),
      ]),
      choice('method', 'How you count income', [['cash', 'When the money arrives'], ['accrual', 'When the work is done'], ['other', 'Something else']],
        () => state.ret.accountingMethod, (v) => { state.ret.accountingMethod = v; }),
      choice('participate', 'Did you work in this business regularly through the year?', [['yes', 'Yes'], ['no', 'No']],
        () => (state.ret.materiallyParticipated === null ? '' : state.ret.materiallyParticipated ? 'yes' : 'no'),
        (v) => { state.ret.materiallyParticipated = v === 'yes'; }),
    ]));

    form.append(section('Money coming in', 'What the business took, before you take anything off it.', [
      moneyField('1', L('1'), 'Everything the business was paid, including what came on a 1099.'),
      moneyField('2', L('2'), 'Refunds and credits you gave customers.'),
      moneyField('6', L('6'), 'Anything else the business earned that is not a sale.'),
    ]));

    const cogsToggle = el('label', { class: 'toggle' }, [
      el('input', {
        type: 'checkbox', checked: state.showCogs,
        onchange: (e) => { state.showCogs = e.target.checked; buildForm(); refresh(); },
      }),
      el('span', { text: 'I buy or make things to sell, and I count stock' }),
    ]);
    const cogsFields = state.showCogs
      ? [...COGS_LINES.map((id) => moneyField(id, L(id), null, id === '36' ? purchasesHelper() : null)), moneyField('41', L('41'))]
      : [];
    form.append(section('Stock and what it cost you', 'Only if you hold stock. Skip it if you sell your time.', [cogsToggle, ...cogsFields]));

    const expenseFields = EXPENSE_LINES
      .filter((id) => id !== y.otherExpensesLine)
      .map((id) => moneyField(id, L(id),
        id === '9' ? 'The deduction you are claiming, not what the vehicle cost to run.'
          : id === '13' ? 'From your depreciation schedule or Form 4562. This tool does not work it out.'
            : id === '24b' ? 'The part you can deduct — usually half.'
              : id === '26' ? 'Wages you paid other people. Not money you took yourself.'
                : null,
        id === '9' ? mileageHelper() : id === '24b' ? mealsHelper() : null));
    form.append(section('Money going out', 'Enter the figure you are claiming on each line. This tool arranges what you give it — it does not decide what counts.', expenseFields));

    form.append(otherExpensesBlock());

    form.append(section('Working from home', null, [
      choice('homemethod', 'Which way did you work it out?', [['simplified', 'The square-foot method'], ['actual', 'The detailed way, on Form 8829'], ['none', 'I am not claiming it']],
        () => state.ret.homeOfficeMethod || 'none', (v) => { state.ret.homeOfficeMethod = v === 'none' ? null : v; }),
      moneyField('30', L('30'), null, homeHelper()),
    ]));

    // These two sections are always built and simply shown or hidden. Rebuilding
    // the form when a figure appears would throw away the caret mid-word, which
    // is exactly when a person is typing that figure.
    state.vehicleSection = section('Your vehicle', 'Schedule C asks these when you claim car or truck costs.', [
        el('div', { class: 'field' }, [
          el('label', { for: 'placed', text: 'When you first used it for the business' }),
          el('input', { type: 'date', id: 'placed', value: state.ret.vehicle.placedInService || '', oninput: (e) => { state.ret.vehicle.placedInService = e.target.value; refresh(); } }),
        ]),
        ...[['businessMiles', 'Business miles'], ['commutingMiles', 'Miles getting to and from work'], ['otherMiles', 'All other miles']].map(([key, label]) => el('div', { class: 'field' }, [
          el('label', { for: key, text: label }),
          el('input', { type: 'text', inputmode: 'numeric', id: key, value: state.ret.vehicle[key] ?? '', oninput: (e) => { state.ret.vehicle[key] = e.target.value.replace(/[\s,]/g, ''); refresh(); } }),
        ])),
        ...[['personalUse', 'Was it available for your own use off duty?'], ['anotherVehicle', 'Do you or your spouse have another vehicle?'], ['evidence', 'Do you have records to back the deduction up?'], ['evidenceWritten', 'Are those records written down?']]
          .map(([key, label]) => choice(key, label, [['yes', 'Yes'], ['no', 'No']],
            () => (state.ret.vehicle[key] === undefined ? '' : state.ret.vehicle[key] ? 'yes' : 'no'),
            (v) => { state.ret.vehicle[key] = v === 'yes'; })),
    ]);
    state.lossSection = section('You have a loss', 'Schedule C asks one more question when the year ends down.', [
      choice('atrisk', 'Was all the money in this business yours to lose?', [['all', 'Yes, all of it'], ['some', 'No, some of it was not']],
        () => state.ret.atRisk || '', (v) => { state.ret.atRisk = v; }),
    ]);
    form.append(state.vehicleSection, state.lossSection);

    form.append(section('What this tool will not do', null, [
      el('ul', { class: 'refusals' }, REFUSALS.map((r) => el('li', {}, [
        el('strong', { text: `${r.subject}. ` }),
        el('span', { text: `${r.because} ${r.instead}` }),
      ]))),
    ]));
  }

  // ── the running total, and the way out ──────────────────────────────
  function refresh() {
    syncOtherRows();
    for (const [id, message] of Object.entries(state.errors)) {
      const box = document.getElementById(`e${id}`);
      if (box) box.textContent = message;
    }
    for (const line of loadYear(state.ret.year).lines) {
      if (state.errors[line.id]) continue;
      const box = document.getElementById(`e${line.id}`);
      if (box) box.textContent = '';
    }

    let out;
    try { out = compute(state.ret); } catch (e) {
      summary.replaceChildren(el('p', { class: 'error', text: e.message }));
      return;
    }
    const dollars = state.ret.rounding === 'dollars';
    const show = (id) => (out.line[id].source === 'empty' ? '—' : formatDollars(out.line[id].cents, { dollars }));

    const figures = el('dl', { class: 'figures' }, [
      ...[['Money coming in', '7'], ['Money going out', '28'], ['Working from home', '30']].flatMap(([label, id]) => [
        el('dt', { text: label }), el('dd', { text: show(id) }),
      ]),
      el('dt', { class: 'big', text: out.line['31'].cents < 0 ? 'Loss for the year' : 'Profit for the year' }),
      el('dd', { class: 'big', text: show('31') }),
    ]);

    const problems = [
      ...out.blockers.map((b) => ({ level: 'blocker', message: b.message })),
      ...out.notices,
    ];
    const notices = el('ul', { class: 'notices' }, problems.map((n) => el('li', { class: n.level }, [
      n.line ? el('span', { class: 'line-no', text: n.line }) : null,
      el('span', { text: n.message }),
    ])));

    if (state.vehicleSection) state.vehicleSection.hidden = !state.ret.entries['9'];
    if (state.lossSection) state.lossSection.hidden = out.line['31'].cents >= 0;

    const ready = out.blockers.length === 0 && Object.keys(state.errors).length === 0;
    const pdfBtn = el('button', { type: 'button', class: 'primary', disabled: !ready, text: 'Download the PDF', onclick: () => download('pdf') });
    const xlBtn = el('button', { type: 'button', class: 'primary', disabled: !ready, text: 'Download the spreadsheet', onclick: () => download('xlsx') });

    // The panel is rebuilt each time, so put the caret back where it was.
    const focused = document.activeElement;
    const focusedId = focused && summary.contains(focused) ? focused.id : null;

    // replaceChildren turns a null argument into the text "null", so the list is
    // filtered rather than passed straight through. This printed "nullnull" on
    // the page until a screenshot caught it.
    summary.replaceChildren(...[
      el('h2', { text: 'Where you are' }),
      figures,
      choice('rounding', 'How to show the figures', [['cents', 'Dollars and cents'], ['dollars', 'Whole dollars, the way it is filed']],
        () => state.ret.rounding, (v) => { state.ret.rounding = v; }),
      choice('include', 'What goes in the PDF', [['both', 'Both'], ['statement', 'The profit and loss only'], ['worksheet', 'The Schedule C worksheet only']],
        () => state.include, (v) => { state.include = v; }),
      el('div', { class: 'downloads' }, [pdfBtn, xlBtn]),
      problems.length ? el('h3', { text: 'Worth checking' }) : null,
      problems.length ? notices : null,
      el('div', { class: 'keep' }, [
        el('label', { class: 'toggle' }, [
          el('input', {
            type: 'checkbox', checked: state.remember,
            onchange: (e) => { state.remember = e.target.checked; if (!state.remember) clearStorage(); else save(state); },
          }),
          el('span', { text: 'Keep what I have typed on this device' }),
        ]),
        el('p', { class: 'hint', text: 'Off by default. It saves in this browser only, and never leaves it. Do not tick it on a shared or library computer.' }),
        el('button', { type: 'button', class: 'ghost', text: 'Clear everything', onclick: () => { clearStorage(); window.location.reload(); } }),
      ]),
      el('p', { class: 'handoff' }, [
        el('span', { text: 'Would rather not do this again next year? ' }),
        el('a', { href: HANDOFF, text: 'We take on sole traders.' }),
      ]),
    ].filter(Boolean));
    if (focusedId) document.getElementById(focusedId)?.focus();
    if (state.remember) save(state);
  }

  function download(kind) {
    const opts = { include: state.include === 'both' ? ['statement', 'worksheet'] : [state.include] };
    const made = kind === 'pdf' ? pdfFor(state.ret, opts) : xlsxFor(state.ret, opts);
    const type = kind === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    const url = URL.createObjectURL(new Blob([made.bytes], { type }));
    const link = el('a', { href: url, download: made.name });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
    document.getElementById('after-download')?.removeAttribute('hidden');
  }

  buildForm();
  refresh();
  return { state, refresh, buildForm };
}

// ── keeping a draft, only when asked ──────────────────────────────────
function save(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      ret: state.ret, raw: state.raw, otherRows: state.otherRows, showCogs: state.showCogs, remember: true,
    }));
  } catch { /* a browser with storage switched off is not an error */ }
}

function restore(state) {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    if (!saved || !saved.remember) return;
    Object.assign(state, { ...saved, errors: {} });
  } catch { clearStorage(); }
}

function clearStorage() {
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* nothing to do */ }
}

export { FIRM, HANDOFF, STORAGE_KEY };

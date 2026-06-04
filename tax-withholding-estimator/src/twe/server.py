"""Local web server for the Tax Withholding Estimator.

Starts a stdlib HTTPServer, serves a single-page form at ``/``, and exposes
``POST /api/estimate`` which runs the Python engine and returns JSON.
No external dependencies — only the standard library is used.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from twe.engine import estimate
from twe.models import EstimatorInput
from twe.report import result_to_dict
from twe.tax_data import TaxDataError

# ---------------------------------------------------------------------------
# Single-page HTML application (embedded so the package is self-contained)
# ---------------------------------------------------------------------------

_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tax Withholding Estimator</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f1f5f9;color:#1e293b;min-height:100vh}
/* ---- header ---- */
.hdr{background:#0f766e;color:#fff;padding:.75rem 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.18)}
.hdr-title{font-weight:700;font-size:1.05rem}
.hdr-sub{font-size:.72rem;opacity:.78;margin-top:.1rem}
/* ---- layout ---- */
.wrap{max-width:1240px;margin:0 auto;padding:1.25rem;display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;align-items:start}
.sticky-panel{position:sticky;top:66px}
/* ---- cards ---- */
.card{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden;margin-bottom:1rem}
.ch{padding:.75rem 1.1rem;font-weight:600;font-size:.85rem;display:flex;align-items:center;justify-content:space-between;background:#f0fdfa;color:#0f766e;border-bottom:1px solid #ccfbf1}
.ch.tog{cursor:pointer;user-select:none}
.ch.tog:hover{background:#e6faf6}
.cb{padding:1rem 1.1rem}
/* ---- field grid ---- */
.fg{display:grid;grid-template-columns:1fr 1fr;gap:.65rem .9rem}
.f{display:flex;flex-direction:column;gap:.2rem}
.f.full{grid-column:1/-1}
.f label{font-size:.76rem;font-weight:500;color:#475569}
.hint{font-size:.68rem;color:#94a3b8;margin-top:.1rem}
input[type=number],select{padding:.44rem .6rem;border:1.5px solid #e2e8f0;border-radius:6px;font-size:.84rem;color:#1e293b;background:#fff;width:100%;transition:border-color .15s}
input[type=number]:focus,select:focus{outline:none;border-color:#0f766e;box-shadow:0 0 0 3px rgba(15,118,110,.12)}
input::placeholder{color:#cbd5e1}
/* ---- radio pills ---- */
.rg{display:flex;gap:.4rem;flex-wrap:wrap}
.rb input[type=radio]{position:absolute;opacity:0;width:0;height:0}
.rb label{display:inline-block;padding:.35rem .8rem;border:1.5px solid #e2e8f0;border-radius:20px;cursor:pointer;font-size:.78rem;font-weight:500;color:#64748b;transition:all .15s}
.rb input:checked+label{background:#0f766e;border-color:#0f766e;color:#fff}
/* ---- sub-box ---- */
.sub-box{background:#f8fafc;border-radius:7px;padding:.8rem;margin-top:.5rem}
.sub-label{font-size:.76rem;font-weight:600;color:#475569;margin-bottom:.5rem}
/* ---- collapse ---- */
.ci{transition:transform .2s;font-size:.7rem;color:#94a3b8}
.tog.open .ci{transform:rotate(-180deg)}
.cbody{overflow:hidden;transition:max-height .25s ease}
/* ---- buttons ---- */
.btn-calc{width:100%;padding:.8rem;background:#0f766e;color:#fff;border:none;border-radius:8px;font-size:.95rem;font-weight:600;cursor:pointer;transition:background .15s;margin-top:.25rem}
.btn-calc:hover{background:#0d6460}
.btn-calc:disabled{background:#94a3b8;cursor:not-allowed}
/* ---- results ---- */
.res-sum{border-radius:10px;padding:1.4rem;text-align:center;margin-bottom:.9rem}
.res-sum.refund{background:linear-gradient(135deg,#059669,#0f766e);color:#fff}
.res-sum.due{background:linear-gradient(135deg,#dc2626,#b91c1c);color:#fff}
.res-sum .big{font-size:2.4rem;font-weight:700;margin:.2rem 0}
.res-sum .lbl{font-size:.78rem;opacity:.82;text-transform:uppercase;letter-spacing:.05em}
.res-sum .sub{font-size:.78rem;opacity:.75;margin-top:.2rem}
.rec-card{border-radius:10px;padding:1.1rem;margin-bottom:.9rem}
.rec-card.warn{background:#fffbeb;border:1.5px solid #fde68a}
.rec-card.ok{background:#f0fdf4;border:1.5px solid #bbf7d0}
.rec-card h3{font-size:.85rem;font-weight:700;margin-bottom:.6rem}
.rec-card.warn h3{color:#92400e}
.rec-card.ok h3{color:#166534}
.amt-big{font-size:1.7rem;font-weight:700;color:#1e293b}
.amt-lbl{font-size:.75rem;color:#64748b}
.rec-note{font-size:.78rem;margin-top:.6rem}
.rec-card.warn .rec-note{color:#92400e}
.rec-card.ok .rec-note{color:#166534}
.bk-table{width:100%;border-collapse:collapse;font-size:.82rem}
.bk-table th{text-align:left;padding:.4rem .8rem;background:#f8fafc;color:#475569;font-weight:600;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid #e2e8f0}
.bk-table td{padding:.42rem .8rem;border-bottom:1px solid #f1f5f9}
.bk-table tr:last-child td{border:none}
.bk-table td:last-child{text-align:right;font-variant-numeric:tabular-nums}
.bk-table tr.tot td{font-weight:700;background:#f8fafc}
.bk-table tr.sect td{padding:.25rem .8rem;background:#f8fafc;font-size:.68rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;font-weight:600}
.rates{display:flex;gap:1.5rem;padding:.7rem 1rem;border-top:1px solid #f1f5f9}
.rate-v{font-size:1.05rem;font-weight:700}
.rate-l{font-size:.68rem;color:#64748b;text-transform:uppercase}
.sh-box{background:#f8fafc;border-radius:7px;padding:.8rem;margin-bottom:.9rem;font-size:.8rem}
.sh-box h4{font-weight:600;margin-bottom:.4rem}
.sh-row{display:flex;gap:1.5rem;flex-wrap:wrap}
.notes-list{list-style:none;font-size:.77rem;color:#64748b}
.notes-list li{padding:.3rem 0;border-bottom:1px solid #f1f5f9;padding-left:1.1rem;position:relative}
.notes-list li::before{content:'\\2139';position:absolute;left:0;color:#0ea5e9}
.empty-state{text-align:center;padding:2.5rem 1rem;color:#94a3b8}
.empty-state .ico{font-size:2.5rem;margin-bottom:.6rem}
.empty-state p{font-size:.85rem;line-height:1.5}
.err-box{background:#fef2f2;border:1.5px solid #fecaca;border-radius:7px;padding:.85rem;color:#b91c1c;font-size:.83rem}
.disc{font-size:.7rem;color:#94a3b8;text-align:center;padding:.75rem .5rem;line-height:1.5}
.disc a{color:#0f766e}
@media(max-width:768px){.wrap{grid-template-columns:1fr}.sticky-panel{position:static;order:-1}.fg{grid-template-columns:1fr}}
</style>
</head>
<body>
<header class="hdr">
  <div>
    <div class="hdr-title">&#x1F4CB; Tax Withholding Estimator</div>
    <div class="hdr-sub">Federal only &middot; Planning tool &mdash; not tax advice</div>
  </div>
  <button class="btn-calc" onclick="go()" style="width:auto;padding:.4rem 1.25rem;margin:0;font-size:.88rem">Calculate &#x21B5;</button>
</header>

<div class="wrap">
<!-- ===== FORM ===== -->
<div id="form-col">

  <!-- Filing info -->
  <div class="card">
    <div class="ch">&#x1F4C1; Filing Information</div>
    <div class="cb">
      <div class="f" style="margin-bottom:.85rem">
        <label>Filing Status</label>
        <div class="rg">
          <div class="rb"><input type="radio" name="fs" id="fs_s" value="single" checked><label for="fs_s">Single</label></div>
          <div class="rb"><input type="radio" name="fs" id="fs_mfj" value="married_jointly"><label for="fs_mfj">Married Jointly</label></div>
          <div class="rb"><input type="radio" name="fs" id="fs_mfs" value="married_separately"><label for="fs_mfs">Married Separately</label></div>
          <div class="rb"><input type="radio" name="fs" id="fs_hoh" value="head_of_household"><label for="fs_hoh">Head of Household</label></div>
        </div>
      </div>
      <div class="fg">
        <div class="f">
          <label for="tax_year">Tax Year</label>
          <select id="tax_year"></select>
        </div>
      </div>
    </div>
  </div>

  <!-- Paystub -->
  <div class="card">
    <div class="ch">&#x1F4B0; Paystub</div>
    <div class="cb">
      <div class="fg">
        <div class="f">
          <label for="pay_freq">Pay Frequency</label>
          <select id="pay_freq">
            <option value="weekly">Weekly (52/yr)</option>
            <option value="biweekly" selected>Bi-weekly (26/yr)</option>
            <option value="semimonthly">Semi-monthly (24/yr)</option>
            <option value="monthly">Monthly (12/yr)</option>
            <option value="annual">Annual (1/yr)</option>
          </select>
        </div>
        <div class="f">
          <label for="last_pay_date">Last Pay Date</label>
          <input type="date" id="last_pay_date">
          <div id="periods_badge" class="hint" style="min-height:1.2em"></div>
        </div>
        <input type="hidden" id="periods_left">
        <div class="f">
          <label for="gross">Gross Pay Per Period ($)</label>
          <input type="number" id="gross" placeholder="e.g. 3,200.00" min="0" step="0.01">
        </div>
        <div class="f">
          <label for="withheld">Federal Tax Withheld Per Period ($)</label>
          <input type="number" id="withheld" placeholder="e.g. 410.00" min="0" step="0.01">
        </div>
        <div class="f">
          <label for="ret401k">Pre-tax 401(k)/403(b) Per Period ($)</label>
          <input type="number" id="ret401k" placeholder="e.g. 200.00" min="0" step="0.01">
        </div>
        <div class="f">
          <label for="pretax_other">Other Pre-tax (Health/HSA/FSA) Per Period ($)</label>
          <input type="number" id="pretax_other" placeholder="e.g. 150.00" min="0" step="0.01">
        </div>
      </div>
      <div class="sub-box">
        <div class="sub-label">Year-to-Date &mdash; for mid-year estimates</div>
        <div class="fg">
          <div class="f">
            <label for="ytd_wages">YTD Taxable Wages ($)</label>
            <input type="number" id="ytd_wages" placeholder="From last paystub" min="0" step="0.01">
          </div>
          <div class="f">
            <label for="ytd_wh">YTD Federal Tax Withheld ($)</label>
            <input type="number" id="ytd_wh" placeholder="From last paystub" min="0" step="0.01">
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Other Income -->
  <div class="card" id="c_inc">
    <div class="ch tog open" onclick="tog('inc')">
      <span>&#x1F4C8; Other Income <span style="font-size:.72rem;font-weight:400;color:#94a3b8">(IRA, dividends, capital gains, SE&hellip;)</span></span>
      <span class="ci">&#9660;</span>
    </div>
    <div class="cbody" id="b_inc" style="max-height:2000px">
    <div class="cb">
      <div class="fg">
        <div class="f">
          <label for="ira_dist">IRA / Retirement Distributions ($)</label>
          <input type="number" id="ira_dist" placeholder="0" min="0" step="0.01">
          <div class="hint">Taxable portion &mdash; Form 1099-R</div>
        </div>
        <div class="f">
          <label for="soc_sec">Taxable Social Security ($)</label>
          <input type="number" id="soc_sec" placeholder="0" min="0" step="0.01">
          <div class="hint">Enter the already-computed taxable amount</div>
        </div>
        <div class="f">
          <label for="interest">Interest Income ($)</label>
          <input type="number" id="interest" placeholder="0" min="0" step="0.01">
        </div>
        <div class="f">
          <label for="ord_div">Ordinary Dividends ($)</label>
          <input type="number" id="ord_div" placeholder="0" min="0" step="0.01">
          <div class="hint">Box 1a of Form 1099-DIV</div>
        </div>
        <div class="f">
          <label for="qual_div">Qualified Dividends ($)</label>
          <input type="number" id="qual_div" placeholder="0" min="0" step="0.01">
          <div class="hint">Box 1b &mdash; must be &le; ordinary dividends</div>
        </div>
        <div class="f">
          <label for="ltcg">Long-Term Capital Gains ($)</label>
          <input type="number" id="ltcg" placeholder="0" min="0" step="0.01">
        </div>
        <div class="f">
          <label for="stcg">Short-Term Capital Gains ($)</label>
          <input type="number" id="stcg" placeholder="0" min="0" step="0.01">
          <div class="hint">Taxed as ordinary income</div>
        </div>
        <div class="f">
          <label for="se_net">Net Self-Employment Income ($)</label>
          <input type="number" id="se_net" placeholder="0" min="0" step="0.01">
          <div class="hint">Schedule C net profit</div>
        </div>
        <div class="f">
          <label for="unemp">Unemployment Compensation ($)</label>
          <input type="number" id="unemp" placeholder="0" min="0" step="0.01">
        </div>
        <div class="f">
          <label for="other_inc">Other Taxable Income ($)</label>
          <input type="number" id="other_inc" placeholder="0" min="0" step="0.01">
        </div>
        <div class="f">
          <label for="sp_wages">Spouse&rsquo;s Wages ($)</label>
          <input type="number" id="sp_wages" placeholder="0" min="0" step="0.01">
          <div class="hint">For MFJ &mdash; full-year taxable wages</div>
        </div>
        <div class="f">
          <label for="sp_wh">Spouse&rsquo;s Federal Tax Withheld ($)</label>
          <input type="number" id="sp_wh" placeholder="0" min="0" step="0.01">
        </div>
      </div>
    </div>
    </div>
  </div>

  <!-- Adjustments -->
  <div class="card" id="c_adj">
    <div class="ch tog open" onclick="tog('adj')">
      <span>&#x1F4C9; Above-the-Line Adjustments</span>
      <span class="ci">&#9660;</span>
    </div>
    <div class="cbody" id="b_adj" style="max-height:2000px">
    <div class="cb">
      <div class="fg">
        <div class="f">
          <label for="ira_ded">Traditional IRA Deduction ($)</label>
          <input type="number" id="ira_ded" placeholder="0" min="0" step="0.01">
        </div>
        <div class="f">
          <label for="hsa_ded">HSA Deduction ($)</label>
          <input type="number" id="hsa_ded" placeholder="0" min="0" step="0.01">
        </div>
        <div class="f">
          <label for="sl_int">Student Loan Interest ($)</label>
          <input type="number" id="sl_int" placeholder="0" min="0" max="2500" step="0.01">
        </div>
        <div class="f">
          <label for="other_adj">Other Adjustments ($)</label>
          <input type="number" id="other_adj" placeholder="0" min="0" step="0.01">
        </div>
      </div>
    </div>
    </div>
  </div>

  <!-- Deductions -->
  <div class="card" id="c_ded">
    <div class="ch tog open" onclick="tog('ded')">
      <span>&#x1F3E0; Deductions</span>
      <span class="ci">&#9660;</span>
    </div>
    <div class="cbody" id="b_ded" style="max-height:2000px">
    <div class="cb">
      <div class="f" style="margin-bottom:.75rem">
        <label>Deduction Type</label>
        <div class="rg">
          <div class="rb"><input type="radio" name="ded_type" id="ded_std" value="standard" checked onchange="togItemized()"><label for="ded_std">Standard</label></div>
          <div class="rb"><input type="radio" name="ded_type" id="ded_itm" value="itemized" onchange="togItemized()"><label for="ded_itm">Itemized</label></div>
        </div>
      </div>
      <div id="itm_row" style="display:none;margin-bottom:.65rem">
        <div class="f">
          <label for="itm_total">Total Itemized Deductions ($)</label>
          <input type="number" id="itm_total" placeholder="e.g. 25,000" min="0" step="0.01">
          <div class="hint">Schedule A total</div>
        </div>
      </div>
      <div class="f">
        <label for="extra_std">Additional Standard Deductions (age 65+ or blind)</label>
        <select id="extra_std">
          <option value="0">0 &mdash; neither applies</option>
          <option value="1">1 &mdash; one taxpayer qualifies</option>
          <option value="2">2 &mdash; both qualify (or one qualifies twice)</option>
          <option value="3">3</option>
          <option value="4">4</option>
        </select>
        <div class="hint">Each adds $2,000 (Single/HoH) or $1,600 (MFJ/MFS)</div>
      </div>
    </div>
    </div>
  </div>

  <!-- Credits -->
  <div class="card" id="c_cred">
    <div class="ch tog open" onclick="tog('cred')">
      <span>&#x1F381; Credits</span>
      <span class="ci">&#9660;</span>
    </div>
    <div class="cbody" id="b_cred" style="max-height:2000px">
    <div class="cb">
      <div class="fg">
        <div class="f">
          <label for="ctc">Child Tax Credit ($)</label>
          <input type="number" id="ctc" placeholder="0" min="0" step="0.01">
          <div class="hint">Up to $2,000/child &mdash; phase-outs not modeled here</div>
        </div>
        <div class="f">
          <label for="other_nr_cred">Other Nonrefundable Credits ($)</label>
          <input type="number" id="other_nr_cred" placeholder="0" min="0" step="0.01">
          <div class="hint">Child care, education, saver&rsquo;s, etc.</div>
        </div>
        <div class="f">
          <label for="ref_cred">Refundable Credits ($)</label>
          <input type="number" id="ref_cred" placeholder="0" min="0" step="0.01">
          <div class="hint">EITC, ACTC, etc.</div>
        </div>
      </div>
    </div>
    </div>
  </div>

  <!-- Other Payments -->
  <div class="card" id="c_pay">
    <div class="ch tog" onclick="tog('pay')">
      <span>&#x1F4B3; Other Payments Already Made</span>
      <span class="ci">&#9660;</span>
    </div>
    <div class="cbody" id="b_pay" style="max-height:0">
    <div class="cb">
      <div class="fg">
        <div class="f">
          <label for="est_pay">Estimated Tax Payments ($)</label>
          <input type="number" id="est_pay" placeholder="0" min="0" step="0.01">
          <div class="hint">Quarterly Form 1040-ES payments so far</div>
        </div>
        <div class="f">
          <label for="other_wh">Other Withholding ($)</label>
          <input type="number" id="other_wh" placeholder="0" min="0" step="0.01">
          <div class="hint">Non-paycheck withholding (1099 backup, etc.)</div>
        </div>
      </div>
    </div>
    </div>
  </div>

  <!-- Options -->
  <div class="card" id="c_opt">
    <div class="ch tog" onclick="tog('opt')">
      <span>&#x2699;&#xFE0F; Options &amp; Safe Harbor</span>
      <span class="ci">&#9660;</span>
    </div>
    <div class="cbody" id="b_opt" style="max-height:0">
    <div class="cb">
      <div class="fg">
        <div class="f">
          <label for="target_ref">Target Refund ($)</label>
          <input type="number" id="target_ref" placeholder="0" min="0" step="0.01">
          <div class="hint">Desired refund amount (0 = break even)</div>
        </div>
        <div class="f"></div>
        <div class="f">
          <label for="py_tax">Prior Year Total Tax ($)</label>
          <input type="number" id="py_tax" placeholder="Optional" min="0" step="0.01">
          <div class="hint">Form 1040 line 24 &mdash; enables safe-harbor calc</div>
        </div>
        <div class="f">
          <label for="py_agi">Prior Year AGI ($)</label>
          <input type="number" id="py_agi" placeholder="Optional" min="0" step="0.01">
          <div class="hint">Form 1040 line 11 &mdash; for 100%/110% test</div>
        </div>
      </div>
    </div>
    </div>
  </div>

  <button class="btn-calc" id="calc-btn" onclick="go()">&#x27F3; Calculate Withholding</button>
  <p class="disc">Federal income tax only &mdash; for planning purposes only. Always verify with a tax professional or the official <a href="https://www.irs.gov/individuals/tax-withholding-estimator" target="_blank">IRS Tax Withholding Estimator</a>.</p>
</div>

<!-- ===== RESULTS ===== -->
<div class="sticky-panel">
  <div id="results">
    <div class="card">
      <div class="empty-state">
        <div class="ico">&#x1F4CA;</div>
        <p>Fill in your paystub information and click <strong>Calculate</strong> to see your projected tax liability and withholding recommendation.</p>
      </div>
    </div>
  </div>
</div>
</div><!-- .wrap -->

<script>
const $ = id => document.getElementById(id);
const numVal = id => { const v=$(''+id).value.trim(); return v===''?null:parseFloat(v); };
const intVal = id => { const v=$(''+id).value.trim(); return v===''?null:parseInt(v,10); };

function tog(name){
  const hdr = document.querySelector('#c_'+name+' .ch');
  const body = $('b_'+name);
  const open = hdr.classList.contains('open');
  if(open){ hdr.classList.remove('open'); body.style.maxHeight='0'; }
  else { hdr.classList.add('open'); body.style.maxHeight='2000px'; }
}

function togItemized(){
  $('itm_row').style.display = $('ded_itm').checked ? 'block':'none';
}

function usd(v){
  const n=parseFloat(v), a=Math.abs(n), s=n<0?'-':'';
  return s+'$'+a.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
}
function pct(v){ return (parseFloat(v)*100).toFixed(2)+'%'; }
function z(v){ return parseFloat(v)===0; }
function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function buildPayload(){
  const isItm = $('ded_itm').checked;
  return {
    filing_status: document.querySelector('input[name="fs"]:checked').value,
    tax_year: parseInt($('tax_year').value,10),
    paystub:{
      pay_frequency: $('pay_freq').value,
      gross_pay_per_period: numVal('gross')||0,
      federal_tax_withheld_per_period: numVal('withheld')||0,
      retirement_pretax_per_period: numVal('ret401k')||0,
      other_pretax_per_period: numVal('pretax_other')||0,
      ytd_taxable_wages: numVal('ytd_wages'),
      ytd_federal_tax_withheld: numVal('ytd_wh'),
      pay_periods_remaining: intVal('periods_left'),
    },
    other_income:{
      taxable_retirement_distributions: numVal('ira_dist')||0,
      taxable_social_security: numVal('soc_sec')||0,
      interest: numVal('interest')||0,
      ordinary_dividends: numVal('ord_div')||0,
      qualified_dividends: numVal('qual_div')||0,
      long_term_capital_gains: numVal('ltcg')||0,
      short_term_capital_gains: numVal('stcg')||0,
      self_employment_net: numVal('se_net')||0,
      unemployment: numVal('unemp')||0,
      other_taxable_income: numVal('other_inc')||0,
      spouse_taxable_wages: numVal('sp_wages')||0,
      spouse_federal_tax_withheld: numVal('sp_wh')||0,
    },
    adjustments:{
      traditional_ira_deduction: numVal('ira_ded')||0,
      hsa_deduction: numVal('hsa_ded')||0,
      student_loan_interest: numVal('sl_int')||0,
      other_adjustments: numVal('other_adj')||0,
    },
    deductions:{
      itemized_total: isItm ? numVal('itm_total') : null,
      extra_standard_deductions: parseInt($('extra_std').value,10),
    },
    credits:{
      child_tax_credit: numVal('ctc')||0,
      other_nonrefundable_credits: numVal('other_nr_cred')||0,
      refundable_credits: numVal('ref_cred')||0,
    },
    other_payments:{
      estimated_tax_payments: numVal('est_pay')||0,
      other_withholding: numVal('other_wh')||0,
    },
    target_refund: numVal('target_ref')||0,
    prior_year_tax: numVal('py_tax'),
    prior_year_agi: numVal('py_agi'),
  };
}

async function go(){
  const btn=$('calc-btn'); btn.disabled=true; btn.textContent='Calculating…';
  try {
    const r=await fetch('/api/estimate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(buildPayload())});
    const data=await r.json();
    if(!r.ok) showError(data.error||'Unknown error');
    else render(data);
  } catch(e){ showError('Could not reach server: '+e.message); }
  finally { btn.disabled=false; btn.textContent='⟳ Calculate Withholding'; }
}

function showError(msg){
  $('results').innerHTML='<div class="card"><div class="cb"><div class="err-box">⚠️ '+esc(msg)+'</div></div></div>';
}

function bkRow(label,val,cls){
  return '<tr'+(cls?' class="'+cls+'"':'')+'><td>'+label+'</td><td>'+usd(val)+'</td></tr>';
}
function sectRow(label){
  return '<tr class="sect"><td colspan="2">'+label+'</td></tr>';
}

function render(d){
  const b=d.breakdown, r=d.recommendation;
  const bal=parseFloat(r.projected_balance);
  const isRef=bal>=0;
  const statusMap={single:'Single',married_jointly:'Married Jointly',married_separately:'Married Separately',head_of_household:'Head of Household'};

  // ---- summary card ----
  const sumHtml=`<div class="res-sum ${isRef?'refund':'due'}">
    <div class="lbl">${isRef?'Projected Refund':'Projected Balance Due'}</div>
    <div class="big">${usd(Math.abs(bal))}</div>
    <div class="sub">${statusMap[d.filing_status]} &middot; ${d.tax_year_used} &middot; at current withholding rate</div>
  </div>`;

  // ---- recommendation ----
  const isOver=r.is_over_withholding;
  let recHtml;
  if(isOver){
    recHtml=`<div class="rec-card ok">
      <h3>&#x2705; On track &mdash; you may be over-withholding</h3>
      <div><span class="amt-big">${usd(r.recommended_withholding_per_period)}</span></div>
      <div class="amt-lbl">would break even per paycheck (your target refund: ${usd(r.target_refund)})</div>
      <p class="rec-note">You could <strong>reduce</strong> withholding by adjusting Form W-4 Step&nbsp;3 (dependents) or Step&nbsp;4b (extra deductions). Total projected payments of <strong>${usd(r.projected_total_payments)}</strong> exceed the <strong>${usd(b.total_tax_liability)}</strong> projected liability.</p>
    </div>`;
  } else {
    recHtml=`<div class="rec-card warn">
      <h3>&#x26A0;&#xFE0F; Action recommended &mdash; under-withholding</h3>
      <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:.5rem">
        <div><span class="amt-big">${usd(r.recommended_withholding_per_period)}</span><div class="amt-lbl">recommended per paycheck</div></div>
        <div><span class="amt-big" style="color:#b45309">+${usd(r.additional_withholding_per_period)}</span><div class="amt-lbl">extra per paycheck &mdash; W-4 line&nbsp;4(c)</div></div>
      </div>
      <p class="rec-note">Enter <strong>${usd(r.additional_withholding_per_period)}</strong> as additional withholding on <strong>Form W-4 Step&nbsp;4(c)</strong>. You have <strong>${r.periods_remaining}</strong> pay period${r.periods_remaining!==1?'s':''} remaining to close the gap.</p>
    </div>`;
  }

  // ---- safe harbor ----
  let shHtml='';
  if(r.safe_harbor_target){
    const met=parseFloat(r.projected_total_payments)>=parseFloat(r.safe_harbor_target);
    shHtml=`<div class="sh-box">
      <h4>&#x1F6E1;&#xFE0F; Safe Harbor &mdash; avoid underpayment penalty</h4>
      <div class="sh-row">
        <div><span style="color:#64748b">Min. payments needed: </span><strong>${usd(r.safe_harbor_target)}</strong></div>
        <div><span style="color:#64748b">Status: </span><strong style="color:${met?'#166534':'#b45309'}">${met?'&#x2705; Met':'&#x26A0;&#xFE0F; Not met'}</strong></div>
        ${r.safe_harbor_additional_per_period&&parseFloat(r.safe_harbor_additional_per_period)>0?'<div><span style="color:#64748b">Extra needed/period: </span><strong>'+usd(r.safe_harbor_additional_per_period)+'</strong></div>':''}
      </div>
    </div>`;
  }

  // ---- breakdown table ----
  const projRemaining=parseFloat(r.projected_withholding_current_rate)-parseFloat(r.ytd_withholding);
  let rows='';
  rows+=sectRow('Income');
  rows+=bkRow('Projected taxable wages',b.projected_taxable_wages);
  rows+=bkRow('Total income',b.total_income);
  if(!z(b.adjustments_total)) rows+=bkRow('&minus; Adjustments to income',b.adjustments_total);
  rows+=bkRow('Adjusted Gross Income (AGI)',b.adjusted_gross_income,'tot');
  rows+=bkRow('&minus; Deduction ('+b.deduction_kind+')',b.deduction_used);
  rows+=bkRow('Taxable income',b.taxable_income,'tot');
  rows+=sectRow('Tax');
  rows+=bkRow('Ordinary income tax',b.ordinary_income_tax);
  if(!z(b.capital_gains_tax)) rows+=bkRow('Capital gains / qual. dividends',b.capital_gains_tax);
  if(!z(b.self_employment_tax)) rows+=bkRow('Self-employment tax',b.self_employment_tax);
  if(!z(b.additional_medicare_tax)) rows+=bkRow('Additional Medicare Tax (0.9%)',b.additional_medicare_tax);
  if(!z(b.net_investment_income_tax)) rows+=bkRow('Net Investment Income Tax (3.8%)',b.net_investment_income_tax);
  if(!z(b.nonrefundable_credits)) rows+=bkRow('&minus; Nonrefundable credits',b.nonrefundable_credits);
  if(!z(b.refundable_credits)) rows+=bkRow('&minus; Refundable credits',b.refundable_credits);
  rows+=bkRow('TOTAL TAX LIABILITY',b.total_tax_liability,'tot');
  rows+=sectRow('Payments');
  rows+=bkRow('YTD withholding ('+r.periods_elapsed+' of '+r.periods_per_year+' periods)',r.ytd_withholding);
  if(projRemaining>0.005) rows+=bkRow('Remaining projected withholding ('+r.periods_remaining+' periods)',projRemaining.toFixed(2));
  if(!z(r.other_payments_total)) rows+=bkRow('Other payments / spouse withholding',r.other_payments_total);
  rows+=bkRow('Projected total payments',r.projected_total_payments,'tot');
  rows+=bkRow((bal>=0?'Projected refund':'Projected balance due'),Math.abs(bal).toFixed(2),'tot');

  const bkHtml=`<div class="card" style="margin-top:.75rem">
    <div class="ch">&#x1F4CA; Full Breakdown</div>
    <div style="padding:0">
      <table class="bk-table"><tbody>${rows}</tbody></table>
      <div class="rates">
        <div><div class="rate-v">${pct(b.marginal_rate)}</div><div class="rate-l">Marginal Rate</div></div>
        <div style="width:1px;background:#e2e8f0"></div>
        <div><div class="rate-v">${pct(b.effective_rate)}</div><div class="rate-l">Effective Rate</div></div>
      </div>
    </div>
  </div>`;

  // ---- notes ----
  let notesHtml='';
  if(d.notes&&d.notes.length){
    notesHtml=`<div class="card" style="margin-top:.75rem">
      <div class="ch" style="font-size:.78rem">&#x2139;&#xFE0F; Notes</div>
      <div class="cb" style="padding:.65rem 1.1rem">
        <ul class="notes-list">${d.notes.map(n=>'<li>'+esc(n)+'</li>').join('')}</ul>
      </div>
    </div>`;
  }

  $('results').innerHTML=sumHtml+recHtml+shHtml+bkHtml+notesHtml+
    '<p class="disc">For planning only &mdash; not tax advice. Verify with the official <a href="https://www.irs.gov/individuals/tax-withholding-estimator" target="_blank">IRS Tax Withholding Estimator</a>.</p>';

  if(window.innerWidth<768) $('results').scrollIntoView({behavior:'smooth'});
}

// ---- tax-year auto-detect & period-remaining calculator ----
(function(){
  const BUNDLED=[2025];
  const cur=new Date().getFullYear();
  const sel=$('tax_year');
  const years=new Set([...BUNDLED, cur]);
  [...years].sort().reverse().forEach(y=>{
    const o=document.createElement('option');
    o.value=y; o.textContent=y+(y===cur?' (current)':'');
    if(y===cur) o.selected=true;
    sel.appendChild(o);
  });
})();

function computeRemaining(freq,dateStr,taxYear){
  if(!dateStr) return null;
  const lastPay=new Date(dateStr+'T12:00:00');
  if(isNaN(lastPay.getTime())) return null;
  const yr=taxYear||lastPay.getFullYear();
  const yearEnd=new Date(yr,11,31,23,59,59);
  const ms=86400000;
  if(freq==='annual') return lastPay.getFullYear()<yr?1:0;
  if(freq==='monthly'){
    // next pay month is lastPay.getMonth()+1; count through December
    return Math.max(0,11-lastPay.getMonth());
  }
  if(freq==='semimonthly'){
    // assume pay dates are the 1st and 15th
    let count=0;
    const day=lastPay.getDate();
    let next=day<15
      ?new Date(lastPay.getFullYear(),lastPay.getMonth(),15,12)
      :new Date(lastPay.getFullYear(),lastPay.getMonth()+1,1,12);
    while(next<=yearEnd){
      count++;
      next=next.getDate()===1
        ?new Date(next.getFullYear(),next.getMonth(),15,12)
        :new Date(next.getFullYear(),next.getMonth()+1,1,12);
    }
    return count;
  }
  // weekly / biweekly
  const days=freq==='weekly'?7:14;
  let next=new Date(lastPay.getTime()+days*ms);
  let count=0;
  while(next<=yearEnd){ count++; next=new Date(next.getTime()+days*ms); }
  return count;
}

function updatePeriods(){
  const freq=$('pay_freq').value;
  const dateStr=$('last_pay_date').value;
  const taxYear=parseInt($('tax_year').value,10);
  const badge=$('periods_badge'), hidden=$('periods_left');
  if(!dateStr){ badge.innerHTML='<span class="hint">Leave blank to assume a full year</span>'; hidden.value=''; return; }
  const n=computeRemaining(freq,dateStr,taxYear);
  if(n===null){ badge.innerHTML=''; hidden.value=''; return; }
  badge.innerHTML='<span style="color:#059669;font-weight:600">&#x2192; '+n+' paycheck'+(n!==1?'s':'')+' remaining in '+taxYear+'</span>';
  hidden.value=n;
}

$('pay_freq').addEventListener('change',updatePeriods);
$('last_pay_date').addEventListener('change',updatePeriods);
$('tax_year').addEventListener('change',updatePeriods);
// Show default hint before a date is entered
$('periods_badge').innerHTML='<span class="hint">Leave blank to assume a full year</span>';

document.addEventListener('keydown',e=>{ if(e.key==='Enter'&&e.target.tagName!=='BUTTON') go(); });
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args) -> None:  # suppress per-request console noise
        pass

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            body = _HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def _send_json(self, code: int, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path == "/api/estimate":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
                inp = EstimatorInput.from_dict(data)
                result = estimate(inp)
                self._send_json(200, result_to_dict(result))
            except (ValueError, TaxDataError, json.JSONDecodeError) as exc:
                self._send_json(400, {"error": str(exc)})
        else:
            self.send_error(404)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    """Start the estimator web UI and block until Ctrl+C."""

    server = HTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}"
    print(f"Tax Withholding Estimator: {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

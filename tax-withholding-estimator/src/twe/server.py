"""Local web server for the Tax Withholding Estimator.

Starts a stdlib HTTPServer, serves a single-page form at ``/``, and exposes
``POST /api/estimate`` which runs the Python engine and returns JSON.
No external dependencies — only the standard library is used.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import webbrowser
import importlib.resources as _resources
from http.server import BaseHTTPRequestHandler, HTTPServer

from twe.engine import estimate
from twe.models import EstimatorInput
from twe.report import render_tape, result_to_dict
# twe.excel_report is imported lazily inside the handler (optional dependency)
from twe.tax_data import TaxDataError

# ---------------------------------------------------------------------------
# Single-page HTML application (embedded so the package is self-contained)
# ---------------------------------------------------------------------------

_HTML_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tax Withholding Estimator</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0B1F3A;--navy-deep:#061A35;--navy-soft:#173361;
  --gold:#B08D57;--gold-light:#D4B97E;--gold-deep:#8A6F44;
  --cream:#F6F2EA;--cream2:#EFE9DC;--paper:#FBF9F4;--hairline:#D9CFB8;
  --ink:#0E1726;--charcoal:#1F2733;
}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--paper);color:var(--ink);min-height:100vh}
/* ---- header ---- */
.hdr{background:var(--navy-deep);color:#fff;padding:.65rem 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 10px rgba(0,0,0,.32)}
.seal{display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;border:2px solid var(--gold);background:var(--navy-deep);color:var(--gold);font-family:Georgia,serif;font-weight:bold;font-size:22px;flex-shrink:0}
.wordmark{font-family:Georgia,serif;letter-spacing:2px;font-size:15px;color:#fff}
.subtag{font-size:8.5px;letter-spacing:2px;color:var(--gold-light);margin-top:2px}
.hdr-divider{width:1px;height:34px;background:rgba(212,185,126,.28);margin:0 12px}
.hdr-title{font-family:Georgia,serif;font-size:.97rem;color:#fff;letter-spacing:.3px}
.hdr-sub{font-size:.68rem;color:rgba(212,185,126,.8);margin-top:.15rem}
/* ---- layout ---- */
.wrap{max-width:1240px;margin:0 auto;padding:1.25rem;display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;align-items:start}
.sticky-panel{position:sticky;top:66px}
/* ---- cards ---- */
.card{background:#fff;border:1px solid var(--hairline);border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);overflow:hidden;margin-bottom:1rem}
.ch{padding:.68rem 1.1rem;font-weight:600;font-size:.82rem;display:flex;align-items:center;justify-content:space-between;background:var(--navy);color:#fff;border-bottom:1px solid var(--navy-soft);letter-spacing:.3px}
.ch.tog{cursor:pointer;user-select:none}
.ch.tog:hover{background:var(--navy-soft)}
.cb{padding:1rem 1.1rem}
/* ---- field grid ---- */
.fg{display:grid;grid-template-columns:1fr 1fr;gap:.65rem .9rem}
.f{display:flex;flex-direction:column;gap:.2rem}
.f.full{grid-column:1/-1}
.f label{font-size:.76rem;font-weight:500;color:var(--charcoal)}
.hint{font-size:.68rem;color:#94a3b8;margin-top:.1rem}
input[type=number],input[type=text],input[type=date],select{padding:.44rem .6rem;border:1.5px solid var(--hairline);border-radius:6px;font-size:.84rem;color:var(--ink);background:#fff;width:100%;transition:border-color .15s}
input[type=number]:focus,input[type=text]:focus,input[type=date]:focus,select:focus{outline:none;border-color:var(--gold);box-shadow:0 0 0 3px rgba(176,141,87,.18)}
input::placeholder{color:#c4b89e}
/* ---- radio pills ---- */
.rg{display:flex;gap:.4rem;flex-wrap:wrap}
.rb input[type=radio]{position:absolute;opacity:0;width:0;height:0}
.rb label{display:inline-block;padding:.35rem .8rem;border:1.5px solid var(--hairline);border-radius:20px;cursor:pointer;font-size:.78rem;font-weight:500;color:var(--charcoal);transition:all .15s}
.rb input:checked+label{background:var(--navy);border-color:var(--navy);color:#fff}
/* ---- sub-box ---- */
.sub-box{background:var(--cream2);border:1px solid var(--hairline);border-radius:7px;padding:.8rem;margin-top:.5rem}
.sub-label{font-size:.76rem;font-weight:600;color:var(--charcoal);margin-bottom:.5rem}
/* ---- collapse ---- */
.ci{transition:transform .2s;font-size:.7rem;color:rgba(255,255,255,.6)}
.tog.open .ci{transform:rotate(-180deg)}
.cbody{overflow:hidden;transition:max-height .25s ease}
/* ---- buttons ---- */
.btn-calc{width:100%;padding:.8rem;background:var(--navy);color:#fff;border:none;border-radius:6px;font-size:.95rem;font-weight:600;cursor:pointer;transition:background .15s;margin-top:.25rem;font-family:Georgia,serif;letter-spacing:.3px}
.btn-calc:hover{background:var(--navy-soft)}
.btn-calc:disabled{background:#94a3b8;cursor:not-allowed}
/* ---- results ---- */
.res-sum{border-radius:8px;padding:1.4rem;text-align:center;margin-bottom:.9rem}
.res-sum.refund{background:linear-gradient(135deg,#2F5D3A,#1a3d22);color:#fff}
.res-sum.due{background:linear-gradient(135deg,#9B2226,#7a1a1d);color:#fff}
.res-sum .big{font-size:2.4rem;font-weight:700;font-family:Georgia,serif;margin:.2rem 0}
.res-sum .lbl{font-size:.78rem;opacity:.82;text-transform:uppercase;letter-spacing:.08em}
.res-sum .sub{font-size:.78rem;opacity:.75;margin-top:.2rem}
.rec-card{border-radius:8px;padding:1.1rem;margin-bottom:.9rem}
.rec-card.warn{background:#fffbeb;border:1.5px solid #f0d58c}
.rec-card.ok{background:#f0fdf4;border:1.5px solid #bbf7d0}
.rec-card h3{font-size:.85rem;font-weight:700;margin-bottom:.6rem}
.rec-card.warn h3{color:#92400e}
.rec-card.ok h3{color:#166534}
.amt-big{font-size:1.7rem;font-weight:700;color:var(--ink);font-family:Georgia,serif}
.amt-lbl{font-size:.75rem;color:var(--charcoal)}
.rec-note{font-size:.78rem;margin-top:.6rem}
.rec-card.warn .rec-note{color:#92400e}
.rec-card.ok .rec-note{color:#166534}
.bk-table{width:100%;border-collapse:collapse;font-size:.82rem}
.bk-table th{text-align:left;padding:.4rem .8rem;background:var(--cream2);color:var(--charcoal);font-weight:600;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid var(--hairline)}
.bk-table td{padding:.42rem .8rem;border-bottom:1px solid #f0e8d8}
.bk-table tr:last-child td{border:none}
.bk-table td:last-child{text-align:right;font-variant-numeric:tabular-nums}
.bk-table tr.tot td{font-weight:700;background:var(--cream)}
.bk-table tr.sect td{padding:.25rem .8rem;background:var(--navy);color:rgba(255,255,255,.75);font-size:.68rem;text-transform:uppercase;letter-spacing:.05em;font-weight:600}
.rates{display:flex;gap:1.5rem;padding:.7rem 1rem;border-top:1px solid var(--hairline)}
.rate-v{font-size:1.05rem;font-weight:700;font-family:Georgia,serif}
.rate-l{font-size:.68rem;color:var(--charcoal);text-transform:uppercase;letter-spacing:.03em}
.sh-box{background:var(--cream2);border:1px solid var(--hairline);border-radius:7px;padding:.8rem;margin-bottom:.9rem;font-size:.8rem}
.sh-box h4{font-weight:600;margin-bottom:.4rem;color:var(--navy)}
.sh-row{display:flex;gap:1.5rem;flex-wrap:wrap}
.notes-list{list-style:none;font-size:.77rem;color:var(--charcoal)}
.notes-list li{padding:.3rem 0;border-bottom:1px solid var(--hairline);padding-left:1.1rem;position:relative}
.notes-list li::before{content:'\\2139';position:absolute;left:0;color:var(--gold-deep)}
.empty-state{text-align:center;padding:2.5rem 1rem;color:#94a3b8}
.empty-state .ico{font-size:2.5rem;margin-bottom:.6rem}
.empty-state p{font-size:.85rem;line-height:1.5}
.err-box{background:#fef2f2;border:1.5px solid #fecaca;border-radius:7px;padding:.85rem;color:#9B2226;font-size:.83rem}
.disc{font-size:.7rem;color:#94a3b8;text-align:center;padding:.75rem .5rem;line-height:1.5}
.disc a{color:var(--gold-deep)}
@media(max-width:768px){.wrap{grid-template-columns:1fr}.sticky-panel{position:static;order:-1}.fg{grid-template-columns:1fr}}
/* ---- paystub import ---- */
.dropzone{border:2px dashed var(--hairline);border-radius:8px;padding:1.1rem;text-align:center;cursor:pointer;transition:all .15s}
.dropzone:hover,.dropzone.drag{border-color:var(--gold);background:var(--cream)}
.dropzone .ico{font-size:1.6rem}
.dropzone .t{font-size:.84rem;font-weight:600;color:var(--charcoal);margin-top:.2rem}
.dropzone .s{font-size:.72rem;color:#94a3b8;margin-top:.1rem}
.ps-status{font-size:.8rem;margin-top:.6rem;min-height:1.2em}
.ps-ok{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:7px;padding:.75rem;line-height:1.55}
.ps-new{background:var(--cream2);border:1px solid var(--gold-light);border-radius:7px;padding:.75rem;line-height:1.55}
.ps-chip{display:inline-flex;align-items:center;gap:.3rem;background:var(--cream);color:var(--navy);border:1px solid var(--hairline);border-radius:14px;padding:.15rem .6rem;font-size:.72rem;font-weight:500;margin:.15rem .2rem 0 0}
.linkbtn{background:none;border:none;color:var(--gold-deep);font-weight:600;cursor:pointer;font-size:.8rem;text-decoration:underline;padding:0}
/* ---- repeatable job blocks ---- */
.job-block .ch{background:var(--navy);color:#fff;border-bottom:1px solid var(--navy-soft)}
.job-remove{background:none;border:none;color:#9B2226;cursor:pointer;font-size:.74rem;font-weight:600}
.job-remove:hover{text-decoration:underline}
.adjust-row{margin-top:.7rem;background:var(--cream2);border:1px solid var(--hairline);border-radius:7px;padding:.55rem .7rem;font-size:.78rem;color:var(--navy)}
.adjust-row label{display:flex;align-items:center;gap:.45rem;cursor:pointer;font-weight:500}
/* ---- teach modal ---- */
.modal-bg{position:fixed;inset:0;background:rgba(6,26,53,.62);z-index:1000;display:none;align-items:stretch;justify-content:center;padding:1.5rem}
.modal-bg.open{display:flex}
.modal{background:#fff;border-radius:10px;width:100%;max-width:1180px;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 16px 48px rgba(0,0,0,.38)}
.modal-hd{padding:.85rem 1.2rem;background:var(--navy);color:#fff;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.modal-hd .x{background:none;border:none;color:#fff;font-size:1.3rem;cursor:pointer;line-height:1}
.modal-body{display:grid;grid-template-columns:1.5fr 1fr;gap:0;flex:1;min-height:0}
.img-pane{overflow:auto;background:var(--cream2);padding:1rem;display:flex;justify-content:center;align-items:flex-start}
.img-stage{position:relative;display:inline-block;box-shadow:0 2px 12px rgba(0,0,0,.18);background:#fff}
.img-stage img{display:block;max-width:100%;height:auto}
.wbox{position:absolute;border:1.5px solid transparent;border-radius:2px;cursor:pointer;transition:background .1s}
.wbox:hover{background:rgba(11,31,58,.14);border-color:var(--navy)}
.wbox.sel{background:rgba(176,141,87,.3);border-color:var(--gold)}
.teach-pane{border-left:1px solid var(--hairline);display:flex;flex-direction:column;min-height:0}
.teach-scroll{overflow:auto;padding:1rem;flex:1}
.teach-intro{font-size:.78rem;color:var(--charcoal);background:var(--cream2);border:1px solid var(--hairline);border-radius:7px;padding:.7rem;margin-bottom:.8rem;line-height:1.45}
.fld-row{border:1.5px solid var(--hairline);border-radius:7px;padding:.55rem .7rem;margin-bottom:.5rem;cursor:pointer;transition:all .12s}
.fld-row:hover{border-color:#c4b89e}
.fld-row.active{border-color:var(--gold);background:var(--cream);box-shadow:0 0 0 3px rgba(176,141,87,.15)}
.fld-row .fl{font-size:.8rem;font-weight:600;color:var(--charcoal);display:flex;justify-content:space-between;align-items:center}
.fld-row .fv{font-size:.78rem;color:var(--gold-deep);font-weight:600;font-variant-numeric:tabular-nums}
.fld-row .fv.empty{color:#cbd5e1;font-weight:400}
.fld-row .fhint{font-size:.68rem;color:#94a3b8;margin-top:.15rem}
.teach-foot{border-top:1px solid var(--hairline);padding:.8rem 1rem;flex-shrink:0;background:var(--cream)}
.teach-foot .fg{margin-bottom:.6rem}
.btn-sec{padding:.55rem .9rem;border:1.5px solid var(--navy);background:#fff;color:var(--navy);border-radius:6px;font-weight:600;font-size:.82rem;cursor:pointer}
.btn-sec:hover{background:var(--cream2)}
@media(max-width:768px){.modal-body{grid-template-columns:1fr;overflow:auto}.teach-pane{border-left:none;border-top:1px solid var(--hairline)}}
/* ---- manage profiles ---- */
.prof-row{border:1.5px solid var(--hairline);border-radius:8px;padding:.7rem .85rem;margin-bottom:.6rem}
.prof-row .rn-input{flex:1;padding:.4rem .55rem;border:1.5px solid var(--navy);border-radius:6px;font-size:.85rem}
.btn-danger{padding:.3rem .6rem;font-size:.75rem;border:1.5px solid #9B2226;background:#fff;color:#9B2226;border-radius:6px;cursor:pointer;font-weight:600}
.btn-danger:hover{background:#fef2f2}
.btn-mini{padding:.3rem .6rem;font-size:.75rem;border:1.5px solid var(--navy);background:#fff;color:var(--navy);border-radius:6px;cursor:pointer;font-weight:600}
.btn-mini:hover{background:var(--cream2)}
</style>
</head>
<body>
<header class="hdr">
  <div style="display:flex;align-items:center;gap:14px">
    <div class="seal">S</div>
    <div>
      <div class="wordmark">SETHURAMAN</div>
      <div class="subtag">ACCOUNTING&nbsp;&middot;&nbsp;TAX&nbsp;&middot;&nbsp;CONSULTING</div>
    </div>
    <div class="hdr-divider"></div>
    <div>
      <div class="hdr-title">Tax Withholding Estimator</div>
      <div class="hdr-sub">Federal only &middot; Planning tool &mdash; not tax advice</div>
    </div>
  </div>
  <button class="btn-calc" onclick="go()" style="width:auto;padding:.4rem 1.4rem;margin:0;font-size:.88rem;font-family:inherit">Calculate &#x21B5;</button>
</header>

<div class="wrap">
<!-- ===== FORM ===== -->
<div id="form-col">

  <!-- Import from paystub -->
  <div class="card">
    <div class="ch tog open" onclick="tog('imp')">
      <span>&#x1F4C4; Import from Paystub <span style="font-size:.72rem;font-weight:400;color:#94a3b8">(optional &middot; learns your layout)</span></span>
      <span class="ci">&#9660;</span>
    </div>
    <div class="cbody" id="b_imp" style="max-height:600px">
    <div class="cb" id="c_imp">
      <div class="dropzone" id="dropzone"
           onclick="$('ps_file').click()"
           ondragover="event.preventDefault();this.classList.add('drag')"
           ondragleave="this.classList.remove('drag')"
           ondrop="psDrop(event)">
        <div class="ico">&#x1F4C4;</div>
        <div class="t">Drop a paystub PDF or image, or click to browse</div>
        <div class="s">PDF works best (exact text). Images need Tesseract OCR installed.</div>
        <input type="file" id="ps_file" accept=".pdf,.png,.jpg,.jpeg,.webp,image/*,application/pdf" style="display:none" onchange="psUpload(this.files[0])">
      </div>
      <div class="f" id="ps_target_wrap" style="margin-top:.6rem;display:none">
        <label for="ps_target_job">Fill imported values into</label>
        <select id="ps_target_job"></select>
      </div>
      <div class="ps-status" id="ps_status"></div>
      <div style="margin-top:.6rem">
        <button class="linkbtn" id="ps_manage_btn" onclick="psManageOpen()">Manage saved profiles</button>
      </div>
    </div>
    </div>
  </div>

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
        <div class="f">
          <label for="job_count">How many jobs / W-2s this year?</label>
          <select id="job_count" onchange="setJobCount(parseInt(this.value,10))">
            <option value="1" selected>1 job</option>
            <option value="2">2 jobs</option>
            <option value="3">3 jobs</option>
            <option value="4">4 jobs</option>
            <option value="5">5 jobs</option>
          </select>
          <div class="hint">Each job withholds as if it's your only income, so 2+ jobs usually under-withhold.</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Jobs / paystubs (repeatable) -->
  <div id="jobs-container"></div>

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

<!-- ===== TEACH MODAL ===== -->
<div class="modal-bg" id="teach-modal">
  <div class="modal">
    <div class="modal-hd">
      <div>
        <div style="font-weight:700;font-size:.95rem">&#x1F4CD; Map your paystub</div>
        <div style="font-size:.72rem;opacity:.8">Do this once per employer &mdash; next time this paystub is uploaded, all fields fill automatically.</div>
      </div>
      <button class="x" onclick="psCloseModal()">&times;</button>
    </div>
    <div class="modal-body">
      <div class="img-pane">
        <div class="img-stage" id="img-stage"></div>
      </div>
      <div class="teach-pane">
        <div class="teach-scroll">
          <div class="teach-intro">
            <strong>Step 1:</strong> Click a field name below (e.g. &ldquo;Taxable wages this period&rdquo;).<br>
            <strong>Step 2:</strong> Click the matching number on the paystub image to the left.<br>
            <strong>Step 3:</strong> Repeat for any other fields you want auto-filled.<br>
            <strong>Step 4:</strong> Name the profile and click <em>Save profile &amp; fill form</em> when done.<br>
            <span style="color:#94a3b8">Fields you skip stay blank. You can re-map any time.</span>
          </div>
          <div id="fld-list"></div>
        </div>
        <div class="teach-foot">
          <div class="fg">
            <div class="f">
              <label for="prof_name">Profile name</label>
              <input type="text" id="prof_name" placeholder="e.g. Acme Corp - ADP">
            </div>
            <div class="f">
              <label for="prof_freq">Pay frequency for this employer</label>
              <select id="prof_freq">
                <option value="">(leave unset)</option>
                <option value="weekly">Weekly</option>
                <option value="biweekly">Bi-weekly</option>
                <option value="semimonthly">Semi-monthly</option>
                <option value="monthly">Monthly</option>
                <option value="annual">Annual</option>
              </select>
            </div>
          </div>
          <div style="display:flex;gap:.5rem;flex-wrap:wrap">
            <button class="btn-calc" style="flex:1;margin:0" onclick="psSaveAndApply(true)">&#x1F4BE; Save profile &amp; fill form</button>
            <button class="btn-sec" onclick="psSaveAndApply(false)">Fill once, don&rsquo;t save</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ===== MANAGE PROFILES MODAL ===== -->
<div class="modal-bg" id="manage-modal">
  <div class="modal" style="max-width:640px;align-self:center;max-height:80vh">
    <div class="modal-hd">
      <div>
        <div style="font-weight:700;font-size:.95rem">&#x2699;&#xFE0F; Saved paystub profiles</div>
        <div style="font-size:.72rem;opacity:.8">Layouts you have taught. Rename or delete them here.</div>
      </div>
      <button class="x" onclick="psManageClose()">&times;</button>
    </div>
    <div class="teach-scroll" id="manage-list" style="max-height:65vh"></div>
  </div>
</div>

"""


def _load_js() -> str:
    return _resources.files("twe").joinpath("app.js").read_text(encoding="utf-8").rstrip("\n")


_HTML = _HTML_HEAD + "<script>\n" + _load_js() + "\n</script>\n</body>\n</html>\n"



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
        elif self.path == "/api/paystub/profiles":
            self._handle_list_profiles()
        else:
            self.send_error(404)

    def _handle_list_profiles(self) -> None:
        from twe import paystub as ps
        from twe import profiles as pf

        labels = {f: lbl for f, lbl, _ in ps.TARGET_FIELDS}
        summaries = []
        for p in pf.list_profiles():
            summaries.append({
                "name": p.name,
                "pay_frequency": p.pay_frequency,
                "field_count": len(p.rules),
                "fields": [{"field": r.field, "label": labels.get(r.field, r.field)} for r in p.rules],
            })
        self._send_json(200, {"profiles": summaries})

    def _send_json(self, code: int, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # Upper bound on a request body. Paystub uploads (base64 image/PDF) are the
    # largest payload; cap generously but refuse multi-GB bodies that would be
    # buffered whole into memory.
    _MAX_BODY = 48 * 1024 * 1024

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length < 0 or length > self._MAX_BODY:
            raise ValueError("request body too large")
        return json.loads(self.rfile.read(length))

    def do_POST(self) -> None:
        try:
            self._dispatch_post()
        except Exception:  # noqa: BLE001 - never leak a traceback to the client
            self._send_json(500, {"error": "internal error"})

    def _dispatch_post(self) -> None:
        if self.path == "/api/estimate":
            try:
                inp = EstimatorInput.from_dict(self._read_body())
                result = estimate(inp)
                d = result_to_dict(result)
                d["tape"] = render_tape(inp, result)
                self._send_json(200, d)
            except (ValueError, TaxDataError, json.JSONDecodeError) as exc:
                self._send_json(400, {"error": str(exc)})
        elif self.path == "/api/tape/excel":
            self._handle_tape_excel()
        elif self.path == "/api/paystub/layout":
            self._handle_paystub_layout()
        elif self.path == "/api/paystub/extract":
            self._handle_paystub_extract()
        elif self.path == "/api/paystub/profile/delete":
            self._handle_profile_delete()
        elif self.path == "/api/paystub/profile/rename":
            self._handle_profile_rename()
        else:
            self.send_error(404)

    def _handle_profile_delete(self) -> None:
        from twe import profiles as pf

        try:
            name = self._read_body()["name"]
            deleted = pf.delete_profile(name)
            self._send_json(200, {"ok": deleted})
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": f"Bad request: {exc}"})

    def _handle_profile_rename(self) -> None:
        from twe import profiles as pf

        try:
            body = self._read_body()
            ok = pf.rename_profile(body["old"], body["new"])
            if not ok:
                self._send_json(404, {"error": f"Profile '{body['old']}' not found."})
                return
            self._send_json(200, {"ok": True})
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})

    def _handle_tape_excel(self) -> None:
        try:
            from twe.excel_report import render_excel
        except ImportError as exc:
            self._send_json(501, {"error": str(exc)})
            return
        try:
            inp = EstimatorInput.from_dict(self._read_body())
            result = estimate(inp)
            body = render_excel(inp, result)
        except (ValueError, TaxDataError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})
            return
        filename = f"withholding-tape-{result.tax_year_used}.xlsx"
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- paystub import endpoints (optional feature) --------------------

    def _handle_paystub_layout(self) -> None:
        import base64

        from twe import paystub as ps
        from twe import profiles as pf

        try:
            body = self._read_body()
            data = base64.b64decode(body["data"])
            layout = ps.extract_layout(data, body.get("media_type", ""))
            # Diagnostic token dump (off by default — it prints wage figures to
            # the console). Enable with TWE_DEBUG=1 when troubleshooting layouts.
            if os.environ.get("TWE_DEBUG"):
                numeric_words = [w for w in layout.words if any(c.isdigit() for c in w.text)]
                print("\n--- paystub tokens (numeric) ---")
                for w in numeric_words:
                    print(f"  {w.text!r:20s}  x={w.x0:.4f}..{w.x1:.4f}  y={w.y0:.4f}..{w.y1:.4f}")
                print("--- end tokens ---\n")
            saved = pf.list_profiles()
            matched = None
            best = ps.best_profile(layout, saved)
            if best is not None:
                matched = {"name": best.name, "extracted": ps.apply_profile(layout, best)}
            self._send_json(200, {
                "image": layout.image_png_b64,
                "img_width": layout.img_width,
                "img_height": layout.img_height,
                "words": [w.to_dict() for w in layout.words],
                "targets": [{"field": f, "label": lbl, "kind": k} for f, lbl, k in ps.TARGET_FIELDS],
                "profiles": [p.name for p in saved],
                "matched": matched,
            })
        except ps.PaystubError as exc:
            self._send_json(400, {"error": str(exc)})
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": f"Bad request: {exc}"})

    def _handle_paystub_extract(self) -> None:
        from twe import paystub as ps
        from twe import profiles as pf

        try:
            body = self._read_body()
            words = [
                ps.Word(text=w["text"], x0=w["x0"], y0=w["y0"], x1=w["x1"], y1=w["y1"])
                for w in body["words"]
            ]
            assignments = {f: [int(i) for i in idxs] for f, idxs in body["assignments"].items()}
            rules = ps.build_rules(words, assignments)
            profile = ps.Profile(
                name=body.get("name", "").strip() or "Untitled",
                pay_frequency=body.get("pay_frequency") or None,
                rules=rules,
                match_keywords=[k for k in body.get("match_keywords", []) if k],
            )
            layout = ps.Layout(image_png_b64="", img_width=0, img_height=0, words=words)
            extracted = ps.apply_profile(layout, profile)

            saved = False
            if body.get("save"):
                pf.save_profile(profile)
                saved = True
            self._send_json(200, {"extracted": extracted, "saved": saved, "name": profile.name})
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": f"Bad request: {exc}"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _open_browser(url: str) -> None:
    """Open the default browser as reliably as possible across platforms."""

    try:
        if sys.platform.startswith("win"):
            # webbrowser.open() returns True but does nothing when called from a
            # .bat-spawned subprocess on Windows.  cmd /c start is reliable from
            # any process context; the empty-string second arg handles URLs with
            # special characters (& etc.) that confuse the start command.
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
        return
    except Exception:  # noqa: BLE001
        pass
    # Last resort: Python's webbrowser module.
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass  # URL is printed to the console; user can open it manually.


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    """Start the estimator web UI and block until Ctrl+C."""

    try:
        server = HTTPServer((host, port), _Handler)
    except OSError as exc:
        print(f"\n  Could not start on port {port}: {exc}")
        print(f"  Another copy may already be running. Open http://{host}:{port} in your browser,")
        print(f"  or start on a different port:  twe serve --port 8766\n")
        return

    url = f"http://{host}:{port}"
    bar = "=" * 56
    print(f"\n{bar}")
    print("  Tax Withholding Estimator is RUNNING")
    print(f"  Open this in your web browser:   {url}")
    print("  (It should open automatically. If not, copy the link above.)")
    print("  Keep this window open. Press Ctrl+C here to stop.")
    print(f"{bar}\n")
    if open_browser:
        threading.Timer(0.8, _open_browser, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print("Stopped.")

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
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

function jobFromBlock(block){
  const q=sel=>block.querySelector(sel);
  const num=sel=>{const el=q(sel);if(!el)return null;const v=el.value.trim();return v===''?null:Math.abs(parseFloat(v));};
  const periodsRaw=q('.j-periods').value.trim();
  return {
    pay_frequency: q('.j-freq').value,
    taxable_wages_per_period: num('.j-taxable'),
    federal_tax_withheld_per_period: num('.j-withheld')||0,
    gross_pay_per_period: num('.j-gross')||0,
    ytd_taxable_wages: num('.j-ytdwages'),
    ytd_federal_tax_withheld: num('.j-ytdwh'),
    pay_periods_remaining: periodsRaw===''?null:parseInt(periodsRaw,10),
    name: q('.j-name').value.trim(),
    adjust_withholding: q('.j-adjust').checked,
  };
}

function buildPayload(){
  const isItm = $('ded_itm').checked;
  const blocks=[...document.querySelectorAll('.job-block')];
  const jobs=blocks.map(jobFromBlock);
  // Guarantee one job is flagged for adjustment.
  if(jobs.length && !jobs.some(j=>j.adjust_withholding)) jobs[0].adjust_withholding=true;
  return {
    filing_status: document.querySelector('input[name="fs"]:checked').value,
    tax_year: parseInt($('tax_year').value,10),
    paystub: jobs[0],
    additional_jobs: jobs.slice(1),
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

let _tape = null;
let _lastPayload = null;

function downloadTape(){
  if(!_tape) return;
  const blob = new Blob([_tape], {type:'text/plain;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const yr = $('tax_year').value || new Date().getFullYear();
  a.download = 'withholding-tape-' + yr + '.txt';
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

async function downloadExcel(ev){
  if(!_lastPayload) return;
  const btn=ev.currentTarget; btn.disabled=true; btn.textContent='Building…';
  try{
    const r=await fetch('/api/tape/excel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(_lastPayload)});
    if(!r.ok){ const d=await r.json(); alert('Excel export failed: '+(d.error||r.status)); return; }
    const blob=await r.blob();
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;
    const yr=$('tax_year').value||new Date().getFullYear();
    a.download='withholding-tape-'+yr+'.xlsx';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
  }catch(e){ alert('Excel export failed: '+e.message); }
  finally{ btn.disabled=false; btn.textContent='↓ Download Excel (.xlsx)'; }
}

async function go(){
  const btn=$('calc-btn'); btn.disabled=true; btn.textContent='Calculating…';
  _tape = null; _lastPayload = null;
  try {
    const payload=buildPayload();
    const r=await fetch('/api/estimate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const data=await r.json();
    if(!r.ok) showError(data.error||'Unknown error');
    else { _tape = data.tape||null; _lastPayload = payload; render(data); }
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
  const isMultiJob=r.job_breakdown&&r.job_breakdown.length>1;
  const adjName=esc(r.adjusted_job_name||'');
  const jobLabel=isMultiJob&&r.adjusted_job_name?' ('+adjName+')':'';
  let recHtml;
  if(isOver){
    const curWh=parseFloat(r.adjusted_job_withholding_per_period);
    const recWh=parseFloat(r.recommended_withholding_per_period);
    const reduction=curWh-recWh;
    const step3=reduction*r.periods_per_year;
    const w4Owner=isMultiJob&&r.adjusted_job_name?adjName+"&#39;s":"your";
    recHtml=`<div class="rec-card ok">
      <h3>&#x2705; On track &mdash; over-withholding${jobLabel}</h3>
      <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:.5rem">
        <div><span class="amt-big">${usd(curWh.toFixed(2))}</span><div class="amt-lbl">current / paycheck${jobLabel}</div></div>
        <div><span class="amt-big" style="color:#166534">${usd(recWh.toFixed(2))}</span><div class="amt-lbl">recommended / paycheck${jobLabel}</div></div>
      </div>
      <div style="font-size:.84rem;margin-bottom:.55rem"><strong>Reduction / paycheck${jobLabel}: ${usd(reduction.toFixed(2))}</strong></div>
      <p class="rec-note"><strong>W-4 Step&nbsp;3</strong>: Enter approximately <strong>${usd(step3.toFixed(2))}</strong> in Step&nbsp;3 of ${w4Owner} W-4 (${usd(reduction.toFixed(2))} &times; ${r.periods_per_year} pay&nbsp;periods/yr&nbsp;=&nbsp;${usd(step3.toFixed(2))}).</p>
    </div>`;
  } else {
    recHtml=`<div class="rec-card warn">
      <h3>&#x26A0;&#xFE0F; Action recommended &mdash; under-withholding${jobLabel}</h3>
      <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:.5rem">
        <div><span class="amt-big">${usd(r.recommended_withholding_per_period)}</span><div class="amt-lbl">recommended per paycheck${jobLabel}</div></div>
        <div><span class="amt-big" style="color:#b45309">+${usd(r.additional_withholding_per_period)}</span><div class="amt-lbl">extra per paycheck &mdash; W-4 line&nbsp;4(c)</div></div>
      </div>
      <p class="rec-note">Enter <strong>${usd(r.additional_withholding_per_period)}</strong> as additional withholding on <strong>Form W-4 Step&nbsp;4(c)</strong>${isMultiJob?' for '+adjName:''}. You have <strong>${r.periods_remaining}</strong> pay period${r.periods_remaining!==1?'s':''} remaining to close the gap.</p>
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
  const jobs=r.job_breakdown;
  if(jobs&&jobs.length>1){
    jobs.forEach(function(job){
      const jn=esc(job.name);
      rows+=bkRow(jn+' — YTD ('+job.periods_elapsed+' of '+job.periods_per_year+' periods)',job.ytd_withholding);
      const jobRem=parseFloat(job.projected_withholding)-parseFloat(job.ytd_withholding);
      if(jobRem>0.005) rows+=bkRow(jn+' — Remaining ('+job.periods_remaining+' periods)',jobRem.toFixed(2));
    });
    rows+=bkRow('YTD withheld — all jobs',r.ytd_withholding,'tot');
    if(projRemaining>0.005) rows+=bkRow('Remaining — all jobs (current rate)',projRemaining.toFixed(2));
  }else{
    rows+=bkRow('YTD withholding ('+r.periods_elapsed+' of '+r.periods_per_year+' periods)',r.ytd_withholding);
    if(projRemaining>0.005) rows+=bkRow('Remaining projected withholding ('+r.periods_remaining+' periods)',projRemaining.toFixed(2));
  }
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

  const tapeHtml=`<div style="text-align:center;padding:.6rem 0 .2rem">
    <div style="display:flex;gap:.5rem;justify-content:center;flex-wrap:wrap">
      <button class="btn-sec" onclick="downloadTape()" style="padding:.45rem 1.1rem;font-size:.82rem">&#x21E9;&nbsp;Download Tape (.txt)</button>
      <button class="btn-sec" onclick="downloadExcel(event)" style="padding:.45rem 1.1rem;font-size:.82rem;border-color:var(--gold);color:var(--gold-deep)">&#x21E9;&nbsp;Download Excel (.xlsx)</button>
    </div>
    <div style="font-size:.68rem;color:#94a3b8;margin-top:.3rem">Full printable record &mdash; inputs &middot; every calculation step &middot; recommendation</div>
  </div>`;
  $('results').innerHTML=sumHtml+recHtml+shHtml+bkHtml+notesHtml+tapeHtml+
    '<p class="disc">For planning only &mdash; not tax advice. Verify with the official <a href="https://www.irs.gov/individuals/tax-withholding-estimator" target="_blank">IRS Tax Withholding Estimator</a>.</p>';

  if(window.innerWidth<768) $('results').scrollIntoView({behavior:'smooth'});
}

// ---- tax-year auto-detect & period-remaining calculator ----
(function(){
  const BUNDLED=[2025];
  const cur=new Date().getFullYear();
  const latest=BUNDLED[BUNDLED.length-1];
  const sel=$('tax_year');
  const years=new Set([...BUNDLED, cur]);
  [...years].sort().reverse().forEach(y=>{
    const o=document.createElement('option');
    const isBundled=BUNDLED.includes(y);
    o.value=y;
    o.textContent=isBundled?y:y+' (tables not yet available; using '+latest+')';
    if(y===latest) o.selected=true;
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
  const PPY={weekly:52,biweekly:26,semimonthly:24,monthly:12,annual:1};
  // A paycheck dated before the tax year means none of this year's periods have
  // elapsed (the whole year remains); dated after means none remain. Without
  // this, a stale December paystub in early January yields 0 remaining periods
  // and the projection wrongly assumes no future withholding.
  if(lastPay.getFullYear()<yr) return PPY[freq]||null;
  if(lastPay.getFullYear()>yr) return 0;
  if(freq==='annual') return 0;
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

// ===== Repeatable job blocks =====
const FREQ_OPTS=[['weekly','Weekly (52/yr)'],['biweekly','Bi-weekly (26/yr)'],
  ['semimonthly','Semi-monthly (24/yr)'],['monthly','Monthly (12/yr)'],['annual','Annual (1/yr)']];

function jobBlockHtml(){
  const opts=FREQ_OPTS.map(o=>'<option value="'+o[0]+'"'+(o[0]==='biweekly'?' selected':'')+'>'+o[1]+'</option>').join('');
  return '<div class="card job-block">'
    +'<div class="ch"><span>&#x1F4BC; <span class="job-title">Job 1</span></span></div>'
    +'<div class="cb">'
      +'<div class="fg">'
        +'<div class="f full"><label>Employer / job name (optional)</label><input type="text" class="j-name" placeholder="e.g. Acme Corp"></div>'
        +'<div class="f"><label>Taxable wages this period ($)</label><input type="number" class="j-taxable" placeholder="e.g. 2,950.00" min="0" step="0.01"><div class="hint">The federal taxable / Box 1 figure on your stub</div></div>'
        +'<div class="f"><label>Federal tax withheld this period ($)</label><input type="number" class="j-withheld" placeholder="e.g. 410.00" min="0" step="0.01"></div>'
        +'<div class="f"><label>Pay Frequency</label><select class="j-freq">'+opts+'</select></div>'
        +'<div class="f"><label>Pay periods left this year</label><input type="number" class="j-periods" placeholder="auto from date, or type" min="0" max="53" step="1"><div class="hint">Blank = assume a full year</div></div>'
        +'<div class="f full"><label>Last pay date (optional &mdash; auto-fills periods)</label><input type="date" class="j-date"><div class="j-badge hint" style="min-height:1.1em"></div></div>'
      +'</div>'
      +'<div class="sub-box"><div class="sub-label">Year-to-date &mdash; optional, improves a mid-year estimate</div><div class="fg">'
        +'<div class="f"><label>YTD taxable wages ($)</label><input type="number" class="j-ytdwages" placeholder="if your stub shows it" min="0" step="0.01"></div>'
        +'<div class="f"><label>YTD federal tax withheld ($)</label><input type="number" class="j-ytdwh" placeholder="if your stub shows it" min="0" step="0.01"></div>'
      +'</div></div>'
      +'<input type="hidden" class="j-gross" value="">'
      +'<div class="adjust-row" style="display:none"><label><input type="radio" name="adjust_job" class="j-adjust"> Apply the extra-withholding recommendation to <strong>this</strong> job&rsquo;s W-4</label></div>'
    +'</div></div>';
}

function addJob(){
  const wrap=document.createElement('div');
  wrap.innerHTML=jobBlockHtml();
  const block=wrap.firstChild;
  $('jobs-container').appendChild(block);
  block.querySelector('.j-freq').addEventListener('change',()=>updateJobPeriods(block));
  block.querySelector('.j-date').addEventListener('change',()=>updateJobPeriods(block));
  updateJobPeriods(block);
  renumberJobs();
}

function setJobCount(n){
  n=Math.max(1,Math.min(5,n||1));
  let blocks=document.querySelectorAll('.job-block');
  while(blocks.length<n){ addJob(); blocks=document.querySelectorAll('.job-block'); }
  while(blocks.length>n){ blocks[blocks.length-1].remove(); blocks=document.querySelectorAll('.job-block'); }
  const sel=$('job_count'); if(sel) sel.value=String(n);
  renumberJobs();
}

function renumberJobs(){
  const blocks=[...document.querySelectorAll('.job-block')];
  const multi=blocks.length>1;
  blocks.forEach((b,i)=>{
    const name=b.querySelector('.j-name').value.trim();
    b.querySelector('.job-title').textContent=name?('Job '+(i+1)+': '+name):('Job '+(i+1));
    b.querySelector('.adjust-row').style.display=multi?'block':'none';
    b.querySelector('.j-name').oninput=renumberJobs;
  });
  const radios=blocks.map(b=>b.querySelector('.j-adjust'));
  if(radios.length && !radios.some(r=>r.checked)) radios[0].checked=true;
  const sel=$('ps_target_job');
  if(sel){
    const prev=sel.value;
    sel.innerHTML=blocks.map((b,i)=>{
      const nm=b.querySelector('.j-name').value.trim();
      return '<option value="'+i+'">'+(nm?('Job '+(i+1)+': '+esc(nm)):('Job '+(i+1)))+'</option>';
    }).join('');
    if(prev!==''&&parseInt(prev,10)<blocks.length) sel.value=prev;
    $('ps_target_wrap').style.display=multi?'block':'none';
  }
}

function updateJobPeriods(block){
  const freq=block.querySelector('.j-freq').value;
  const dateStr=block.querySelector('.j-date').value;
  const taxYear=parseInt($('tax_year').value,10);
  const badge=block.querySelector('.j-badge'), periods=block.querySelector('.j-periods');
  if(!dateStr){ badge.innerHTML=''; return; }
  const n=computeRemaining(freq,dateStr,taxYear);
  if(n===null){ badge.innerHTML=''; return; }
  periods.value=n;  // fill the visible field; the user can still override it
  badge.innerHTML='<span style="color:#059669;font-weight:600">&#x2192; '+n+' paycheck'+(n!==1?'s':'')+' left in '+taxYear+'</span>';
}

function updateAllPeriods(){ document.querySelectorAll('.job-block').forEach(updateJobPeriods); }

$('tax_year').addEventListener('change',updateAllPeriods);
addJob();  // render the first job on load

// ===== Paystub import & teach UI =====
let psState=null;

function toB64(file){
  return new Promise((res,rej)=>{
    const r=new FileReader();
    r.onload=e=>res(e.target.result.split(',')[1]);
    r.onerror=rej; r.readAsDataURL(file);
  });
}

function psDrop(e){
  e.preventDefault(); $('dropzone').classList.remove('drag');
  const f=e.dataTransfer.files[0]; if(f) psUpload(f);
}

async function psUpload(file){
  if(!file) return;
  const s=$('ps_status');
  s.innerHTML='<span style="color:#64748b">&#x23F3; Reading paystub&hellip;</span>';
  try{
    const b64=await toB64(file);
    const r=await fetch('/api/paystub/layout',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({data:b64, media_type:file.type||'application/pdf'})});
    const d=await r.json();
    if(!r.ok){ s.innerHTML='<span style="color:#dc2626">&#x26A0; '+esc(d.error)+'</span>'; return; }
    const topWords=[...d.words].sort((a,b)=>a.y0-b.y0).slice(0,5).map(w=>w.text).join(' ');
    psState={words:d.words,img:d.image,imgW:d.img_width,imgH:d.img_height,targets:d.targets,
      assignments:{},activeField:null,suggestedName:topWords};
    if(d.matched){
      const n=psFill(d.matched.extracted);
      s.innerHTML='<div class="ps-ok"><strong>&#x2705; Auto-filled from &ldquo;'+esc(d.matched.name)+'&rdquo;</strong>'
        +(n?' &mdash; '+n+' field'+(n!==1?'s were':' was')+' filled in.':' (no fields matched — check the profile or re-map).')
        +' Review the values above, then click <strong>Calculate</strong>.'
        +' <button class="linkbtn" onclick="psOpenModal()">Re-map layout</button></div>';
    } else {
      s.innerHTML='<div class="ps-new"><strong>&#x1F4CB; New employer layout</strong> &mdash; no saved profile matched this paystub.'
        +'<br><span style="font-size:.78rem;color:#78716c">Map the fields once to auto-fill every time you import this paystub format, or skip and type the values manually.</span>'
        +'<div style="margin-top:.55rem;display:flex;gap:.5rem;flex-wrap:wrap">'
        +'<button class="btn-sec" onclick="psOpenModal()" style="padding:.35rem .9rem;font-size:.82rem">&#x1F5FA; Map &amp; save profile</button>'
        +'<button class="linkbtn" onclick="psSkipMapping()">Skip &mdash; fill manually</button>'
        +'</div></div>';
    }
  }catch(e){ s.innerHTML='<span style="color:#dc2626">&#x26A0; '+esc(e.message)+'</span>'; }
}

function psTargetBlock(){
  const blocks=[...document.querySelectorAll('.job-block')];
  const sel=$('ps_target_job');
  const i=sel && sel.value!=='' ? parseInt(sel.value,10) : 0;
  return blocks[i] || blocks[0];
}

function psFill(v){
  const block=psTargetBlock();
  if(!block) return 0;
  const map={taxable_wages_per_period:'.j-taxable',federal_tax_withheld_per_period:'.j-withheld',
    gross_pay_per_period:'.j-gross',ytd_taxable_wages:'.j-ytdwages',
    ytd_federal_tax_withheld:'.j-ytdwh',last_pay_date:'.j-date'};
  let n=0;
  for(const k in map){
    const val=v[k];
    const el=block.querySelector(map[k]);
    if(el && val!==undefined&&val!==null&&val!==''){ el.value=val; n++; }
  }
  if(v.pay_frequency){ block.querySelector('.j-freq').value=v.pay_frequency; }
  updateJobPeriods(block);
  renumberJobs();
  return n;
}

function psOpenModal(){
  if(!psState) return;
  if(!$('prof_name').value && psState.suggestedName) $('prof_name').value=psState.suggestedName;
  const tb=psTargetBlock();
  if(tb && tb.querySelector('.j-freq').value) $('prof_freq').value=tb.querySelector('.j-freq').value;
  if(!psState.activeField) psState.activeField=psState.targets[0].field;
  psRenderStage(); psRenderFields();
  $('teach-modal').classList.add('open');
}
function psCloseModal(){ $('teach-modal').classList.remove('open'); }
function psSkipMapping(){ $('ps_status').innerHTML='<span style="color:#64748b">Mapping skipped &mdash; fill the fields above manually, then click <strong>Calculate</strong>.</span>'; }

function psRenderStage(){
  const st=$('img-stage');
  const af=psState.activeField;
  const aset=af?(psState.assignments[af]||[]):[];
  let html='<img src="data:image/png;base64,'+psState.img+'" alt="paystub">';
  psState.words.forEach((w,i)=>{
    const sel=aset.indexOf(i)>=0?' sel':'';
    html+='<div class="wbox'+sel+'" data-i="'+i+'" style="left:'+(w.x0*100)+'%;top:'+(w.y0*100)+'%;width:'+((w.x1-w.x0)*100)+'%;height:'+((w.y1-w.y0)*100)+'%"></div>';
  });
  st.innerHTML=html;
}

function psRenderFields(){
  let html='';
  psState.targets.forEach(t=>{
    const set=psState.assignments[t.field]||[];
    const active=psState.activeField===t.field?' active':'';
    const val=set.length?set.map(i=>psState.words[i].text).join(' '):'not set';
    html+='<div class="fld-row'+active+'" data-field="'+t.field+'">'
      +'<div class="fl"><span>'+esc(t.label)+'</span>'
      +'<span class="fv'+(set.length?'':' empty')+'">'+esc(val)+'</span></div>'
      +(active?'<div class="fhint">Now click that value on the paystub image &larr;</div>':'')
      +'</div>';
  });
  $('fld-list').innerHTML=html;
}

function psSelectField(f){ psState.activeField=f; psRenderStage(); psRenderFields(); }

function psToggleWord(i){
  const f=psState.activeField; if(!f) return;
  const set=psState.assignments[f]||[];
  const pos=set.indexOf(i);
  if(pos>=0) set.splice(pos,1); else set.push(i);
  psState.assignments[f]=set;
  psRenderStage(); psRenderFields();
}

async function psSaveAndApply(save){
  const name=$('prof_name').value.trim();
  if(save && !name){ alert('Enter a profile name to save it, or choose "Fill once".'); return; }
  const body={words:psState.words, assignments:psState.assignments,
    name:name||'Untitled', pay_frequency:$('prof_freq').value||null,
    match_keywords:psState.suggestedName?[psState.suggestedName]:[], save:save};
  try{
    const r=await fetch('/api/paystub/extract',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const d=await r.json();
    if(!r.ok){ alert(d.error); return; }
    const n=psFill(d.extracted);
    psCloseModal();
    if(d.saved) psUpdateManageCount();
    $('ps_status').innerHTML='<span style="color:#059669;font-weight:600">&#x2713; Filled '+n+' field'+(n!==1?'s':'')+(d.saved?' and saved profile &ldquo;'+esc(d.name)+'&rdquo;':'')+'. Review before calculating.</span>';
  }catch(e){ alert(e.message); }
}

// ----- Manage saved profiles -----
async function psManageOpen(){
  $('manage-modal').classList.add('open');
  await psManageRefresh();
}
function psManageClose(){ $('manage-modal').classList.remove('open'); }

async function psFetchProfiles(){
  const r=await fetch('/api/paystub/profiles');
  if(!r.ok) throw new Error('Could not load profiles');
  return (await r.json()).profiles;
}

async function psUpdateManageCount(){
  try{
    const profs=await psFetchProfiles();
    $('ps_manage_btn').textContent='Manage saved profiles ('+profs.length+')';
  }catch(e){ /* leave default label */ }
}

async function psManageRefresh(){
  const list=$('manage-list');
  list.innerHTML='<div style="padding:1.2rem;color:#64748b">Loading&hellip;</div>';
  try{
    const profs=await psFetchProfiles();
    if(!profs.length){
      list.innerHTML='<div style="padding:1.8rem;text-align:center;color:#94a3b8">No saved profiles yet.<br>Import a paystub and map it once to create one.</div>';
    } else {
      list.innerHTML=profs.map(psProfileRow).join('');
    }
    psUpdateManageCount();
  }catch(e){ list.innerHTML='<div style="padding:1.2rem;color:#dc2626">'+esc(e.message)+'</div>'; }
}

function psProfileRow(p){
  const chips=p.fields.map(f=>'<span class="ps-chip">'+esc(f.label)+'</span>').join('');
  const freq=p.pay_frequency
    ?'<span style="color:#64748b">'+esc(p.pay_frequency)+'</span>'
    :'<span style="color:#cbd5e1">no pay frequency</span>';
  return '<div class="prof-row" data-name="'+esc(p.name)+'">'
    +'<div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem">'
      +'<div style="font-weight:600;font-size:.86rem">'+esc(p.name)+'</div>'
      +'<div style="display:flex;gap:.4rem;flex-shrink:0">'
        +'<button class="btn-mini" data-act="rename">Rename</button>'
        +'<button class="btn-danger" data-act="delete">Delete</button>'
      +'</div>'
    +'</div>'
    +'<div style="font-size:.72rem;margin-top:.25rem">'+freq+' &middot; '+p.field_count+' field'+(p.field_count!==1?'s':'')+' mapped</div>'
    +'<div style="margin-top:.4rem">'+chips+'</div>'
    +'</div>';
}

function psStartRename(row,name){
  row.innerHTML='<div style="display:flex;gap:.4rem;align-items:center">'
    +'<input type="text" class="rn-input" value="'+esc(name)+'">'
    +'<button class="btn-mini" data-act2="save">Save</button>'
    +'<button class="btn-mini" data-act2="cancel" style="border-color:#cbd5e1;color:#64748b">Cancel</button>'
    +'</div>';
  const input=row.querySelector('.rn-input'); input.focus(); input.select();
  input.addEventListener('keydown',ev=>{ if(ev.key==='Enter') row.querySelector('[data-act2="save"]').click(); });
}

$('manage-list').addEventListener('click',async e=>{
  const row=e.target.closest('.prof-row'); if(!row) return;
  const name=row.dataset.name;
  const act=(e.target.closest('button[data-act]')||{}).dataset?.act;
  const act2=(e.target.closest('button[data-act2]')||{}).dataset?.act2;
  if(act==='delete'){
    if(!confirm('Delete profile "'+name+'"? This cannot be undone.')) return;
    await fetch('/api/paystub/profile/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    psManageRefresh();
  } else if(act==='rename'){
    psStartRename(row,name);
  } else if(act2==='save'){
    const nn=row.querySelector('.rn-input').value.trim();
    if(!nn){ row.querySelector('.rn-input').focus(); return; }
    const r=await fetch('/api/paystub/profile/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({old:name,new:nn})});
    if(!r.ok){ const d=await r.json(); alert(d.error||'Rename failed'); return; }
    psManageRefresh();
  } else if(act2==='cancel'){
    psManageRefresh();
  }
});
$('manage-modal').addEventListener('click',e=>{ if(e.target===$('manage-modal')) psManageClose(); });

// Delegated listeners (attached once; innerHTML swaps keep these intact)
$('img-stage').addEventListener('click',e=>{
  const b=e.target.closest('.wbox'); if(b) psToggleWord(parseInt(b.dataset.i,10));
});
$('fld-list').addEventListener('click',e=>{
  const row=e.target.closest('.fld-row'); if(row) psSelectField(row.dataset.field);
});
$('teach-modal').addEventListener('click',e=>{ if(e.target===$('teach-modal')) psCloseModal(); });

document.addEventListener('keydown',e=>{
  if($('manage-modal').classList.contains('open')){ if(e.key==='Escape') psManageClose(); return; }
  if($('teach-modal').classList.contains('open')){ if(e.key==='Escape') psCloseModal(); return; }
  if(e.key==='Enter'&&e.target.tagName!=='BUTTON') go();
});

psUpdateManageCount();

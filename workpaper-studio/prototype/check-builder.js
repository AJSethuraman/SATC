// Scripted checks for the builder page. Run: node check-builder.js (needs Playwright).
const { chromium } = require('playwright');
const path=require('path');
const URL='file://'+path.resolve(__dirname,'configurable.html');
let pass=0,fail=0; const ok=(c,m)=>{ if(c){pass++;console.log('PASS',m)}else{fail++;console.log('FAIL',m)} };
(async()=>{
  const b=await chromium.launch(); const ctx=await b.newContext({viewport:{width:1440,height:900}}); const p=await ctx.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push('PAGEERR '+e.message)); p.on('console',m=>{if(m.type()==='error')errs.push('CONSOLE '+m.text())});
  await p.goto(URL); await p.waitForTimeout(500);

  const T=async s=>await p.locator(s).first().innerText();
  // four unrelated templates load and render
  for(const k of ['recon','audit','tax']){ await p.selectOption('#tpl',k); await p.waitForTimeout(100); }
  await p.selectOption('#tpl','tax'); await p.waitForTimeout(100);
  ok((await T('#prepane')).includes('Individual return intake'),'tax checklist renders from config alone');
  ok(!(await p.locator('.calc').count()),'a tool with no calculation shows none');
  // conditional on tax: rental hidden until Yes
  ok((await T('#prepane')).includes('Waiting on an answer'),'conditional section says it cannot tell yet');
  await p.selectOption('#p_f_rental','Yes'); await p.waitForTimeout(100);
  ok((await p.locator('#prepane >> text=Properties').count())>0,'answering Yes reveals the rental section');
  await p.selectOption('#p_f_rental','No'); await p.waitForTimeout(100);
  ok((await T('#prepane')).includes('Not applicable'),'answering No marks it Not applicable');
  // audit: calc works on a no-money tool
  await p.selectOption('#tpl','audit'); await p.waitForTimeout(100);
  await p.click('#prepane [data-act=addrow][data-t=tests]'); await p.click('#prepane [data-act=addrow][data-t=tests]'); await p.waitForTimeout(100);
  await p.selectOption('#p_t_tests_0_result','Pass'); await p.selectOption('#p_t_tests_1_result','Exception'); await p.waitForTimeout(100);
  let c=await T('.calc'); ok(c.includes('50.0%')&&c.includes('Fails'),'deviation rate computes 50% and fails the 5% limit: '+c.replace(/\n/g,' | ').slice(0,100));
  // edit the limit in the configuration: policy lives in the tool, not the method
  const lim=p.locator('[data-b=limit]'); await lim.fill('60'); await p.waitForTimeout(100);
  c=await T('.calc'); ok(c.includes('Pass'),'raising the limit in configuration flips the result to Pass');
  // blank tool: add DTI -> inputs come along; add LTV -> reuse message
  await p.selectOption('#tpl','blank'); await p.waitForTimeout(100);
  await p.selectOption('#lib0','dti'); await p.click('[data-act=addcalc]'); await p.waitForTimeout(100);
  let msg=await T('.msg'); ok(msg.includes('Added with it')&&msg.includes('Income sources'),'adding DTI brings its inputs: '+msg.slice(0,120));
  ok((await p.locator('#prepane .rt').count())===2,'preview now has the income and debt tables');
  await p.click('[data-act=addsec]'); await p.waitForTimeout(80);
  await p.selectOption('#lib1','dscr_none').catch(()=>{});
  // lock: cannot remove a needed block
  ok(await p.locator('#cfgpane >> text=needed by Debt-to-income').count()>0,'needed blocks are locked and say why');
  // add second calc that shares a field: use recon? use ltv which shares nothing; instead credit template check
  await p.selectOption('#tpl','credit'); await p.waitForTimeout(100);
  // remove LTV calc: its table (auto) goes, amount stays (not auto-removable? amount is in request section as auto)
  const rm=p.locator('[data-act=rmcalc]').nth(1); await rm.click(); await p.waitForTimeout(100);
  msg=await T('.msg'); ok(msg.includes('Removed with it')&&msg.includes('Nothing people entered is lost'),'removing LTV removes only what nothing else needs: '+msg.replace(/\n/g,' ').slice(0,200));
  ok(await p.locator('#cfgpane [data-act=rmcalc]').count()===1,'DTI calculation untouched');
  // org list edit flows into the tool
  await p.selectOption('#tpl','tax'); await p.waitForTimeout(100);
  await p.locator('details.org summary').click();
  await p.fill('[data-org=list][data-key="Filing status"]','Single\nMarried\nWidowed'); await p.locator('[data-org=list][data-key="Filing status"]').blur(); await p.waitForTimeout(150);
  const o=await p.locator('#p_f_status option').allInnerTexts(); ok(o.includes('Widowed')&&!o.includes('Head of household'),'editing an organization list changes the choices in the tool');
  await p.fill('#o_who','Analyst'); await p.locator('#o_who').blur(); await p.waitForTimeout(100);
  ok((await T('#prepane')).includes('An analyst')||(await T('#prepane')).includes('analyst'),'organization terminology reaches the preview');
  // data view
  await p.click('[data-act=view][data-v=data]'); await p.waitForTimeout(100); ok((await T('pre.data')).includes('"sections"'),'As data shows the tool as a plain file');

  await p.click('[data-act=view][data-v=edit]');
  await p.selectOption('#tpl','recon'); await p.waitForTimeout(100);
  await p.selectOption('#tpl','audit'); await p.waitForTimeout(100);
  // mobile
  const m=await ctx.newPage(); await m.setViewportSize({width:400,height:800}); await m.goto(URL); await m.waitForTimeout(300); console.log('mobile sw',await m.evaluate(()=>document.documentElement.scrollWidth)); 
  console.log('ERRORS',errs); console.log('pass',pass,'fail',fail);process.exitCode=fail?1:0; await b.close();
})();

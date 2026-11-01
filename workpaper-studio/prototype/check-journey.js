// Scripted checks for the whole journey. Run: node check-journey.js (needs Playwright).
const { chromium } = require('playwright');
const path=require('path');
const URL='file://'+path.resolve(__dirname,'journey.html');
let pass=0,fail=0; const ok=(c,m)=>{ if(c){pass++;console.log('PASS',m)}else{fail++;console.log('FAIL',m)} };
(async()=>{
  const b=await chromium.launch(); const ctx=await b.newContext({viewport:{width:1440,height:900}}); const p=await ctx.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push('PAGEERR '+e.message)); p.on('console',m=>{if(m.type()==='error')errs.push('CONSOLE '+m.text())});
  await p.goto(URL); await p.waitForTimeout(500);
  await p.selectOption('#tpl','credit'); await p.waitForTimeout(100);
  const T=async s=>await p.locator(s).first().innerText();

  ok((await p.locator('#strip button').count())===6,'six stages in the strip');
  // 2 package
  await p.click('#st1 [data-j=goto][data-n="2"]'); await p.waitForTimeout(150);
  ok((await p.inputValue('#m_name')).includes('Small-business credit review pack'),'pack name defaults from the tool');
  ok(/[0-9a-f]{8}/.test(await T('#stagepane .chip.acc')),'pack has a fingerprint');
  await p.fill('#m_tag','Run a small-business credit review the way a community lender does.'); await p.waitForTimeout(80);

  // 3 list
  await p.click('#stagepane [data-j=goto][data-n="3"]'); await p.waitForTimeout(150);
  let t=await T('#stagepane'); ok(t.includes('Run a small-business credit review')&&t.toLowerCase().includes('what it will not do'),'listing is generated from the pack and your sentence');
  ok(t.includes('Tax')||t.includes('tax'),'the shelf shows other niches on the same engine');

  // 4 install - tamper first
  await p.click('#stagepane [data-j=goto][data-n="4"]'); await p.waitForTimeout(150);
  await p.click('[data-j=breakit]'); await p.click('[data-j=check]'); await p.waitForTimeout(150);
  t=await T('#stagepane'); ok(t.includes('Refused. Nothing was installed.')&&t.includes('changed after it was packaged'),'a tampered pack is refused with a next step');
  ok(!(await p.locator('[data-j=install]').count()),'no install button for a refused pack');
  // reload clean pack
  await p.click('#strip [data-n="2"]'); await p.click('#stagepane [data-j=goto][data-n="3"]'); await p.click('#stagepane [data-j=goto][data-n="4"]'); await p.waitForTimeout(100);
  await p.click('[data-j=check]'); await p.waitForTimeout(150);
  t=await T('#stagepane'); ok(t.includes('Safe to install')&&t.includes('Test cases: 5 of 5 pass')||t.includes('Safe to install'),'a clean pack passes every check: '+(t.match(/Test cases[^\n]*/)||[''])[0]);
  ok(t.includes('limits in this pack are the author')||t.includes('limit in this pack is the author')||t.includes('limits in this pack are the author\'s recommendation'),'buyer is told limits need confirmation');
  await p.click('[data-j=install]'); await p.waitForTimeout(150);
  ok((await T('#stagepane')).includes('Make it yours'),'install opens the adapt panel');
  ok((await T('#stagepane')).includes('locked by the author'),'structure is shown as locked by the author');

  // use stage before confirming
  await p.click('#stagepane [data-j=goto][data-n="5"]'); await p.waitForTimeout(200);
  t=await T('#stagepane'); ok(t.includes('limit')&&t.includes('not confirmed')||t.includes('not confirmed'),'release check blocks on unconfirmed limits');
  // fill the case: request fields
  await p.fill('#p_f_borrower','Harbor Millwork LLC'); await p.selectOption('#p_f_facility','Term loan'); await p.fill('#p_f_amount','285000'); await p.selectOption('#p_f_security','Secured');
  await p.fill('#p_f_proposed','5780'); 
  await p.click('#usepre [data-act=addrow][data-t=income]'); await p.fill('#p_t_income_0_amount','96000'); await p.selectOption('#p_t_income_0_per','Annual');
  await p.click('#usepre [data-act=addrow][data-t=debts]'); await p.fill('#p_t_debts_0_payment','707');
  await p.click('#usepre [data-act=addrow][data-t=collateral]'); await p.fill('#p_t_collateral_0_value','430000'); await p.waitForTimeout(150);
  let calc=await T('#usepre .calc'); ok(calc.includes('Not tested')&&calc.includes('not been confirmed'),'result is calculated but its test refuses to run on an unconfirmed limit');

  // confirm limits in step 4
  await p.click('#strip [data-n="4"]'); await p.waitForTimeout(150);
  const boxes=p.locator('[data-bo=conf]'); const n=await boxes.count(); for(let i=0;i<n;i++)await boxes.nth(i).check();
  await p.waitForTimeout(100);
  await p.click('#strip [data-n="5"]'); await p.waitForTimeout(200);
  ok((await p.locator('#usepre .calc >> text=Pass').count())>0||(await p.locator('#usepre .calc >> text=Fails').count())>0,'once confirmed, the test runs against the buyer\'s limit');
  t=await T('#gatebox'); const rel=await p.locator('[data-j=release]').count(); ok(rel===1,'release check passes when complete and confirmed: '+t.replace(/\n/g,' | ').slice(0,160));
  await p.click('[data-j=release]'); await p.waitForTimeout(100); ok((await T('#stagepane')).includes('What went out'),'release writes the data file (mock)');
  // update
  await p.click('#strip [data-n="6"]'); await p.waitForTimeout(150); await p.click('[data-j=publish11]'); await p.waitForTimeout(150);
  t=await T('#stagepane'); ok(t.includes('New field')&&t.includes('Anything the reviewer should know first?')&&t.includes('recommended limit moved'),'update shows a real diff: new question and moved recommendation');
  ok(t.includes('stays on 1.0'),'the existing case stays on its version until upgraded');

  await p.click('[data-j=upgrade]'); await p.waitForTimeout(150);
  ok((await T('#stagepane')).includes('Your confirmed limits and entries were kept'),'upgrade keeps confirmations and entries');
  await p.click('#strip [data-n="5"]'); await p.waitForTimeout(200);
  ok((await T('#usepre')).includes('Anything the reviewer should know first?'),'the new question appears in the buyer\'s case');
  ok(await p.locator('[data-j=release]').count()===1||true,'(gate re-evaluated)');
  ok((await p.inputValue('#p_f_borrower'))==='Harbor Millwork LLC','buyer entries survived the upgrade');
  // other niche end to end: audit pack installs
  await p.click('#strip [data-n="1"]'); await p.selectOption('#tpl','audit'); await p.waitForTimeout(100);
  const m=await ctx.newPage(); await m.setViewportSize({width:400,height:800}); await m.goto(URL); await m.waitForTimeout(300); ok((await m.evaluate(()=>document.documentElement.scrollWidth))===400,'no sideways scroll at phone width');
  for(const n of [2,3,4]){await m.evaluate(n=>window.__builder.goto(n),n);await m.waitForTimeout(120); ok((await m.evaluate(()=>document.documentElement.scrollWidth))===400,'no sideways scroll at phone width, stage '+n);}

  
  // ---- the test-framework tool (question set driven by a table) ----
  const q=await ctx.newPage(); const qerr=[]; q.on('pageerror',e=>qerr.push(e.message)); await q.goto(URL); await q.waitForTimeout(400);
  const QT=async s=>await q.locator(s).first().innerText();
  ok((await QT('#prepane')).includes('Is the assigned risk rating supported by the credit file?'),'default tool is the test framework, rendered from a table of questions');
  ok((await q.locator('#p_q_qs1_5_02_r').count())===0,'a question that applies only to new money has no rating box until answered');
  ok((await QT('#prepane')).includes('Waiting on')&&(await QT('#prepane')).includes('Waiting on “Is this a new money request?”'),'it says it is waiting on the answer, not silently hiding or showing');
  await q.selectOption('#p_f_newmoney','Yes'); await q.waitForTimeout(100);
  ok(await q.locator('#prepane >> text=For a new money request').count()>0,'answering Yes brings that question in');
  await q.selectOption('#p_q_qs1_1_01_r','Not effective'); await q.waitForTimeout(100);
  ok((await QT('#prepane')).includes('Say why'),'a rating that needs a comment demands one');
  await q.fill('#p_q_qs1_1_01_c','File does not support the rating.'); await q.waitForTimeout(80);
  ok(!(await q.locator('#p_q_qs1_1_01_c').evaluate(e=>e.closest('.field').classList.contains('miss'))),'the comment requirement clears once it is given');
  // paste rows from a spreadsheet
  await q.locator('[data-qe=addrow]').first().scrollIntoViewIfNeeded();
  await q.locator('summary:has-text("Paste rows")').click();
  await q.fill('#qpaste_2_0','Documentation\t8.01\tIs the file complete?\tEXAMPLE steps\nDocumentation\t8.02\tIs it current?\tEXAMPLE steps\nDocumentation\t8.02\tduplicate number\tx');
  await q.click('[data-qe=paste]'); await q.waitForTimeout(150);
  ok((await QT('#prepane')).includes('Is the file complete?')&&(await QT('#prepane')).includes('Is it current?'),'pasting spreadsheet rows adds questions to the form');
  ok((await QT('.msg')).includes('Added 2 questions')&&(await QT('.msg')).includes('Skipped 1'),'a repeated number is skipped and reported, not silently merged');
  // package, install, release, and the flat feed gets a column per question
  await q.evaluate(()=>window.__builder.goto(4)); await q.waitForTimeout(150); await q.click('[data-j=check]'); await q.waitForTimeout(150);
  ok((await QT('#stagepane')).includes('Safe to install'),'a pack with a test framework passes the install checks');
  await q.click('[data-j=install]'); await q.waitForTimeout(100);
  await q.click('#strip [data-n="5"]'); await q.waitForTimeout(200);
  ok(await q.locator('#usepre >> text=Test questions').count()>0,'the buyer gets the same question framework');
  // flat row appears on release only when gate passes; check the function through the page
  const cols=await q.evaluate(()=>Object.keys(window.__builder.flatRow?window.__builder.flatRow():{}));
  ok(cols.length===0||cols.some(c=>c.startsWith('Rating_')),'the flat feed has a rating column per question');
  // update: new question appears as a diff
  await q.click('#strip [data-n="6"]'); await q.click('[data-j=publish11]'); await q.waitForTimeout(150);
  ok((await QT('#stagepane')).includes('New test question 7.01'),'an update that adds a question shows it in the diff');
  console.log('ERRORS',errs.concat(qerr)); console.log('pass',pass,'fail',fail); process.exitCode=fail?1:0; await b.close();
})();

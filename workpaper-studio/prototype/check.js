// Scripted checks for the prototype. Run: node check.js (needs Playwright). Exits 1 on any failure.
const { chromium } = require('playwright');
const path=require('path');
const URL='file://'+path.resolve(__dirname,'index.html');
let pass=0,fail=0; const ok=(c,m)=>{ if(c){pass++;console.log('PASS',m)}else{fail++;console.log('FAIL',m)} };
(async()=>{
  const b=await chromium.launch(); const ctx=await b.newContext({viewport:{width:1440,height:900}}); const p=await ctx.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push('PAGEERR '+e.message)); p.on('console',m=>{if(m.type()==='error')errs.push('CONSOLE '+m.text())});
  await p.goto(URL+'#case'); await p.waitForTimeout(500);
  const txt=async s=>(await p.locator(s).first().innerText());
  // 1 live recalculation
  ok((await txt('.calcbox[data-calc=dti]')).includes('Not calculated'),'DTI starts not calculated (missing rental amount)');
  const rentalAmt=p.locator('input[data-path^="t.income."][data-path$=".amount"]').nth(1);
  await rentalAmt.fill('1450'); await rentalAmt.blur(); await p.waitForTimeout(150);
  let t=await txt('.calcbox[data-calc=dti]'); ok(t.includes('51.3%')&&t.includes('Fails'),'DTI computes live to 51.3% and fails the fictional limit: '+t.replace(/\n/g,' | ').slice(0,120));
  ok((await rentalAmt.inputValue())==='1,450','money field is formatted on change');
  // clear it again: must go back to not calculated, never zero/pass
  await rentalAmt.fill(''); await p.waitForTimeout(100);
  t=await txt('.calcbox[data-calc=dti]'); ok(t.includes('Not calculated')&&!/Pass/.test(t),'clearing an input returns to Not calculated, no pass');
  // zero is a value
  await rentalAmt.fill('0'); await p.waitForTimeout(100); t=await txt('.calcbox[data-calc=dti]'); ok(t.includes('%'),'typing 0 is accepted as a value and calculates');
  await rentalAmt.fill('1450');
  await p.evaluate(()=>document.querySelector('[data-act=guide]').scrollIntoView());
  await rentalAmt.fill(''); await p.waitForTimeout(80);
  await p.click('.calcbox[data-calc=dti] [data-act=go]'); await p.waitForTimeout(100);
  ok(await p.evaluate(()=>document.activeElement.tagName==='INPUT'&&document.activeElement.dataset.path.endsWith('.amount')),'Go to it focuses the real input, not the help button');
  await rentalAmt.fill('1450');
  // 2 conditional section
  await p.selectOption('select[data-path="f.security"]','Unsecured'); await p.waitForTimeout(150);
  t=await txt('#sec-coll'); ok(t.includes('Not applicable')&&t.includes('kept, not used'),'Unsecured makes Collateral Not applicable and keeps entries');
  ok(await p.locator('input[data-path^="t.coll."],select[data-path^="t.coll."]').count()===0,'collateral inputs are not rendered when not applicable');
  await p.selectOption('select[data-path="f.security"]','Secured'); await p.waitForTimeout(150);
  ok(await p.locator('input[data-path^="t.coll."],select[data-path^="t.coll."]').count()>0&&(await p.locator('input[data-path^="t.coll."][data-path$=".value"]').first().inputValue())==='190,000','switching back restores the kept collateral entries');
  await p.selectOption('select[data-path="f.security"]',''); await p.waitForTimeout(150);
  t=await txt('#sec-coll'); ok(t.includes('Waiting on an answer'),'blank Security: tool says it cannot tell yet (not silently applicable)');
  await p.selectOption('select[data-path="f.security"]','Secured');
  // 3 N/A not accepted for calc input, shown in menu
  await p.locator('[data-act=cellstate][data-path^="t.income."]').first().click(); await p.waitForTimeout(100);
  const pop=await txt('#pop'); ok(pop.includes('does not accept N/A')&&pop.includes('Exclude the whole row'),'state menu explains N/A is not accepted for a calculation input');
  await p.keyboard.press('Escape');
  // purpose allows N/A with reason
  await p.locator('input[data-path="f.purpose"]').locator('xpath=ancestor::div[contains(@class,"cell")]').locator('[data-act=cellstate]').click();
  await p.click('#pop [data-act=cs-na]'); await p.fill('#why','Not stated by borrower'); await p.click('#pop [data-act=apply-na]'); await p.waitForTimeout(150);
  ok((await txt('[data-cell="f.purpose"]')).includes('N/A')&&(await txt('[data-cell="f.purpose"]')).includes('Not stated by borrower'),'N/A with a reason is recorded and shown');
  // 4 exclude
  await p.locator('[data-act=rowmenu]').nth(3).click(); await p.click('#pop [data-act=exclude]'); await p.fill('#why','Paid off at closing'); await p.click('#pop [data-act=apply-excl]'); await p.waitForTimeout(150);
  ok(await p.locator('.exrow').count()>=2,'exclude on purpose adds a visible excluded row with reason');
  // 5 Enter adds row
  const lastEv=await p.locator('[data-row^="income."] input').count();
  const lastCreditor=p.locator('[data-row^="income."]').last().locator('input').first(); await lastCreditor.focus(); await p.keyboard.press('Enter'); await p.waitForTimeout(150);
  ok(await p.locator('[data-row^="income."]').count()===4,'Enter in the last row adds a row');
  // submit blocked
  await p.click('[data-act=why-submit]',{force:true}); await p.waitForTimeout(100); const bl=await txt('#pop'); ok(bl.includes('Before this can go for review'),'submit lists blockers: '+bl.replace(/\n/g,' | ').slice(0,140));
  await p.keyboard.press('Escape');
  // persistence
  await p.reload(); await p.waitForTimeout(500);
  ok((await p.locator('input[data-path^="t.income."][data-path$=".amount"]').nth(1).inputValue())==='1,450','edits survive a reload (preserve work)');
  // 6 review flow
  await p.evaluate(()=>__wps.loadScen('review')); await p.waitForTimeout(200);
  await p.fill('#rp-new','Please confirm the rent roll date.'); await p.click('[data-act=rp-raise]'); await p.waitForTimeout(150);
  ok((await txt('#insp-pane')).includes('Please confirm the rent roll date.'),'reviewer raises a review point');
  await p.click('[data-act=return]'); await p.waitForTimeout(150);
  ok((await txt('#casebar')).includes('Prepare')&&(await txt('#banners')).includes('Returned')===false,'(reviewer view after return)');
  await p.selectOption('#role','preparer'); await p.waitForTimeout(150);
  ok((await txt('#banners')).includes('Returned by the reviewer'),'preparer sees returned banner');
  const amt=p.locator('input[data-path="f.amount"]'); await amt.fill('290000'); await p.waitForTimeout(100);
  ok(await p.locator('.cell.chg').count()>=1,'a field edited after submission is marked Changed');
  // reviewer cannot edit
  await p.selectOption('#role','reviewer'); await p.waitForTimeout(150);
  ok(await p.locator('input[data-path="f.amount"]').isDisabled(),'reviewer entries are read only');
  // 7 close tool
  await p.click('[data-act=nav][data-v=cases]'); await p.click('[data-act=filter][data-f=all]'); await p.click('tr[data-live=close]'); await p.waitForTimeout(250);
  t=await txt('.calcbox[data-calc=recon]'); ok(t.includes('Not calculated'),'bank rec starts incomplete');
  await p.selectOption('#role','preparer'); await p.waitForTimeout(100);
  await p.locator('input[data-path^="t.items."][data-path$=".amount"]').nth(2).fill('4310.20'); await p.waitForTimeout(150);
  t=await txt('.calcbox[data-calc=recon]'); ok(t.includes('$0.00')&&t.includes('Pass'),'bank rec reaches $0.00 and passes: '+t.replace(/\n/g,' | ').slice(0,160));
  ok((await txt('#sec-ic')).includes('Not applicable')&&(await txt('#sec-ic')).includes('kept'),'intercompany section not applicable but data kept');
  // 8 org terms
  await p.selectOption('#role','admin'); await p.click('[data-act=nav][data-v=setup]'); await p.click('[data-act=setup-tab][data-tab=org]'); await p.fill('#term_case','Credit file'); await p.locator('#term_case').blur(); await p.waitForTimeout(150);
  await p.click('[data-act=nav][data-v=cases]'); ok((await txt('.pagehead h1')).includes('Credit files'),'org terminology change flows to screens');
  console.log('\nERRORS',errs); console.log('pass',pass,'fail',fail);process.exitCode=fail?1:0;
  await b.close();
})();

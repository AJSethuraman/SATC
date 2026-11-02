const K='A';
function calcRows(X,rows){const {h,C,R}=X;return rows.map(r=>R(r.big?h.big:h.calc,C(2,5,r.l,'clbl'+(r.big?' bigl':''))+C(7,2,r.v,r.cls||'s-calc num'+(r.big?' big':''))+(r.verd?C(9,3,r.verd[0],'verd '+r.verd[1]):''),'')).join('')}
function analysis(){
 const X=ctx(K,'#2B3A55'),{h,C,R,gap,wrap,title,status,sec,th,tr}=X;
 const pcols=[8,9,10,11];
 const hdr=(lab,names)=>R(h.th,C(2,6,'','')+names.map((n,i)=>C(pcols[i],1,n,'s-in ctr')).join(''),'');
 const row=(lab,vals,kinds)=>R(h.row,C(2,6,lab,'lab')+pcols.map((c,i)=>C(c,1,vals[i],'s-'+kinds[i]+' num')).join(''));
 const col3=[{c:6,s:2,t:'VALUE',n:1},{c:8,s:2,t:'ADVANCE %',n:1},{c:10,s:2,t:'ADJUSTED VALUE',n:1}];
 const cv=(lab,v,a,adj)=>R(h.row,C(2,4,lab,'lab')+C(6,2,v,'s-in num')+C(8,2,a,'s-in num')+C(10,2,adj,adj?'s-calc num':'s-lock num'));
 const inc=[{c:3,s:4,t:'SOURCE'},{c:7,s:2,t:'AMOUNT',n:1},{c:9,s:2,t:'PER'}];
 const dbt=[{c:3,s:5,t:'CREDITOR'},{c:8,s:2,t:'MONTHLY PAYMENT',n:1}];
 const b=[
  title('Credit file review: Analysis','Lakeshore Community Bank (synthetic)','Credit file review 1.1',['Workpaper','Check','Settings','Framework']),gap(8),
  status([{l:'Ready for review',v:'No',tone:'warn'},{l:'Still missing',v:'2',tone:'plain'},{l:'Sections complete',v:'6 of 8',tone:'plain'}]),gap(10),
  sec('Supporting analysis','Complete · Optional','ok'),
  R(h.grp,C(2,10,'OWNER AND GUARANTOR CASH FLOW','phd2'),''),
  hdr('',['J. Hale','M. Hale','Person 3','Person 4']),
  row('Adjusted personal income',['$96,000','$41,000','',''],['in','in','in','in']),
  row('Existing personal debt payments',['$18,600','$6,200','',''],['in','in','in','in']),
  row('Left after debt payments',['$77,400','$34,800','',''],['calc','calc','lock','lock']),gap(8),
  R(h.grp,C(2,10,'COLLATERAL VALUATION','phd2'),''),
  th(col3.map(x=>x),'').replace('class="c th"','class="c th"'),
  cv('Cash','','',''),cv('Marketable securities','','',''),cv('Accounts receivable','','',''),cv('Inventory','','',''),cv('Equipment','$190,000','70','$133,000'),cv('Real estate','$240,000','80','$192,000'),
  R(h.tot,C(2,4,'Total','lab tl')+C(6,2,'$430,000','s-calc num tot')+C(8,2,'','tl')+C(10,2,'$325,000','s-calc num tot'),''),gap(8),
  R(h.grp,C(2,10,'INCOME SOURCES','phd2'),''),
  th(inc,''),tr('Income 1',inc,['Owner salary','$96,000','Annual'],[]),tr('Income 2',inc,['Rental, 14 Dock St','$1,450','Monthly'],[]),tr('Income 3',inc,['Spouse wages','$3,200','Monthly'],[]),tr('Income 4',inc,['','',''],[]),gap(8),
  R(h.grp,C(2,10,'EXISTING DEBTS','phd2'),''),
  th(dbt,''),tr('Debt 1',dbt,['Auto loan','$612'],[]),tr('Debt 2',dbt,['Credit card','$95'],[]),tr('Debt 3',dbt,['Student loan (deferred)','$0'],[]),tr('Debt 4',dbt,['',''],[]),gap(8),
  R(h.row,C(2,4,'Proposed monthly payment','lab')+C(6,2,'$5,780','s-in num')),gap(10),
  R(h.sechd-2,C(2,6,'DEBT-TO-INCOME','phd2')+C(8,4,'DTI-DEMO 1.0','codec'),''),
  calcRows(X,[{l:'Monthly income',v:'$12,650'},{l:'Existing monthly debt payments',v:'$707'},{l:'Proposed monthly payment',v:'$5,780'},{l:'Inputs still missing',v:'0'},{l:'Debt-to-income',v:'51.3%',big:1,verd:['Above limit','bad']}]),
  R(h.note,C(6,6,'Limit 40.0% on Settings, confirmed by the organization.','note')),gap(10)
 ];
 return wrap(b.join(''));
}
function control(){
 const X=ctx(K,'#2F5D62'),{h,C,R,gap,wrap,title,status,sec,panels,tr}=X;
 const cols=[{c:3,s:1,t:'PAYMENT'},{c:4,s:1,t:'DATE'},{c:5,s:1,t:'AMOUNT',n:1},{c:6,s:2,t:'A1 AUTHORIZED APPROVER'},{c:8,s:2,t:'A2 APPROVED FIRST'},{c:10,s:2,t:'A3 INVOICE ON FILE'}];
 const rt=v=>`<span>${v}</span>`;
 const it=(n,v)=>R(h.row,C(2,1,'Item '+n,'rl')+cols.map((x,i)=>C(x.c,x.s,i>=3?rt(v[i]):v[i],'s-in'+(x.n?' num':'')+(i>=3?' rate '+(v[i]==='Pass'?'ok':v[i]==='Exception'?'bad':'mute'):''))).join(''));
 const gapRow=t=>R(h.note+3,C(2,10,t,'note'));
 const th2=R(h.th,C(2,1,'','th')+cols.map(x=>C(x.c,x.s,x.t,'th'+(x.n?' num':''))).join(''));
 const b=[
  title('Control test','Northgate Audit (synthetic)','Control test 2.0',['Check','Settings']),gap(8),
  status([{l:'Ready for review',v:'Yes',tone:'ok'},{l:'Still missing',v:'0',tone:'plain'},{l:'Sections complete',v:'6 of 6',tone:'plain'}]),gap(10),
  panels([{t:'CONTROL',st:'Complete',tone:'ok',c0:2,span:5,ls:2,f:[{l:'Control',v:'P2P-07 Payments approved before release',k:'in'},{l:'Control owner',v:'Accounts payable',k:'in'}]},{t:'PERIOD',st:'Complete',tone:'ok',c0:7,span:5,ls:2,f:[{l:'How often it runs',v:'Monthly',k:'in'},{l:'Period tested',v:'Q3 2026',k:'in'}]}],'ok'),gap(8),
  panels([{t:'RESULT',st:'Complete',tone:'ok',c0:2,span:5,ls:3,f:[{l:'Were exceptions found?',v:'Yes',k:'in'}]}],'ok'),gap(12),
  sec('Sample','Complete','ok'),R(h.grp,C(2,10,'PAYMENTS TESTED · 25 ITEMS','phd2')),th2,
  it(1,['PAY-30140','2026-07-02','$21,590','Pass','Pass','Pass']),it(2,['PAY-30167','2026-07-05','$10,485','Pass','Pass','Pass']),it(3,['PAY-30194','2026-07-08','$42,590','Pass','Pass','Pass']),
  gapRow('Items 4–12 not shown'),
  it(13,['PAY-30464','2026-08-11','$28,054','Exception','Exception','Pass']),it(14,['PAY-30491','2026-08-14','$53,884','Pass','Pass','N/A']),
  gapRow('Items 15–24 not shown'),
  it(25,['PAY-30788','2026-09-20','$10,061','Pass','Pass','Pass']),gap(12),
  R(h.sechd-2,C(2,6,'DEVIATION RATE','phd2')+C(8,4,'DEV-DEMO 1.0','codec')),
  calcRows(X,[{l:'Items tested',v:'25'},{l:'Items with an exception',v:'2'},{l:'Inputs still missing',v:'0'},{l:'Deviation rate',v:'8.0%',big:1,verd:['Above limit','bad']}]),
  R(h.note,C(6,6,'Limit 5.0% on Settings, confirmed by the organization.','note')),gap(10)
 ];
 return wrap(b.join(''));
}
function admin(which){
 const X=ctx(K,'#2B3A55'),{h,C,R,gap,wrap,title,sec,th}=X;
 const hd=(n,w)=>title(n,'Lakeshore Community Bank (synthetic)','Credit file review 1.1',w);
 const note=t=>R(h.note+4,C(2,10,t,'note'));
 const lk=(c,s,t,cls)=>C(c,s,t,'s-lock '+(cls||''));
 let b=[];
 if(which==='check'){
  const rows=[['Tester details','OK'],['Reviewer details','OK'],['Scope','OK'],['Borrower details','OK'],['Facilities','OK'],['Test questions','1 missing','Go to Test questions'],['Supporting analysis','OK'],['Conclusion','1 missing','Go to Conclusion'],['Limit confirmed (DTI)','OK']];
  b=[hd('Release check',['Workpaper','Settings']),gap(8),note('Every line must read OK before this goes for review. Each line says where to go.'),gap(4),
   R(h.th,C(2,5,'CHECK','th')+C(7,2,'RESULT','th')+C(9,3,'WHERE TO GO','th')),
   ...rows.map(r=>R(h.row,lk(2,5,r[0])+lk(7,2,r[1],'verd '+(r[1]==='OK'?'ok':'warn'))+(r[2]?C(9,3,'<a>'+r[2]+'</a>','s-lock'):C(9,3,'','s-lock')))),gap(8),
   R(h.big,C(2,5,'Ready for review','bigl lab')+C(7,2,'No','verd warn')),gap(10)];
 }
 if(which==='settings'){
  const f=[{c:2,s:3,t:'LIMIT'},{c:5,s:2,t:'METHOD'},{c:7,s:1,t:'AUTHOR',n:1},{c:8,s:1,t:'OUR POLICY',n:1},{c:9,s:1,t:'CONFIRMED'},{c:10,s:2,t:'BY · DATE'}];
  const row=(a,m,au,pol,cf,by,miss)=>R(h.row,C(2,3,a,'s-lock')+C(5,2,m,'s-lock')+C(7,1,au,'s-lock num')+C(8,1,pol,(miss?'s-miss':'s-in')+' num')+C(9,1,cf,'s-in')+C(10,2,by,'s-lock'));
  b=[hd('Settings',['Workpaper','Check']),gap(8),note('Limits belong to this organization, not to the method. Until a limit is confirmed here, nothing is tested against it.'),gap(4),
   R(h.th,f.map(x=>C(x.c,x.s,x.t,'th'+(x.n?' num':''))).join('')),
   row('Highest debt-to-income','DTI-DEMO 1.0','40.0%','40.0%','Yes','D. Patel · 2026-10-02'),
   row('Highest deviation rate','DEV-DEMO 1.0','5.0%','<i class="hint">Required</i>','','Not confirmed',1),gap(8),
   note('A limit that is not confirmed shows its verdict as “Not tested: limit not confirmed”.'),gap(10)];
 }
 if(which==='framework'){
  const q=[['1','Risk rating','1.01','Is the assigned risk rating supported by the credit file?','Read the approval document and its attachments. Using your rating guidance and judgment, conclude whether the rating is reasonable.','Always'],['2','Data accuracy','2.02','Is the industry code correct in the system of record?','Compare the code with the approval document.','Always'],['5','Repayment analysis','5.02','For a new money request, was the required analysis completed with current information?','Confirm the analysis was required, completed, and used current information.','New money request = Yes'],['6','Collateral','6.01','Was the collateral eligible, valued and documented?','Confirm the type is allowed, the valuation is current and the lien is documented.','Security = Secured']];
  b=[hd('Framework',['Workpaper','Settings']),gap(8),note('One row per question. The workpaper is built from this table.'),gap(4),
   R(h.th,C(2,1,'§','th')+C(3,2,'SECTION','th')+C(5,1,'Q#','th')+C(6,3,'QUESTION','th')+C(9,2,'TEST STEPS','th')+C(11,1,'SHOWN WHEN','th')),
   ...q.map(r=>R(56,C(2,1,r[0],'s-lock')+C(3,2,r[1],'s-lock')+C(5,1,r[2],'s-lock')+C(6,3,r[3],'s-in wrap')+C(9,2,r[4],'s-in wrap')+C(11,1,r[5],'s-in wrap','font-size:var(--fs-note)'))),gap(10)];
 }
 if(which==='lists'){
  const L=[['Yes / No',['Yes','No']],['Effectiveness',['Effective','Partially effective','Not effective','Not applicable']],['Testers',['A. Rivera','B. Chen','C. Okafor']],['Facility types',['Term loan','Line of credit','Equipment loan','SBA term loan']],['Quarter ends',['2026-09-30','2026-12-31','2027-03-31']]];
  const cs=[2,4,6,8,10];
  b=[hd('Lists',['Workpaper','Framework']),gap(8),note('Every dropdown reads from these lists. Add values at the end of a list.'),gap(4),
   R(h.th,L.map((l,i)=>C(cs[i],2,l[0],'th')).join('')),
   ...[0,1,2,3,4,5].map(r=>R(h.row,L.map((l,i)=>C(cs[i],2,l[1][r]||'','s-in')).join(''))),gap(10)];
 }
 return wrap(b.join(''));
}
function catalogue(){
 const X=ctx(K,'#2B3A55'),{h,C,R,gap,wrap}=X;
 const calc=(title,rows)=>R(h.sechd-4,C(2,10,title,'phd2'))+calcRows(X,rows)+gap(6);
 const q=(n,txt,r,cmt,mode)=>{const tone={Effective:'ok','Partially effective':'warn','Not effective':'bad'}[r];
  if(mode==='na')return R(h.q,C(2,1,n,'qn')+C(3,4,txt,'q wrap')+C(7,2,'Not applicable','s-na')+C(9,3,'Condition not met: new money = No','s-lock note wrap'));
  return R(h.q,C(2,1,n,'qn')+C(3,4,txt,'q wrap hn')+C(7,2,r?r:'<i class="hint">Rate this</i>',r?'s-in rate '+tone:'s-miss')+C(9,3,cmt==='!'?'<i class="hint">Comment required</i>':(cmt||''),cmt==='!'?'s-miss wrap':'s-in cmt wrap'));};
 const b=[
  R(h.sechd,C(2,10,'Calculation panel: four outcomes','sec'),'sechd'),gap(6),
  calc('Complete, under the limit',[{l:'Inputs still missing',v:'0'},{l:'Debt-to-income',v:'32.4%',big:1,verd:['Within limit','ok']}]),
  calc('Complete, over the limit',[{l:'Inputs still missing',v:'0'},{l:'Debt-to-income',v:'51.3%',big:1,verd:['Above limit','bad']}]),
  calc('Inputs missing: nothing is calculated',[{l:'Inputs still missing',v:'2'},{l:'Debt-to-income',v:'Not calculated',big:1,cls:'s-nc'}]),
  calc('Complete, limit not confirmed on Settings',[{l:'Inputs still missing',v:'0'},{l:'Debt-to-income',v:'32.4%',big:1,verd:['Not tested: limit not confirmed','mute']}]),
  gap(6),R(h.sechd,C(2,10,'Question block: four states','sec'),'sechd'),gap(6),
  q('1.01','Is the assigned risk rating supported by the credit file?','Effective','Rating supported by cash flow and collateral coverage.'),
  q('3.01','Are all policy exceptions noted and mitigated in the approval document?','Partially effective','!'),
  q('6.01','Was the collateral eligible, valued and documented?','',''),
  q('6.02','Is the lien position documented? (unsecured credit)','','','na'),
  R(34,C(3,9,'Red corner mark = cell note with the “how to test” text. It opens on hover and takes no row space. A comment becomes required when the rating is Partially or Not effective.','note wrap')),gap(8),
  R(h.sechd,C(2,10,'Section headers: status words','sec'),'sechd'),gap(6),
  ...[['Complete','ok'],['1 missing','warn'],['Optional','mute'],['Not applicable','mute']].map(s=>R(h.sechd-4,C(2,10,'Section name','sec'),'sechd')+R(h.note+4,C(2,10,s[0],'sfoot '+s[1]))),gap(10)
 ];
 return wrap(b.join(''));
}
Object.assign(window,{analysis,control,admin,catalogue});

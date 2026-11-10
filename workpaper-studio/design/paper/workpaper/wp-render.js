const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
function ctx(k,brand){
 const t=T(k,brand),h=t.rh,P=t.px;
 const C=(c,s,x,cls='',st='')=>`<div class="c ${cls}" style="grid-column:${c}/span ${s}${st?';'+st:''}">${x==null?'':x}</div>`;
 let card=false;const R=(ht,cells,cls='',rail='')=>`<div class="r ${cls}${card&&k==='A'?' card':''}" style="height:${P(ht)}px">${rail?`<div class="c g rail-${rail}" style="grid-column:1"></div>`:''}${cells}</div>`;
 let pend=null;const gap=(n=h.gap)=>{const f=pend&&card?R(h.note+3,C(2,10,pend.t,'sfoot '+pend.tone)):'';pend=null;card=false;return f+R(n,'')};const open=()=>{card=true};
 const wrap=html=>`<div class="sheet ${t.cls}" style="${t.style}">${html}</div>`;
 const title=(name,org,ver,navs)=>{
  const st=12-navs.length,C_=k==='C';
  return R(h.title,C(2,st-2,name,'title')+navs.map((n,i)=>C(st+i,1,`<a>${n}</a>`,'btn ctr')).join(''),k==='B'?'tband':'band')+R(h.sub,C(2,10,esc(org)+' · '+ver,'sub'),k==='B'?'tsub':'band');
 };
 const chip=(v,tone)=>C(0,1,v);
 const status=items=>{
  const pos=[[2,2,4],[6,2,8],[9,2,11]];
  return R(h.status,items.map((it,i)=>C(pos[i][0],pos[i][1],it.l,'lbl')+C(pos[i][2],1,it.v,'chip ctr '+it.tone+(it.chg?' chg':''))).join(''),'status');
 };
 const sec=(name,stText,tone,rail)=>(open(),pend={t:stText,tone},R(h.sechd,C(2,10,name,'sec'),'sechd',rail));
 const grp=(t_,rail)=>R(h.grp,C(2,10,t_,'grp'),'',rail);
 const stack=false;
 const panels=(list,rail)=>{
  card=false;const out=[];const nrows=1+list[0].f.length*(stack?2:1);
  const edge=(p,c,s)=>(c===p.c0?' pl':'')+(c+s-1===p.c0+p.span-1?' pr':'');
  for(let i=0;i<nrows;i++){
   const last=i===nrows-1;let hh=h.field,cells='';
   if(i===0)hh=h.phd;else if(stack&&i%2===1)hh=h.slbl;
   list.forEach(p=>{
    if(i===0){
     cells+=C(p.c0,p.span,p.t,'phd pc pt pl pr');
    }else if(stack){
     const f=p.f[Math.floor((i-1)/2)];
     if(i%2===1)cells+=C(p.c0,p.span,f.l,'slbl pc pl pr');
     else cells+=C(p.c0,p.span,f.v,'s-'+f.k+' solo pc pl pr'+(last?' pb':'')+(f.n?' num':''));
    }else{
     const f=p.f[i-1];
     cells+=C(p.c0,p.ls,f.l,'lbl pc'+edge(p,p.c0,p.ls)+(last?' pb':''))+C(p.c0+p.ls,p.span-p.ls,f.v,'s-'+f.k+' solo pc'+edge(p,p.c0+p.ls,p.span-p.ls)+(last?' pb':'')+(f.n?' num':''));
    }
   });
   out.push(R(hh,cells,'',rail));
  }
  if(k==='A')out.push(R(h.note+3,list.map(p=>C(p.c0,p.span,p.st,'pfoot pc pl pr pb '+p.tone)).join(''),'',rail));
  return out.join('');
 };
 const th=(cols,rail)=>R(h.th,C(2,1,'','')+cols.map(x=>C(x.c,x.s,x.t,'th'+(x.n?' num':''))).join(''),'',rail);
 const tr=(lab,cols,vals,kinds,rail,cls='')=>R(h.row,C(2,1,lab,'rl')+cols.map((x,i)=>C(x.c,x.s,vals[i]??'','s-'+(kinds[i]||'in')+(x.n?' num':'')+(i===0?' fl':'')+' '+(cls))).join(''),'',rail);
 const hint=(txt)=>`<i class="hint">${txt}</i>`;
 return {t,h,C,R,gap,open,wrap,title,status,sec,grp,panels,th,tr,hint,esc};
}
function credit(k,st='draft'){
 const rd=st==='ready';
 const X=ctx(k,'#2B3A55'),{h,C,R,gap,wrap,title,status,sec,grp,panels,th,tr,hint,t}=X;
 const dot=x=>x;
 const rate={Effective:'ok','Partially effective':'warn','Not effective':'bad'};
 const q=(n,txt,r,cmt,cond,rail,chg)=>{
  const rt=r?'<span>'+dot(r)+'</span>':hint('Rate this');
  return R(h.q,C(2,1,n+(cond?'<small>'+cond+'</small>':''),'qn')+C(3,4,esc(txt),'q wrap hn')+C(7,2,rt,(r?'s-in rate '+rate[r]:'s-miss rate')+' solo'+(chg?' chg':''))+C(9,3,cmt?esc(cmt):'','s-in cmt wrap solo'+(chg?' chg':'')),'qrow',rail);
 };
 const fac=[{c:3,s:4,t:'FACILITY TYPE'},{c:7,s:1,t:'RATING',n:1},{c:8,s:2,t:'COMMITMENT',n:1},{c:10,s:2,t:'OUTSTANDING',n:1}];
 const body=[
  title('Credit file review','Lakeshore Community Bank (synthetic)','Credit file review 1.1',['Analysis','Check','Settings','Framework']),
  gap(8),
  status(rd?[{l:'Ready for review',v:'Yes',tone:'ok',chg:1},{l:'Still missing',v:'0',tone:'plain',chg:1},{l:'Sections complete',v:'8 of 8',tone:'plain',chg:1}]:[{l:'Ready for review',v:'No',tone:'warn'},{l:'Still missing',v:'2',tone:'plain'},{l:'Sections complete',v:'6 of 8',tone:'plain'}]),
  gap(10),
  panels([
   {t:'TESTER DETAILS',st:'Complete',tone:'ok',c0:2,span:4,ls:2,f:[{l:'Tester',v:'A. Rivera',k:'in'},{l:'Test date',v:'2026-10-14',k:'in'}]},
   {t:'REVIEWER DETAILS',st:'Complete',tone:'ok',c0:6,span:3,ls:1,f:[{l:'Reviewer',v:'D. Patel',k:'in'},{l:'Review date',v:'',k:'in'}]},
   {t:'SCOPE',st:'Complete',tone:'ok',c0:9,span:3,ls:1,f:[{l:'Quarter end',v:'2026-09-30',k:'in'},{l:'Scope',v:'New money, secured',k:'in'}]}
  ],'ok'),
  gap(8),
  panels([{t:'BORROWER DETAILS',st:'Complete',tone:'ok',c0:2,span:5,ls:3,f:[{l:'Borrower name',v:'Harbor Millwork LLC',k:'in'},{l:'Security',v:'Secured',k:'in'},{l:'New money request?',v:'Yes',k:'in'}]}],'ok'),
  gap(12),
  sec('Facilities','Complete','ok','ok'),
  gap(4),
  th(fac,'ok'),
  tr('Facility 1',fac,['Term loan',5,'$285,000','$285,000'],[],'ok'),
  tr('Facility 2',fac,['Line of credit',5,'$75,000','$22,500'],[],'ok'),
  tr('Facility 3',fac,['','','',''],[],'ok'),
  tr('Facility 4',fac,['','','',''],[],'ok'),
  R(h.tot,C(2,1,'Total','rl tl')+C(3,4,'','tl')+C(7,1,'','tl')+C(8,2,'$360,000','s-calc num tl tot')+C(10,2,'$307,500','s-calc num tl tot'),'','ok'),
  gap(14),
  sec('Test questions',rd?'Complete':'1 missing',rd?'ok chg':'warn',rd?'ok':'warn'),
  grp('Risk rating','warn'),
  q('1.01','Is the assigned risk rating supported by the credit file?','Effective','Rating supported by cash flow and collateral coverage.',null,'warn'),
  grp('Data accuracy','warn'),
  q('2.02','Is the industry code correct in the system of record?','Not effective','System shows a different industry code from the approval document.',null,'warn'),
  grp('Policy exceptions','warn'),
  q('3.01','Are all policy exceptions noted and mitigated in the approval document?','Partially effective','One exception noted without a mitigant.',null,'warn'),
  grp('Repayment analysis','warn'),
  q('5.02','For a new money request, was the required analysis completed with current information?','Partially effective','Recomputed debt-to-income is 51.3% against our 40% limit. The file does not explain the difference.','if new money','warn'),
  grp('Collateral','warn'),
  (rd?q('6.01','Was the collateral eligible, valued and documented?','Effective','Valued within 90 days; lien documented.','if secured','ok',1):q('6.01','Was the collateral eligible, valued and documented?','','','if secured','warn')),
  gap(10)
 ];
 return wrap(body.join(''));
}
function recon(k){
 const X=ctx(k,'#2D6A3E'),{open,h,C,R,gap,wrap,title,status,sec,grp,panels,th,tr,hint,t}=X;
 const it=[{c:3,s:3,t:'TYPE'},{c:6,s:3,t:'DESCRIPTION'},{c:9,s:1,t:'DATE'},{c:10,s:2,t:'AMOUNT',n:1}];
 const rows=[['Deposit in transit','Customer deposit','2026-10-31','$12,400.00'],['Outstanding check','4410 Delta Supply','2026-10-22','$18,950.00'],['Outstanding check','4418 City Water','2026-10-29','$4,310.20'],['Outstanding check','4102 Harbor Signs (over 90 days)','2026-07-30','$1,280.00'],['Bank fee not yet booked','October analysis fee','2026-10-31','$85.00']];
 const cr=(lab,v,big)=>R(big?h.big:h.calc,C(2,4,lab,'clbl'+(big?' bigl':''))+C(6,2,v,'s-calc num'+(big?' big':'')),'','ok');
 const naRow=(lab,vals)=>R(h.row,C(2,1,lab,'rl na-t')+C(3,6,vals[0],'s-na')+C(9,3,vals[1],'s-na'),'','mute');
 const body=[
  title('Bank reconciliation','Bramble Foods (synthetic)','Bank reconciliation 1.0',['Check','Settings']),
  gap(8),
  status([{l:'Ready for review',v:'Yes',tone:'ok'},{l:'Still missing',v:'0',tone:'plain'},{l:'Sections complete',v:'6 of 6',tone:'plain'}]),
  gap(10),
  panels([
   {t:'ACCOUNT',st:'Complete',tone:'ok',c0:2,span:4,ls:2,f:[{l:'Account',v:'Operating ··4821',k:'in'},{l:'Statement date',v:'2026-10-31',k:'in'}]},
   {t:'BALANCES',st:'Complete',tone:'ok',c0:6,span:6,ls:3,f:[{l:'Balance per bank statement',v:'$185,600.55',k:'in',n:1},{l:'Balance per ledger',v:'$173,545.35',k:'in',n:1}]}
  ],'ok'),
  gap(8),
  panels([{t:'ACTIVITY',st:'Complete',tone:'ok',c0:2,span:4,ls:3,f:[{l:'Any intercompany activity?',v:'No',k:'in'}]}],'ok'),
  gap(12),
  sec('Reconciling items','Complete','ok','ok'),
  gap(4),
  th(it,'ok'),
  ...rows.map((r,i)=>tr('Item '+(i+1),it,r,[],'ok')),
  tr('Item 6',it,['','','',''],[],'ok'),
  tr('Item 7',it,['','','',''],[],'ok'),
  gap(12),
  (X.open(),R(h.sechd-2,C(2,6,'RECONCILIATION','phd2')+C(8,4,'REC-DEMO 1.0','codec'),'','ok')),
  cr('Adjusted bank','$173,460.35'),cr('Adjusted books','$173,460.35'),cr('Inputs still missing','0'),
  R(h.big,C(2,4,'Difference','clbl bigl')+C(6,2,'$0.00','s-calc num big')+C(8,4,'Within limit','verd ok'),'','ok'),
  R(h.note,C(8,4,'Limit is on Settings, confirmed by the organization.','note'),'','ok'),
  gap(12),
  sec('Intercompany','Not applicable','mute','mute'),
  R(h.note+2,C(2,10,'Shown only when intercompany activity = Yes','note'),'','mute'),
  th([{c:3,s:6,t:'COUNTERPARTY'},{c:9,s:3,t:'AMOUNT',n:1}],'mute').replace('class="c th"','class="c th lockd"'),
  naRow('Item 1',['','']),naRow('Item 2',['','']),
  gap(12),
  panels([{t:'SIGN-OFF',st:'Complete',tone:'ok',c0:2,span:6,ls:2,f:[{l:'Prepared by',v:'R. Lund',k:'in'},{l:'Prepared on',v:'2026-11-01',k:'in'}]}],'ok'),
  gap(10)
 ];
 return wrap(body.join(''));
}
function states(k){
 const X=ctx(k,'#2B3A55'),{h,C,R,gap,wrap,t}=X;
 const nt=(s)=>{const o=t.st[s];return `Fill ${o.fill==='hatch'?'hatch #DDE1E6/white':o.fill} · text ${o.fc} · line ${o.bd}${NOTE[s]?' · '+NOTE[s]:''}`};
 const rows=[
  ['Input, filled','s-in num','$285,000','in'],['Input, optional and empty','s-in','','in'],['Missing, required','s-miss',`<i class="hint">Required</i>`,'miss'],
  ['Zero, entered','s-in num','$0.00',null,'Entered zero is a value: looks like any filled input'],['Not applicable','s-na','N/A','na'],['Excluded','s-exc num','$4,310.20','exc'],
  ['Computed','s-calc num','$173,460.35','calc'],['Locked','s-lock','Credit file review 1.1','lock'],['Error','s-err','Amount must be positive','err'],['Not calculated','s-nc','Not calculated','nc']
 ];
 const verd=[['Complete, under limit','Within limit','verd ok','Green text · calculation complete and under the confirmed limit'],['Complete, over limit','Above limit','verd bad','Red text · calculation complete and over the limit'],['Complete, no limit confirmed','Not tested: limit not confirmed','verd mute','Gray italic · result shown, no limit to test against'],['Inputs missing','Not calculated','s-nc','Result and verdict both withheld: never $0.00, never a pass']];
 const body=[
  R(h.sechd,C(2,10,'Cell states','sec'),'sechd'),gap(4),
  ...rows.map(r=>R(h.row+4,C(2,3,r[0],'lbl')+C(5,3,r[2],r[1]+' solo')+C(8,4,r[3]?nt(r[3]):r[4],'note wrap'),'srow')),
  gap(8),
  R(h.sechd,C(2,10,'Verdicts','sec'),'sechd'),gap(4),
  ...verd.map(v=>R(h.row+4,C(2,3,v[0],'lbl')+C(5,3,v[1],v[2]+' vbox')+C(8,4,v[3],'note wrap'),'srow')),
  gap(10)
 ];
 return wrap(body.join(''));
}
Object.assign(window,{credit,recon,states});

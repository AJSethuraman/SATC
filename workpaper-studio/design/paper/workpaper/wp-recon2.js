function recon2(k,st){
 const dr=st==='draft';
 const X=ctx(k,'#2D6A3E'),{open,h,C,R,gap,wrap,title,status,sec,panels,th,tr}=X;
 const it=[{c:3,s:3,t:'TYPE'},{c:6,s:3,t:'DESCRIPTION'},{c:9,s:1,t:'DATE'},{c:10,s:2,t:'AMOUNT',n:1}];
 const rows=[['Deposit in transit','Customer deposit','2026-10-31','$12,400.00'],['Outstanding check','4410 Delta Supply','2026-10-22','$18,950.00'],['Outstanding check','4418 City Water','2026-10-29','$4,310.20'],['Outstanding check','4102 Harbor Signs (over 90 days)','2026-07-30','$1,280.00'],['Bank fee not yet booked','October analysis fee','2026-10-31',dr?'':'$85.00']];
 const miss='<i class="hint">Required</i>';
 const cr=(lab,v,cls)=>R(h.calc,C(2,4,lab,'clbl')+C(6,2,v,cls||'s-calc num'));
 const body=[
  title('Bank reconciliation','Bramble Foods (synthetic)','Bank reconciliation 1.0',['Check','Settings']),gap(8),
  status(dr?[{l:'Ready for review',v:'No',tone:'warn'},{l:'Still missing',v:'4',tone:'plain'},{l:'Sections complete',v:'2 of 6',tone:'plain'}]:[{l:'Ready for review',v:'Yes',tone:'ok',chg:1},{l:'Still missing',v:'0',tone:'plain',chg:1},{l:'Sections complete',v:'6 of 6',tone:'plain',chg:1}]),gap(10),
  panels([
   {t:'ACCOUNT',st:'Complete',tone:'ok',c0:2,span:4,ls:2,f:[{l:'Account',v:'Operating ··4821',k:'in'},{l:'Statement date',v:'2026-10-31',k:'in'}]},
   {t:'BALANCES',st:dr?'1 missing':'Complete',tone:dr?'warn':'ok'+' chg',c0:6,span:6,ls:3,f:[{l:'Balance per bank statement',v:'$185,600.55',k:'in',n:1},{l:'Balance per ledger',v:dr?miss:'$173,545.35',k:dr?'miss':'in',n:1}]}
  ],'ok'),gap(8),
  panels([{t:'ACTIVITY',st:'Complete',tone:'ok',c0:2,span:4,ls:3,f:[{l:'Any intercompany activity?',v:dr?'Yes':'No',k:'in'}]}],'ok'),gap(12),
  sec('Reconciling items',dr?'1 missing':'Complete',dr?'warn':'ok chg',dr?'warn':'ok'),gap(4),
  th(it,'ok'),
  ...rows.map((r,i)=>tr('Item '+(i+1),it,r,i===4&&dr?['in','in','in','miss']:[],'ok')),
  tr('Item 6',it,['','','',''],[],'ok'),tr('Item 7',it,['','','',''],[],'ok'),gap(12),
  (open(),R(h.sechd-2,C(2,6,'RECONCILIATION','phd2')+C(8,4,'REC-DEMO 1.0','codec'))),
  dr?cr('Adjusted bank','Not calculated','s-nc num')+cr('Adjusted books','Not calculated','s-nc num')+cr('Inputs still missing','2'):cr('Adjusted bank','$173,460.35')+cr('Adjusted books','$173,460.35')+cr('Inputs still missing','0'),
  dr?R(h.big,C(2,4,'Difference','clbl bigl')+C(6,2,'Not calculated','s-nc num')+C(8,4,'','verd')):R(h.big,C(2,4,'Difference','clbl bigl')+C(6,2,'$0.00','s-calc num big chg')+C(8,4,'Within limit','verd ok chg')),
  R(h.note,C(8,4,dr?'Result and verdict appear when every input is entered.':'Limit is on Settings, confirmed by the organization.','note')),gap(12),
  sec('Intercompany',dr?'1 missing':'Not applicable',dr?'warn':'mute chg','mute'),
  dr?th([{c:3,s:6,t:'COUNTERPARTY'},{c:9,s:3,t:'AMOUNT',n:1}],'')+tr('Item 1',[{c:3,s:6},{c:9,s:3,n:1}],['Oakline Supply',miss],['in','miss'],'')+tr('Item 2',[{c:3,s:6},{c:9,s:3,n:1}],['',''],[],''):
  R(h.note+2,C(2,10,'Shown only when intercompany activity = Yes','note'),'','mute')+th([{c:3,s:6,t:'COUNTERPARTY'},{c:9,s:3,t:'AMOUNT',n:1}],'mute')+R(h.row,C(2,1,'Item 1','rl na-t')+C(3,6,'','s-na chg')+C(9,3,'','s-na chg'),'','mute')+R(h.row,C(2,1,'Item 2','rl na-t')+C(3,6,'','s-na chg')+C(9,3,'','s-na chg'),'','mute'),
  gap(12),
  panels([{t:'SIGN-OFF',st:dr?'1 missing':'Complete',tone:dr?'warn':'ok'+' chg',c0:2,span:6,ls:2,f:[{l:'Prepared by',v:'R. Lund',k:'in'},{l:'Prepared on',v:dr?miss:'2026-11-01',k:dr?'miss':'in'}]}],'ok'),gap(10)
 ];
 return wrap(body.join(''));
}
window.recon2=recon2;

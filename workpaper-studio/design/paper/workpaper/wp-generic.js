function generic(d){
 const X=ctx('A','#2B3A55'),{h,C,R,gap,wrap,title,status,sec,panels,th,tr,grp}=X;
 const secs=d.secs||[],isF=s=>s.blocks.length&&s.blocks.every(b=>b.k==='field');
 const need=s=>s.blocks.reduce((n,b)=>n+(b.k==='field'&&b.r?1:b.k==='table'?(b.cols||[]).filter(c=>c.r).length&&1:0),0);
 const total=secs.reduce((n,s)=>n+need(s),0);
 const out=[title(d.name||'Untitled tool',d.org||'Sample organization',d.ver||'1.0',['Check','Settings']),gap(8),
  status([{l:'Ready for review',v:total?'No':'Yes',tone:total?'warn':'ok'},{l:'Still missing',v:String(total),tone:'plain'},{l:'Sections complete',v:'0 of '+secs.length,tone:'plain'}]),gap(10)];
 const pos={1:[[2,5,2]],2:[[2,5,2],[7,5,2]],3:[[2,4,2],[6,3,1],[9,3,1]]};
 const mkP=s=>{const n=need(s);return {t:s.title.toUpperCase(),st:n?n+' missing':'Optional',tone:n?'warn':'mute',f:s.blocks.map(b=>({l:b.l,v:b.r?'<i class="hint">Required</i>':'',k:b.r?'miss':'in',n:/Money|Number/.test(b.t)}))}};
 let i=0;const list=secs;
 while(i<list.length){const s=list[i];
  if(isF(s)){const grp_=[];while(i<list.length&&isF(list[i])&&grp_.length<3){grp_.push(list[i]);i++}
   const ps=grp_.map(mkP),mx=Math.max(...ps.map(p=>p.f.length));
   ps.forEach((p,j)=>{const q=pos[ps.length][j];p.c0=q[0];p.span=q[1];p.ls=q[2];while(p.f.length<mx)p.f.push({l:'',v:'',k:'lock'})});
   out.push(panels(ps,'warn'),gap(10));continue}
  i++;const n=need(s);
  out.push(sec(s.title,n?n+' missing':s.mode==='Optional'?'Optional':'Complete',n?'warn':'mute','warn'));
  s.blocks.forEach(b=>{
   if(b.k==='field'){out.push(R(h.row,C(2,3,b.l,'lab')+C(5,3,b.r?'<i class="hint">Required</i>':'',b.r?'s-miss':'s-in')))}
   else if(b.k==='table'){const cs=b.cols&&b.cols.length?b.cols:[{n:'Column',t:'Text'}],w=Math.max(1,Math.floor(9/cs.length));
    const cols=cs.map((c,k)=>({c:3+k*w,s:k===cs.length-1?11-(3+k*w)+1:w,t:String(c.n).toUpperCase(),n:/Money|Number/.test(c.t)}));
    out.push(R(h.grp,C(2,10,String(b.l).toUpperCase(),'phd2')),th(cols,''));
    [1,2,3].forEach(r=>out.push(tr('Row '+r,cols,cols.map(()=>''),cols.map(()=>'in'),'')));
    if(b.totals)out.push(R(h.tot,C(2,1,'Total','rl tl')+cols.map(c=>C(c.c,c.s,c.n?'—':'','tl'+(c.n?' s-calc num tot':''))).join('')))}
   else if(b.k==='questions'){const qs=['Is the first item in order?','Was the second step completed?','Is the third item documented?'];
    out.push(R(h.grp,C(2,10,'GROUP','grp')));
    qs.forEach((qt,k)=>out.push(R(h.q,C(2,1,'1.0'+(k+1),'qn')+C(3,4,qt,'q wrap hn')+C(7,2,'<i class="hint">Rate this</i>','s-miss rate solo')+C(9,3,'','s-in cmt wrap solo'),'qrow')))}
   else if(b.k==='calc'){out.push(R(h.sechd-2,C(2,6,String(b.l).toUpperCase(),'phd2')+C(8,4,'CALC 1.0','codec')),R(h.calc,C(2,4,'Inputs still missing','clbl')+C(6,2,'1','s-calc num')),R(h.big,C(2,4,b.l,'clbl bigl')+C(6,2,'Not calculated','s-nc num')+C(8,4,'','verd')),R(h.note,C(8,4,'Result and verdict appear when every input is entered.','note')))}
  });out.push(gap(10))}
 if(!secs.length)out.push(R(h.row*2,C(2,10,'No sections yet. Describe the work and the engine assembles them.','note')));
 return wrap(out.join(''));
}
window.generic=generic;
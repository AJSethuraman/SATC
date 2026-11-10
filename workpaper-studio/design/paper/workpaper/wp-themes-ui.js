const LS=(k,d)=>{try{return localStorage.getItem('pt_'+k)||d}catch(e){return d}};
const hx2=a=>'#'+a.map(v=>Math.max(0,Math.min(255,Math.round(v))).toString(16).padStart(2,'0')).join('').toUpperCase();
const sh=(h,d)=>hx2([1,3,5].map(i=>parseInt(h.slice(i,i+2),16)+d));
const mkS=(name,g,mute)=>({name,ground:g,card:sh(g,7),field:sh(g,19),recess:sh(g,-7),na:sh(g,-16),hair:sh(g,-17),line:sh(g,-42),edgeD:sh(g,-62),edgeL:sh(g,21),mute,hatch1:sh(g,-25),hatch2:sh(g,7)});
const SURF={stone:{name:'Stone (cream)',ground:'#E6E1D8',card:'#EDE9E0',field:'#F7F4EE',recess:'#DFDACE',na:'#D6D1C6',hair:'#D5D0C5',line:'#BDB6A9',edgeD:'#A8A191',edgeL:'#FBFAF6',mute:'#6F6A62',hatch1:'#CFC9BC',hatch2:'#EDE9E0'},neutral:mkS('Neutral gray','#E3E3E2','#68686A'),cool:mkS('Cool gray','#DEE0E3','#656971'),warmgray:mkS('Warm gray','#E1DFDB','#6B6963'),linen:mkS('Soft stone','#E4E0D9','#6D6A63')};
const st={surface:LS('surface','linen'),theme:LS('theme','navy'),brand:LS('brand','theme'),screen:LS('screen','credit'),hl:LS('hl','1')};
const save=()=>{try{for(const k in st)localStorage.setItem('pt_'+k,st[k])}catch(e){}};
const SCREENS={credit:{name:'Credit file review',fam:'navy',draft:()=>credit('A','draft'),ready:()=>credit('A','ready'),diff:[
 ['Ready for review','No → Yes','Chip rule: missing count = 0 and every required section complete. Amber tint becomes green tint.'],
 ['Still missing / Sections complete','2 → 0 · 6 of 8 → 8 of 8','Formulas counting required cells that are empty, and sections whose status is Complete. No formatting; plain numbers.'],
 ['Test questions status','1 missing → Complete','Section status text drives its color: amber while any required rating or comment is empty, green when none is.'],
 ['Question 6.01 rating','Missing → Effective','Missing style (amber fill) applies while a required cell is blank. Once rated, the cell reverts to Input and the rating text turns green by its value.']]},
 recon:{name:'Bank reconciliation',fam:'forest',draft:()=>recon2('A','draft'),ready:()=>recon2('A','ready'),diff:[
 ['Ledger balance, item 5 amount, counterparty amount, prepared on','Missing → entered','Four required cells. Each shows the Missing style while empty, plain Input once filled. The count in the status strip follows.'],
 ['Adjusted bank / books / Difference','Not calculated → $173,460.35 · $0.00','The calculation withholds its result while any input it uses is missing. It never shows 0 in that case.'],
 ['Verdict','blank → Within limit','The verdict appears only with a complete result and a confirmed limit. Green for under, red for above.'],
 ['Intercompany section','Active, 1 missing → Not applicable','Activity answered Yes keeps the section live. Answering No grays the whole block and locks its cells; it no longer counts toward completion.'],
 ['Section statuses','1 missing → Complete','Each section header reads its own cells. Amber with a count, green when done, gray when not applicable.']]}};
const mini=t=>`<span class="sws">${[t.brand,t.head,t.sub,t.input].map(c=>`<i style="background:${c}"></i>`).join('')}</span>`;
function render(){
 let th=THEMES.find(t=>t.id===st.theme);if(!th){th=THEMES[0];st.theme=th.id}const sc=SCREENS[st.screen]||SCREENS.credit;
 document.getElementById('chips').innerHTML=THEMES.map(t=>`<button class="chipb ${t.id===st.theme?'on':''}" data-t="${t.id}">${mini(t)}<b>${t.name}</b></button>`).join('');
 document.getElementById('surf').innerHTML=Object.entries(SURF).map(([k,s])=>`<button class="chipb ${k===st.surface?'on':''}" data-f="${k}"><span class="sws">${[s.ground,s.card,s.field,s.recess].map(c=>`<i style="background:${c}"></i>`).join('')}</span><b>${s.name}</b></button>`).join('');
 document.getElementById('tabs').innerHTML=Object.entries(SCREENS).map(([k,s])=>`<button class="tab ${k===st.screen?'on':''}" data-s="${k}">${s.name}</button>`).join('');
 document.querySelectorAll('[data-b]').forEach(b=>b.classList.toggle('on',b.dataset.b===st.brand));
 document.getElementById('hl').checked=st.hl==='1';document.body.classList.toggle('hl',st.hl==='1');
 document.getElementById('a').innerHTML=sc.draft();document.getElementById('b').innerHTML=sc.ready();
 if(!SURF[st.surface])st.surface='stone';const eff={...(st.brand==='tool'?THEMES.find(t=>t.id===sc.fam):th),...SURF[st.surface]};document.querySelectorAll('.sheet').forEach(s=>applyTheme(s,eff,'theme'));
 document.getElementById('desc').textContent='Surface and color family are independent. Family: darkest shade for band and static text, one lighter shade for every header bar. Input text is black.';
 document.getElementById('diff').innerHTML=sc.diff.map(d=>`<tr><td>${d[0]}</td><td><b>${d[1]}</b></td><td>${d[2]}</td></tr>`).join('');
 const slots=[['Dark 1 (static text, band)',eff.ink],['Light 1 (fields)',eff.field],['Input text','#1A1A1A'],['Dark 2 (labels)',eff.sub],['Light 2 (cards)',eff.card],['Accent 1 (header bars)',mixH(eff.brand,eff.head,.72)],['Accent 2 (sheet ground)',eff.ground],['Accent 3 (computed fill)',eff.recess],['Accent 4 (field edge)',eff.edgeD],['Accent 6 (rules)',eff.line],['Hyperlink (nav buttons)','#FFFFFF'],['Followed link (muted)',eff.mute]];
 document.getElementById('slots').innerHTML=slots.map(s=>`<span><i class="sw2" style="background:${s[1]}"></i><small>${s[0]}</small><br><code>${s[1]}</code></span>`).join('');
 const sem=[['Complete',th.ok],['Complete tint',th.okT],['Missing',th.warn],['Missing tint',th.warnT],['Missing edge',th.warnL],['Error',th.bad],['Error tint',th.badT]];
 document.getElementById('sem').innerHTML=sem.map(s=>`<span><i class="sw2" style="background:${s[1]}"></i><small>${s[0]}</small><br><code>${s[1]}</code></span>`).join('');
 fit();save();
}
function fit(){const c=document.getElementById('cmp'),w=c.clientWidth,one=w<1500;c.style.gridTemplateColumns=one?'1fr':'1fr 1fr';const z=Math.min(1,one?(w-24)/824:(w-24)/(824*2+24));document.getElementById('a').style.zoom=z;document.getElementById('b').style.zoom=z}
document.addEventListener('click',e=>{const t=e.target.closest('[data-t],[data-s],[data-b],[data-f]');if(!t)return;if(t.dataset.f)st.surface=t.dataset.f;if(t.dataset.t)st.theme=t.dataset.t;if(t.dataset.s)st.screen=t.dataset.s;if(t.dataset.b)st.brand=t.dataset.b;render()});
document.getElementById('hl').addEventListener('change',e=>{st.hl=e.target.checked?'1':'0';render()});
window.addEventListener('resize',fit);
document.fonts.ready.then(render);render();

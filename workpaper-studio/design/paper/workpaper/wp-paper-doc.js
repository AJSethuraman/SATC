const mk=(x,y,w,label,html)=>{const f=document.createElement('div');f.className='frame';f.style.cssText=`left:${x}px;top:${y}px;width:${w}px`;f.innerHTML=`<div class="cap">${label}</div>${html}`;document.body.appendChild(f);return f};
const sw=h=>`<span class="sw" style="background:${h}"></span><code>${h}</code>`;
const B='#2B3A55',t=T('A',B);
const tb=(head,rows)=>`<table><tr>${head.map(x=>`<th>${x}</th>`).join('')}</tr>${rows.map(r=>`<tr>${r.map(c=>`<td>${/^#[0-9A-F]{6}$/i.test(c)?sw(c):c}</td>`).join('')}</tr>`).join('')}</table>`;
const nav='white 16% over band',sub=tint(B,.7),HD='#3D5A8F',BAR='#38517F',G='#E4E0D9',CD='#EBE7E0',FD='#F7F3EC',RC='#DDD9D2',NA='#D4D0C9',RL='#D3CFC8',ED='#A29E97';
const over=`<div class="hd"><h1>Paper: the full system</h1><p>Direction A taken all the way through: every screen type, every block, every value state, and the exact cell formatting to generate it. Credit uses navy, the reconciliation green, the control test teal: brand changes one color, nothing else.</p></div>
<div class="doc"><h3>The idea in four rules</h3><ul>
<li><b>Three tones, no white.</b> Stone ground, paper cards, paper-white fields. Depth comes from tone, not lines.</li>
<li><b>Fields look like fields.</b> Entered cells are inset: sunken bevel, 3 pt gap to the next. Everything computed is flat and recessed. Locked cells have no fill. A tester can tell what they may touch at a glance.</li>
<li><b>Color means one thing.</b> Green complete / within limit, amber missing, red error / above limit, gray not applicable. Brand color appears in the band and in section rules only.</li>
<li><b>Results never lie.</b> An incomplete calculation reads <i>Not calculated</i>; a missing limit reads <i>Not tested: limit not confirmed</i>. Neither can look like 0 or a pass.</li></ul>
<h3>What changed from the first pass</h3><ul><li>Fields in panels now match every other field. Rating bullets are gone: the text color does the work.</li><li>New screens: analysis, control test, release check, settings, framework, lists.</li><li>New: calculation outcomes, question states, section statuses (below, “Blocks and states”).</li></ul>
<h3>Decisions I made, worth a look</h3><ul><li>Nav buttons are hyperlinked cells in the band, inset by a thick band-colored border.</li><li>“How to test” text is a cell note (red corner), not a row.</li><li>Conditional questions show <i>Not applicable</i> with the reason; if you prefer they can hide the row instead.</li><li>Dates are 2026-10-14, money has no cents except on reconciliation, ratings are plain text.</li></ul></div>`;
const INK='#262421',DK='#2B3A55';
const styles=[
['Ground','Arial 10','—','Soft stone ground '+G+' on every cell','—','—','General'],
['Card','Arial 10','—',CD,'—','—','General'],
['Band title','Arial 14 bold, caps','#FFFFFF',DK+' (family dark)','—','left, indent 1','@'],
['Band subtitle','Arial 8','tint 70% of '+DK,DK,'—','left, indent 1','@'],
['Nav button','Arial 8 bold, caps','#FFFFFF','white 16% over band','raised: top+left white 50%, bottom+right black 35%, 3pt gap in band color','center','@ + HYPERLINK'],
['Status label','Arial 8 bold, caps',DK,G,'—','left','@'],
['Chip (OK / warn / plain)','Arial 10 bold','#1F6F46 / #8A5A00 / '+INK,'#DCEBDD / #F6E3B2 / none','—','center','General'],
['Header bar (card or section)','Arial 10 bold, caps','#FFFFFF',BAR+' (family dark 28% + light 72%)','—','center','@'],
['Header footer (status)','Arial 10 bold','#1F6F46 / #8A5A00 / #6D6A63',CD,'—','right, indent 1','@'],
['Static label (Tester, Account)','Arial 10',DK,CD,'—','left, vcenter','@'],
['Input (all types)','Arial 10','#1A1A1A',FD,'top+left 0.5pt '+ED+'; bottom+right 0.5pt #F9F5EE','text center, comments left, money right','per type'],
['Missing (CF)','Arial 10 italic hint','#8A5A00','#F6E3B2','0.5pt #CF9A33 all sides','as input','—'],
['Not applicable','Arial 10 italic','#6D6A63',NA,'none','center','@'],
['Excluded','Arial 10, strikethrough','#6D6A63','pattern lightUp #CCC8C1 on '+CD,'none','as input','as input'],
['Computed','Arial 10',INK,RC,'none','right','per type'],
['Locked','Arial 10','#6D6A63','none (shows Card)','none','left','@'],
['Error (CF)','Arial 10','#A92A21','#F4D9D4','0.5pt #A92A21 all sides','left','@'],
['Not calculated','Arial 10 italic','#6D6A63','none','bottom 0.5pt dashed #8C857A','center','@'],
['Question group','Arial 11 bold',DK,CD,'—','left','@'],
['Question #','Arial 10 bold',DK,CD,'—','left, vcenter','0.00'],
['Question text','Arial 11',DK,CD,'bottom 0.5pt '+RL,'wrap, vcenter','@ + cell note'],
['Rating (CF by value)','Arial 10','#1F6F46 / #8A5A00 / #A92A21','as Input','as Input','center','list'],
['Table column header','Arial 10 bold, caps',DK,CD,'—','center','@'],
['Row label (Item 1)','Arial 10 regular',DK,CD,'—','left, indent 1','@'],
['Total','Arial 10 bold',INK,'as Computed','none','right','per type'],
['Calc result','Arial 13 bold',INK,'as Computed','none','right','per type'],
['Verdict (CF by text)','Arial 10 bold','#1F6F46 / #A92A21 / #6D6A63 italic','none','none','left, indent 1','@'],
['Note','Arial 9 italic','#6D6A63','none','none','left','@']];
const fmts=[['Money, whole','$#,##0;($#,##0);$0'],['Money, cents (reconciliation)','$#,##0.00;($#,##0.00);$0.00'],['Percent','0.0%'],['Date','yyyy-mm-dd'],['Rating number','0'],['Text','@']];
const cfs=[['Required and empty','=AND(req,ISBLANK(cell))','Missing'],['Entered zero','—','No rule: shows as Input with 0'],['Rating text','=cell="Effective" / "Partially effective" / "Not effective"','font green / amber / red'],['Comment required','=AND(OR(rating="Partially effective",rating="Not effective"),ISBLANK(comment))','Missing on the comment cell'],['Section not applicable','=section_mode="Not applicable"','fills Not applicable on the whole block; inputs locked'],['Excluded row','=excluded_flag=TRUE','Excluded'],['Error','=check_cell=TRUE','Error + message in the cell beside'],['Calculation','=missing_inputs>0 → Not calculated; limit_confirmed<>"Yes" → Not tested: limit not confirmed','Verdict style by text'],['Verdict color','=verdict="Within limit" / "Above limit" / "Not tested…"','font green / red / gray italic']];
const rh=Object.entries(t.rh).map(([a,b])=>[a,b+' pt']);
const spec=`<div class="doc"><h2>Build sheet: Paper</h2><p>Everything below is plain cell formatting, number formats, conditional formats, validation and protection. No shapes, images or macros.</p>
<h3>Sheet</h3><ul><li>Gridlines off · zoom 100% · tab color = brand · all cells filled Ground (A1:XFD1048576)</li><li>Freeze panes below the status strip · print area B:K · landscape, fit to one page wide, margins 0.4″</li><li>Protection on, select unlocked cells only; only Input cells unlocked; no password stored in the file</li><li>Navigation: each button is a cell with <code>=HYPERLINK("#'Analysis'!A1","Analysis")</code></li></ul>
<h3>Columns</h3>${tb(['Column','Width (Excel chars)','Role'],[['A, L','1.3','Gutter (Ground)'],['B','8.4','Row label / question #'],['C','7.9','Label or first field'],['D–K','11.3 each','Fields, merged across as needed'],['Spacer','0.43 (≈3 px)','Inserted between every pair of input fields, filled Card; the widths above exclude spacers']])}
<p style="margin-top:8px">Spacer <b>rows</b>: where fields stack, rows are 15 pt for the field and 3 pt for the gap (the 21 pt rows shown here are one of each). Same fill as Card.</p>
<h3>Row heights (pt)</h3>${tb(['Role','Height'],rh)}
<h3>Cell styles to generate</h3>${tb(['Style','Font','Text color','Fill','Border','Align','Number format'],styles)}
<h3>Number formats</h3>${tb(['Use','Format'],fmts.map(f=>[f[0],'<code>'+f[1]+'</code>']))}
<h3>Conditional formats (in priority order)</h3>${tb(['When','Formula','Result'],cfs.map(c=>[c[0],'<code>'+c[1]+'</code>',c[2]]))}
<h3>Data validation</h3><ul><li>List cells: list from the named range for that list (Lists screen), stop-style error, no input message, in-cell dropdown on</li><li>Number cells: decimal, any value ≥ 0 unless the config says otherwise; dates: date validation</li></ul>
<h3>Palette</h3><div class="chips">${[['Ground (Soft stone)',G],['Card',CD],['Field',FD],['Computed fill',RC],['Not applicable',NA],['Rule',RL],['Field edge',ED],['Static text / band (family dark)',DK],['Header bars',BAR],['Header light shade',HD],['Input text','#1A1A1A'],['Complete','#1F6F46'],['Complete tint','#DCEBDD'],['Missing','#8A5A00'],['Missing tint','#F6E3B2'],['Missing edge','#CF9A33'],['Error','#A92A21'],['Error tint','#F4D9D4'],['Family: credit',DK],['Family: reconciliation','#1F4D3C'],['Family: control test','#1C4F58']].map(c=>`<span>${sw(c[1])}<br><small style="color:#556070">${c[0]}</small></span>`).join('')}</div>
<p style="margin-top:10px">Each color family is one hue in three shades: dark (band, static text), mid (header bars = dark × 0.28 + light × 0.72) and light. Surfaces are derived from one ground color: card +7, field +19, computed −7, not applicable −16, rule −17, edge −62 (per channel).</p></div>`;
const cols=[[640,[['Overview',over]]],[0,[]]];
const place=(x,list)=>list.map(([l,h])=>mk(x,0,l==='Overview'?640:824,l,h));
const groups=[
 {x:0,w:640,items:[['Overview',over]]},
 {x:720,w:824,items:[['Credit file review: workpaper',credit('A')],['Credit file review: analysis',analysis()]]},
 {x:1620,w:824,items:[['Bank reconciliation',recon('A')],['Control test',control()]]},
 {x:2520,w:824,items:[['Blocks and states',catalogue()],['Cell states',states('A')]]},
 {x:3420,w:824,items:[['Release check',admin('check')],['Settings',admin('settings')],['Framework',admin('framework')],['Lists',admin('lists')]]},
 {x:4320,w:824,items:[['Build sheet',spec]]}
];
groups.forEach(g=>g.items.forEach(([l,h])=>{const f=mk(g.x,0,g.w,l,h);f.dataset.g=g.x}));
const layout=()=>groups.forEach(g=>{let y=60;[...document.querySelectorAll('.frame')].filter(f=>+f.dataset.g===g.x).forEach(f=>{f.style.top=y+'px';y+=f.offsetHeight+54})});
themeSheets();layout();document.fonts.ready.then(()=>{layout();setTimeout(layout,400)});

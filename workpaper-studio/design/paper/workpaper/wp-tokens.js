const px=pt=>Math.round(pt*4/3*100)/100;
const rgb=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
const hx=a=>'#'+a.map(v=>Math.round(v).toString(16).padStart(2,'0')).join('').toUpperCase();
const tint=(h,t)=>hx(rgb(h).map(v=>v*(1-t)+255*t));
const S={ink:'#262421',sub:'#5E5A53',mute:'#6F6A62',hair:'#D5D0C5',line:'#BDB6A9',ok:'#1F6F46',okT:'#DCEBDD',warn:'#8A5A00',warnT:'#F6E3B2',warnL:'#CF9A33',bad:'#A92A21',badT:'#F4D9D4',blue:'#2A4474'};
const COLS=[14,64,60,84,84,84,84,84,84,84,84,14];
const chars=p=>Math.round((p-5)/7*10)/10;
function T(k,b){
 const bt=n=>tint(b,n);
 const D={
 A:{cls:'dA',name:'A · Paper',pitch:'Warm stone ground with lighter paper cards. Each section is a card with padding, fields are soft paper tiles sitting on it, and the title band carries floating buttons, not a row of squares.',
  sheet:'#E6E1D8',bw:'1px',fw:{title:400},
  rh:{title:32,sub:13,gap:9,status:20,phd:20,slbl:11,field:22,sechd:26,th:19,row:22,tot:23,q:42,grp:20,calc:17,big:24,note:12},
  fs:{title:16,sub:10,lbl:10,v:10,sec:11,th:10,big:13,note:9},
  st:{in:{fill:'#FDFCF9',fc:S.blue,bd:'#8F8878'},miss:{fill:S.warnT,fc:S.warn,bd:S.warnL},na:{fill:'#DAD5CA',fc:S.mute,bd:'#DAD5CA'},exc:{fill:'hatch',fc:S.mute,bd:S.line},calc:{fill:'#E4DFD4',fc:S.ink,bd:'#E4DFD4'},lock:{fill:'none',fc:S.mute,bd:'transparent'},err:{fill:S.badT,fc:S.bad,bd:S.bad},nc:{fill:'none',fc:S.mute,bd:'#8C857A'}},
  v:{'--card':'#F3F0E9','--btn-fill':'rgba(255,255,255,.16)','--btn-fc':'#FFFFFF','--th-bd':'1px solid '+b,'--sec-bd':'1px solid '+b,'--tot-bd':'1px solid '+S.ink,'--q-bd':'1px solid '+S.hair,'--phd-fill':'#F3F0E9','--phd-fc':b,'--phd-bd':'1px solid '+S.hair,'--bt90':'#DDD8CC'},
  roles:[
   ['Sheet ground',0,'—','—','#E6E1D8 on all cells','none'],
   ['Title band',32,'Arial 16 regular','#FFFFFF',b+' (brand)','none'],
   ['Subtitle',13,'Arial 9 regular',tint(b,.7),b,'none'],
   ['Nav button','title row','Arial 9 regular','#FFFFFF','white 16% over band','3pt border in band color on all sides, so it floats'],
   ['Status strip',20,'Label 8 · value 9 bold',S.sub+' / tone','tone tint on value','none'],
   ['Card (panel or section)','—','—','—','#F3F0E9','none; 10 px ground-colored gap between cards'],
   ['Card header',19,'Arial 9 regular, caps',b,'#F3F0E9','0.5pt bottom '+S.hair],
   ['Field label',21,'Arial 9 regular',S.sub,'card','none'],
   ['Input field (inset)',21,'Arial 10 regular',S.blue,'#FDFCF9','0.5pt inset: top+left #8F8878, bottom+right #FFFFFF'],
   ['Field spacing','3pt','—','—','card color','spacer rows and columns between fields'],
   ['Section header',24,'Arial 11 regular',b,'card','0.5pt bottom '+b],
   ['Question group',17,'Arial 10 bold',S.ink,'card','none'],
   ['Question row',38,'Arial 10 regular, wrap',S.ink,'card','0.5pt bottom '+S.hair],
   ['Table header',16,'Arial 9 regular, caps',S.sub,'card','0.75pt bottom '+b],
   ['Total / computed (flat)',22,'Arial 10 bold',S.ink,'#E4DFD4','none, same spacing as inputs'],
   ['Calculation result',24,'Arial 13 bold',S.ink,'#E4DFD4','none']
  ],
  rules:['Gridlines off · every cell filled with the ground color · freeze panes below the status strip','Cards are B:K filled #F3F0E9; columns A and L stay ground so cards float','Nav buttons: 3pt thick border in the band color around a lighter fill','Input fields are inset: sunken bevel border and a 3pt gap to the next field. Computed cells are flat and recessed, locked cells have no fill','Rating cells: input field with the rating text colored green / amber / red (conditional format on the list value)']},
 B:{cls:'dB',name:'B · Tiles',pitch:'No band and no lines. Every field and table row is a soft tile on a neutral gray ground, kept apart by 2pt gutters in the ground color. Navigation is a row of small tabs.',
  sheet:'#E2E3E0',bw:'2px',fw:{title:400},
  rh:{title:30,sub:13,gap:8,status:20,phd:18,slbl:11,field:18,sechd:24,th:16,row:18,tot:19,q:30,grp:18,calc:18,big:26,note:12},
  fs:{title:18,sub:8,lbl:8,v:9,sec:11,th:8,big:13,note:8},
  st:{in:{fill:'#F3F4F2',fc:S.ink,bd:'#F3F4F2'},miss:{fill:S.warnT,fc:S.warn,bd:S.warnL},na:{fill:'#D3D5D1',fc:S.mute,bd:'#D3D5D1'},exc:{fill:'hatch',fc:S.mute,bd:S.line},calc:{fill:'#CDD0CB',fc:S.ink,bd:'#CDD0CB'},lock:{fill:'none',fc:S.mute,bd:'transparent'},err:{fill:S.badT,fc:S.bad,bd:S.bad},nc:{fill:'none',fc:S.mute,bd:'#8A8D88'}},
  v:{'--card':'none','--btn-fill':'#D3D5D1','--btn-fc':b,'--th-bd':'1px solid '+S.line,'--sec-bd':'1px solid '+b,'--tot-bd':'0 solid transparent','--q-bd':'0 solid transparent','--phd-fill':'none','--phd-fc':b,'--phd-bd':'1px solid '+S.line,'--bt90':'#D3D5D1'},
  roles:[
   ['Sheet ground',0,'—','—','#E2E3E0 on all cells','none'],
   ['Title',30,'Arial 18 regular',b+' (brand)','none','none'],
   ['Subtitle',13,'Arial 9 regular',S.sub,'none','2.25pt bottom '+b+' (thick)'],
   ['Nav tab','title row','Arial 9 regular',b,'#D3D5D1','2pt gutter in ground color'],
   ['Status strip',20,'Label 8 · value 9 bold',S.sub+' / tone','value tile, tone tint','2pt gutter'],
   ['Panel header',18,'Arial 9 bold, caps',b,'none','0.5pt bottom '+S.line],
   ['Field label',18,'Arial 9 regular',S.sub,'none','none'],
   ['Field tile',18,'Arial 10 regular',S.ink,'#F3F4F2','2pt gutter in ground color (thick border)'],
   ['Section header',24,'Arial 11 bold',b,'none','0.5pt bottom '+b],
   ['Question group',18,'Arial 10 bold',S.ink,'none','none'],
   ['Question tile',30,'Arial 10 regular, wrap',S.ink,'#F3F4F2','2pt gutter'],
   ['Rating tile',30,'Arial 10 regular','tone color','tone tint','2pt gutter'],
   ['Table header',16,'Arial 9 regular, caps',S.sub,'none','0.5pt bottom '+S.line],
   ['Table row tile',18,'Arial 10 regular',S.ink,'#F3F4F2','2pt gutter'],
   ['Total tile',19,'Arial 10 bold',S.ink,'#CDD0CB','2pt gutter'],
   ['Calculation result',26,'Arial 13 bold',S.ink,'#CDD0CB','2pt gutter']
  ],
  rules:['Gridlines off · every cell filled with the ground color · freeze panes below the title rule','Gutters: thick (2.25pt) borders in the ground color on every side of a tile — fills never touch','Nav tabs and nothing else live in the title row; the thick bottom rule closes the header','Only lines on the sheet: title rule, section rules, header hairlines','Lightest on borders, heaviest on fill: simple to generate from one tile style']},
 C:{cls:'dC',name:'C · Register',pitch:'A dense audit register on a warm ground. Slim brand band with plain text links, gray section bars, yellow input cells, and a thick colored rail down the left edge showing each section\'s status.',
  sheet:'#ECE9E2',bw:'0 0 1px 0',fw:{title:400},
  rh:{title:24,sub:12,gap:6,status:17,phd:15,slbl:11,field:16,sechd:19,th:15,row:15,tot:16,q:24,grp:15,calc:16,big:21,note:12},
  fs:{title:13,sub:8,lbl:8,v:9,sec:9,th:8,big:12,note:8},
  st:{in:{fill:'#FAF0C6',fc:S.ink,bd:'#DCCB85'},miss:{fill:'#F3C9B5',fc:'#7E2A0C',bd:'#D9764A'},na:{fill:'#DFDBD2',fc:S.mute,bd:'#DFDBD2'},exc:{fill:'hatch',fc:S.mute,bd:S.line},calc:{fill:'none',fc:S.ink,bd:'#CFC9BC'},lock:{fill:'none',fc:S.mute,bd:'transparent'},err:{fill:S.badT,fc:S.bad,bd:S.bad},nc:{fill:'none',fc:S.mute,bd:'#8C857A'}},
  v:{'--card':'none','--btn-fill':'transparent','--btn-fc':'#FFFFFF','--th-bd':'1px solid '+S.ink,'--sec-bd':'0 solid transparent','--tot-bd':'1px solid '+S.ink,'--q-bd':'1px solid #D5D0C5','--phd-fill':'none','--phd-fc':S.sub,'--phd-bd':'1px solid #CFC9BC','--bt90':'#DDD8CC'},
  roles:[
   ['Sheet ground',0,'—','—','#ECE9E2 on all cells','none'],
   ['Title band',24,'Arial 13 regular','#FFFFFF',b+' (brand)','none'],
   ['Subtitle',12,'Arial 9 regular',tint(b,.7),b,'none'],
   ['Nav link','title row','Arial 9 underline','#FFFFFF','band','none'],
   ['Status strip',17,'Label 8 · value 9 bold',S.sub+' / tone','tone tint on value','0.5pt bottom #CFC9BC'],
   ['Panel header',15,'Arial 9 bold, caps',S.sub,'none','0.5pt bottom #CFC9BC'],
   ['Field label',16,'Arial 9 regular',S.sub,'none','none'],
   ['Input field',16,'Arial 10 regular',S.ink,'#FAF0C6','0.5pt bottom #DCCB85'],
   ['Section bar',19,'Arial 10 bold, caps',S.ink,'#DDD8CC','none'],
   ['Section rail','section rows','—','—','—','3pt thick right border on column A: green complete · amber missing · gray optional'],
   ['Question group',15,'Arial 9 bold, caps',S.sub,'none','none'],
   ['Question row',24,'Arial 10 regular, wrap',S.ink,'none','0.5pt bottom #D5D0C5'],
   ['Table header',15,'Arial 9 bold, caps',S.ink,'none','0.5pt top and bottom '+S.ink],
   ['Table row',15,'Arial 10 regular',S.ink,'#FAF0C6 (input)','0.5pt bottom #DCCB85'],
   ['Total row',16,'Arial 10 bold',S.ink,'none','0.5pt top '+S.ink],
   ['Calculation result',21,'Arial 13 bold',S.ink,'none','0.5pt bottom #CFC9BC']
  ],
  rules:['Gridlines off · every cell filled with the ground color · freeze panes below the band','Nothing boxed; separation is hairline and fill','Rail colors are the only large color on the sheet','Smallest row heights of the three','Brand color: band only']}
 };
 const d=D[k];
 const sv={};
 for(const s in d.st){sv['--'+s+'-fill']=d.st[s].fill==='hatch'?'#fff':d.st[s].fill;sv['--'+s+'-fc']=d.st[s].fc;sv['--'+s+'-bd']=d.st[s].bd}
 const vars={'--brand':b,'--bt90':'#F2F2F2','--bt70':'#C6C6C6','--bt90':'#DDD8CC','--cols':COLS.map(c=>c+'px').join(' '),'--sheet':d.sheet,'--bw':d.bw,'--ink':S.ink,'--sub':S.sub,'--mute':S.mute,'--hair':S.hair,'--line':S.line,'--ok':S.ok,'--okT':S.okT,'--warn':S.warn,'--warnT':S.warnT,'--bad':S.bad,'--badT':S.badT,'--blue':S.blue,'--fw-title':d.fw.title,'--fs-title':px(d.fs.title)+'px','--fs-sub':px(d.fs.sub)+'px','--fs-lbl':px(d.fs.lbl)+'px','--fs-v':px(d.fs.v)+'px','--fs-sec':px(d.fs.sec)+'px','--fs-th':px(d.fs.th)+'px','--fs-big':px(d.fs.big)+'px','--fs-note':px(d.fs.note)+'px',...d.v,...sv};
 delete vars['--btn-fill'];vars['--btn-fill']=d.v['--btn-fill'];
 return {...d,k,b,vars,style:Object.entries(vars).map(([a,c])=>a+':'+c).join(';'),px};
}
const NOTE0={in:'Entered by the user',miss:'Required and empty (conditional format)',na:'Text “N/A”, italic, centered',exc:'Pattern fill “light up” + strikethrough',calc:'Formula cell, protected',lock:'Fixed text, protected, no fill',err:'Check formula returns TRUE; message sits beside it',nc:'Italic, dashed bottom border, never a number'};
const NOTE=NOTE0;Object.assign(window,{T,S,COLS,px,chars,tint,NOTE});

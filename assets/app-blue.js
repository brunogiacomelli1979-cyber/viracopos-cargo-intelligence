'use strict';
let app;
try {
  app = JSON.parse(document.getElementById('dados-incorporados').textContent);
  for (const key of ['brasil', 'viracopos', 'comex', 'macro']) {
    if (!Array.isArray(app[key])) throw new Error('Conjunto inválido: ' + key);
    app[key].sort((a, b) => a.mes.localeCompare(b.mes));
  }
} catch (error) {
  document.getElementById('data-status').textContent = 'Não foi possível carregar os dados. Consulte as fontes ou tente recarregar a página.';
  throw error;
}
let janela = 12;
let macroMetrica = 'selic_meta_pct_aa';
let fluxo = 'importacao';
const byId = id => document.getElementById(id);
const fmt = (n, max=1) => n === null || !Number.isFinite(n) ? '—' : n.toLocaleString('pt-BR', {maximumFractionDigits:max,minimumFractionDigits:max});
const parseMonth = s => { const [y,m]=s.split('-'); return new Date(Number(y),Number(m)-1,1); };
const showMonth = s => !s ? '—' : parseMonth(s).toLocaleDateString('pt-BR',{month:'short',year:'numeric'}).replace('.','');
const last = arr => arr.length ? arr[arr.length-1] : null;
const monthIndex = month => Number(month.slice(0, 4)) * 12 + Number(month.slice(5, 7)) - 1;
const referenceMonth = () => byId('competencia').value;
const subset = rows => {
  const end = monthIndex(referenceMonth());
  return rows.filter(row => monthIndex(row.mes) <= end && (janela === Infinity || monthIndex(row.mes) > end - janela));
};
const set = (id, val) => { const el=byId(id); if(el) el.textContent=val; };
function lineChart(target, rawRows, series, message, opts={}) {
  const el=byId(target); if(!el) return; el.textContent='';
  const selected = subset(rawRows);
  const data = [];
  if (selected.length) {
    // Include missing calendar months so lines never bridge an unavailable month.
    for (let m = monthIndex(selected[0].mes); m <= monthIndex(selected.at(-1).mes); m++) {
      const mes = `${Math.floor(m / 12)}-${String(m % 12 + 1).padStart(2, '0')}`;
      data.push(selected.find(row => row.mes === mes) || {mes});
    }
  }
  if (!data.some(row => series.some(s => Number.isFinite(row[s.key])))) {
    el.innerHTML = '<div class="chart-empty"><strong>Sem dados neste período</strong></div>';
    const note = document.createElement('span'); note.textContent = message;
    el.firstChild.appendChild(note); return;
  }
  if (!data.length) {el.innerHTML='<div class="chart-empty"><svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M3 27h26M4 4v23M7 22l7-8 7 3 6-11" stroke-linecap="round" stroke-linejoin="round"/></svg><strong>Série ainda não carregada</strong>'+message+'</div>'; return;}
  const w=850,h=240,pad={l:62,r:20,t:15,b:32}; const x0=pad.l,x1=w-pad.r,y0=pad.t,y1=h-pad.b;
  const values=data.flatMap(d=>series.map(s=>d[s.key])).filter(Number.isFinite);
  let low=Math.min(...values),high=Math.max(...values);
  if (opts.zero && low>=0) low=0;
  if(low===high){ const gap=Math.max(Math.abs(low)*.12,1); low=low-gap;high=high+gap;}
  else{const diff=high-low;high+=diff*.12;low-=diff*.06;if(opts.zero && low<0)low=0;}
  const x=i=>data.length===1?(x0+x1)/2:x0+(x1-x0)*i/(data.length-1);
  const y=v=>y1-(v-low)/(high-low)*(y1-y0);
  const ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.setAttribute('role','img');
  svg.setAttribute('aria-label', el.getAttribute('aria-label'));
  const add=(tag,attrs={},txt)=>{const node=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>node.setAttribute(k,String(v)));if(txt!==undefined)node.textContent=txt;svg.appendChild(node);return node;};
  for(let i=0;i<5;i++){const gy=y0+(y1-y0)*i/4;add('line',{x1:x0,y1:gy,x2:x1,y2:gy,stroke:opts.dark?'#295277':'#295277','stroke-dasharray':'3,6'});const v=high-(high-low)*i/4;add('text',{x:x0-11,y:gy+4,'text-anchor':'end',fill:'#a8c0d3','font-size':'12'},opts.axisValue?opts.axisValue(v):fmt(v,0));}
  const labelIndices=[...new Set(Array.from({length:Math.min(data.length,6)},(_,i)=>Math.round(i*(data.length-1)/Math.max(1,Math.min(data.length,6)-1))))];
  labelIndices.forEach(i=>add('text',{x:x(i),y:h-5,'text-anchor':'middle',fill:'#a8c0d3','font-size':'12'},showMonth(data[i].mes)));
  series.forEach(s=>{
    const pts=data.map((r,i)=>Number.isFinite(r[s.key])?{i, value:r[s.key],mes:r.mes}:null);
    let d='';let prev=false;pts.forEach(point=>{if(!point){prev=false;return;}d+=(prev?' L':' M')+x(point.i).toFixed(1)+','+y(point.value).toFixed(1);prev=true;});
    add('path',{d,fill:'none',stroke:s.color,'stroke-width':3,'stroke-linecap':'round','stroke-linejoin':'round'});
    pts.filter(Boolean).forEach(point=>{let c=add('circle',{cx:x(point.i),cy:y(point.value),r:3.7,fill:s.color,stroke:'#102945','stroke-width':2});let t=document.createElementNS(ns,'title');t.textContent=`${s.label} · ${showMonth(point.mes)} · ${fmt(point.value,2)} ${s.unit||''}`;c.appendChild(t);});
  });
  const plot=document.createElement('div');plot.className='chart-plot';plot.tabIndex=0;plot.setAttribute('role','region');plot.setAttribute('aria-label','Área do gráfico; rolagem horizontal disponível em telas pequenas');plot.appendChild(svg);el.appendChild(plot);
  const details = document.createElement('details');
  const summary = document.createElement('summary'); summary.textContent = 'Consultar valores do gráfico';
  details.appendChild(summary);
  const table = document.createElement('table');
  const caption = document.createElement('caption'); caption.textContent = el.getAttribute('aria-label'); table.appendChild(caption);
  const head = table.createTHead().insertRow();
  ['Competência', ...series.map(s => `${s.label} (${s.unit || ''})`)].forEach(text => { const cell = document.createElement('th'); cell.scope = 'col'; cell.textContent = text; head.appendChild(cell); });
  const body = table.createTBody();
  data.forEach(row => { const tr = body.insertRow(); [showMonth(row.mes), ...series.map(s => fmt(row[s.key], 2))].forEach(text => { tr.insertCell().textContent = text; }); });
  const scroll = document.createElement('div'); scroll.className = 'table-scroll'; scroll.appendChild(table); details.appendChild(scroll); el.appendChild(details);
}
function seriesFromComex(){const m=new Map();app.comex.forEach(r=>{const row=m.get(r.mes)||{mes:r.mes,importacao:null,exportacao:null};row[r.fluxo]=(row[r.fluxo]??0)+(r.valor_fob_usd/1e6);m.set(r.mes,row)});return [...m.values()].sort((a,b)=>a.mes.localeCompare(b.mes));}
function renderKPIs(){
  const cargo=last(subset(app.viracopos));set('kpi-carga',cargo?fmt(cargo.embarque_internacional_t+cargo.desembarque_internacional_t,0):'—');set('kpi-carga-mes',cargo?'Ref. '+showMonth(cargo.mes):'Sem dados ANAC no período');
  const comex=subset(seriesFromComex());const ci=last(comex.filter(x=>Number.isFinite(x.importacao)));const ce=last(comex.filter(x=>Number.isFinite(x.exportacao)));
  set('kpi-imp',ci?fmt(ci.importacao,1):'—');set('kpi-exp',ce?fmt(ce.exportacao,1):'—');set('kpi-imp-mes',ci?'Ref. '+showMonth(ci.mes):'Aguardando dados MDIC');set('kpi-exp-mes',ce?'Ref. '+showMonth(ce.mes):'Aguardando dados MDIC');
  const br=last(subset(app.brasil));set('kpi-brasil',br?fmt(br.exportacoes_usd_bi+br.importacoes_usd_bi,1):'—');set('kpi-brasil-mes',br?'Ref. '+showMonth(br.mes):'Sem dados MDIC no período');set('hero-competencia','Consulta até: '+showMonth(referenceMonth()));
}
function renderCharts(){
  lineChart('grafico-carga',app.viracopos,[{key:'desembarque_internacional_t',label:'Desembarque',color:'#58d0c7',unit:'t'},{key:'embarque_internacional_t',label:'Embarque',color:'#f3bd3f',unit:'t'}],'Aguardando a inserção do histórico de movimentação ANAC.',{zero:true});
  lineChart('grafico-comex',seriesFromComex(),[{key:'importacao',label:'Importação',color:'#58d0c7',unit:'US$ mi'},{key:'exportacao',label:'Exportação',color:'#f3bd3f',unit:'US$ mi'}],'Aguardando dados de importação e exportação por URF.',{zero:true});
  lineChart('grafico-brasil',app.brasil,[{key:'exportacoes_usd_bi',label:'Exportações Brasil',color:'#58d0c7',unit:'US$ bi'},{key:'importacoes_usd_bi',label:'Importações Brasil',color:'#f3bd3f',unit:'US$ bi'}],'Não há dados nacionais importados para este intervalo.',{zero:true});
  const meta={selic_meta_pct_aa:['Evolução da taxa Selic','Meta Selic no último dia do mês','% ao ano'],dolar_venda_medio_brl:['Evolução do dólar comercial','Taxa de venda média diária por mês','R$/US$'],ipca_pct_mes:['Inflação medida pelo IPCA','Variação percentual do índice no mês','% no mês']}[macroMetrica];
  set('macro-title',meta[0]);set('macro-desc',meta[1]);const serie=subset(app.macro).filter(r=>Number.isFinite(r[macroMetrica]));const point=last(serie);set('macro-valor',point?fmt(point[macroMetrica],2)+(macroMetrica==='dolar_venda_medio_brl'?'':'%'):'—');set('macro-meta',point?`${showMonth(point.mes)} · ${meta[2]}`:'Sem dados deste indicador no período');
  lineChart('grafico-macro',app.macro,[{key:macroMetrica,label:meta[0],color:'#58d0c7',unit:meta[2]}],'Consulte o estado da coleta e a última competência em Fontes.',{axisValue:value=>fmt(value,2)});
}
function renderTable(){
 const tbody=byId('tabela-setores'); if(!tbody) return; tbody.textContent=''; const items=subset(app.comex).filter(r=>r.fluxo===fluxo); const ultimo=items.reduce((max,r)=>r.mes>max?r.mes:max,''); const filtered=items.filter(r=>r.mes===ultimo).sort((a,b)=>b.valor_fob_usd-a.valor_fob_usd); const total=filtered.reduce((v,r)=>v+r.valor_fob_usd,0);
 if(!filtered.length){const tr=document.createElement('tr');const td=document.createElement('td');td.colSpan=5;td.className='no-data';td.textContent='Aguardando arquivo consolidado de setores do Comex Stat.';tr.appendChild(td);tbody.appendChild(tr);return;}
 filtered.forEach(r=>{const tr=document.createElement('tr');[r.setor,showMonth(r.mes),'US$ '+fmt(r.valor_fob_usd/1e6,2)+' mi',fmt(r.kg_liquido/1000,1)+' t',total?fmt(r.valor_fob_usd/total*100,1)+'%':'—'].forEach((t,i)=>{const td=document.createElement('td');td.textContent=t;if(i>=2)td.className='numeric';tr.appendChild(td);});tbody.appendChild(tr);});
}
function renderStatus(){const values=[...app.viracopos,...app.brasil,...app.comex,...app.macro].map(r=>r.mes);const novo=values.sort().at(-1);set('status-chip',novo?'● Base compilada · '+showMonth(novo):'● Painel em implantação');try{set('last-build','Compilação técnica: '+new Date(app.gerado_em_utc).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'})+' (Brasília)');}catch{set('last-build','Compilação: —');}}
function renderAll(){renderKPIs();renderCharts();renderTable();}
const availableMonths = [...new Set([...app.brasil,...app.viracopos,...app.comex,...app.macro].map(r=>r.mes))].sort();
availableMonths.forEach(month => {const option=document.createElement('option');option.value=month;option.textContent=showMonth(month);byId('competencia').appendChild(option);});
if(availableMonths.length) byId('competencia').value=availableMonths.at(-1);
else {const option=document.createElement('option');option.value=new Date().toISOString().slice(0,7);option.textContent='Sem competências';byId('competencia').appendChild(option);byId('competencia').disabled=true;}
byId('competencia').addEventListener('change',()=>{renderAll();set('data-status','Consulta atualizada até '+showMonth(referenceMonth()));});
byId('janela').addEventListener('change',e=>{janela=e.target.value==='all'?Infinity:Number(e.target.value);renderAll();set('data-status','Janela atualizada: '+e.target.selectedOptions[0].textContent);});
byId('fluxo').addEventListener('change',e=>{fluxo=e.target.value;renderTable();});
document.querySelectorAll('[data-metric]').forEach(btn=>btn.addEventListener('click',()=>{macroMetrica=btn.dataset.metric;document.querySelectorAll('[data-metric]').forEach(x=>{x.classList.toggle('active',x===btn);x.setAttribute('aria-pressed',String(x===btn));});renderCharts();}));
renderKPIs();renderCharts();renderTable();renderStatus();
const sourceLabels={brasil:'Brasil / MDIC',viracopos:'Carga aérea / ANAC',comex:'Comex / URF',macro:'Macroeconomia / BCB'};
Object.entries(sourceLabels).forEach(([key,label])=>{
  const metadata=app.metadados[key];const row=document.createElement('p');
  row.textContent=`${label}: ${metadata.referencia_final?showMonth(metadata.referencia_final):'sem observações'} · ${metadata.status}. ${metadata.limitacoes}`;
  byId('source-status').appendChild(row);
});
const collectionFailures=Object.values(app.coleta_bcb).filter(value=>typeof value==='object'&&value.status?.startsWith('falha'));
if(collectionFailures.length){const notice=document.createElement('p');notice.textContent='A última tentativa de coleta teve falhas. O histórico disponível foi preservado.';byId('source-status').appendChild(notice);}
Object.entries({selic_meta_pct_aa:'Selic',dolar_venda_medio_brl:'Dólar',ipca_pct_mes:'IPCA'}).forEach(([key,label])=>{
  const point=last(app.macro.filter(row=>Number.isFinite(row[key])));
  const receipt=app.metadados.macro.coletas_por_serie?.[key];
  const row=document.createElement('p');row.textContent=`${label}: ${point?showMonth(point.mes):'sem observações'}${receipt?' · coleta '+new Date(receipt.coletado_em_utc).toLocaleDateString('pt-BR',{timeZone:'America/Sao_Paulo'}):''}.`;
  byId('source-status').appendChild(row);
});
const mobileToggle=document.querySelector('.mobile-toggle');
if(mobileToggle){const closeMenu=()=>{document.querySelector('.main-nav').classList.remove('open');mobileToggle.setAttribute('aria-expanded','false');mobileToggle.setAttribute('aria-label','Abrir menu');};mobileToggle.addEventListener('click',()=>{const n=document.querySelector('.main-nav');n.classList.toggle('open');const open=n.classList.contains('open');mobileToggle.setAttribute('aria-expanded',String(open));mobileToggle.setAttribute('aria-label',open?'Fechar menu':'Abrir menu');});document.querySelectorAll('.main-nav a').forEach(a=>a.addEventListener('click',closeMenu));document.addEventListener('keydown',e=>{if(e.key==='Escape'&&mobileToggle.getAttribute('aria-expanded')==='true'){closeMenu();mobileToggle.focus();}});}
const sectionLinks = [...document.querySelectorAll('.nav-link'), ...document.querySelectorAll('.rail-link')];
const sectionMap = new Map(sectionLinks.map(link => [link.getAttribute('href'), []]));
sectionLinks.forEach(link => sectionMap.get(link.getAttribute('href')).push(link));
const sections = [...document.querySelectorAll('.section-anchor[id]')];
const activate = (id) => { sectionMap.forEach((links, href) => links.forEach(link => {const active=href === '#'+id;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');})); };
let scrollQueued=false;
function updateNavigation(){const offset=document.querySelector('.site-header').getBoundingClientRect().bottom+24;const current=[...sections].reverse().find(section=>section.getBoundingClientRect().top<=offset)||sections[0];if(current)activate(current.id);scrollQueued=false;}
window.addEventListener('scroll',()=>{if(!scrollQueued){scrollQueued=true;requestAnimationFrame(updateNavigation);}},{passive:true});
window.addEventListener('resize',updateNavigation);updateNavigation();
document.querySelectorAll('a[href^="#"]').forEach(link=>link.addEventListener('click',()=>{const id=link.getAttribute('href').slice(1); if(id) activate(id);}));
const photoUrl='https://commons.wikimedia.org/wiki/Special:FilePath/Viracopos-Campinas_International_Airport_2017_003.jpg?width=1200';
const testPhoto=new Image();
testPhoto.onload=()=>{const credit=byId('hero-credit');if(credit){credit.innerHTML='FOTO: MIKE PEEL / CC BY-SA 4.0 ↗';}};
testPhoto.src=photoUrl;

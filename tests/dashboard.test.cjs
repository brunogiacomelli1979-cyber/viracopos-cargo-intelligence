// Regression tests execute the production calculation functions, with no browser dependency.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('assets/app-blue.js','utf8');
const prefix = source.slice(source.indexOf('let janela'),source.indexOf('function lineChart'));
const aggregation = source.slice(source.indexOf('function seriesFromComex'),source.indexOf('function renderKPIs'));
function calculations(rows=[], month='2026-09') {
  const context=vm.createContext({app:{comex:rows},document:{getElementById:()=>({value:month})}});
  vm.runInContext(prefix+'\n'+aggregation,context);
  return expression=>JSON.parse(JSON.stringify(vm.runInContext(expression,context)));
}
test('12 months means calendar months, excluding gaps and future rows',()=>{
  const run=calculations();
  assert.deepEqual(run("subset([{mes:'2024-01'},{mes:'2025-09'},{mes:'2025-10'},{mes:'2026-09'},{mes:'2026-10'}])"),[{mes:'2025-10'},{mes:'2026-09'}]);
});
test('missing Comex flow stays null while measured zero remains zero',()=>{
  const run=calculations([{mes:'2026-09',fluxo:'importacao',valor_fob_usd:0}]);
  assert.deepEqual(run('seriesFromComex()'),[{mes:'2026-09',importacao:0,exportacao:null}]);
});
test('Comex sums sectors in millions and sorts months',()=>{
  const run=calculations([{mes:'2026-09',fluxo:'exportacao',valor_fob_usd:2e6},{mes:'2026-08',fluxo:'importacao',valor_fob_usd:1e6},{mes:'2026-09',fluxo:'exportacao',valor_fob_usd:3e6}]);
  assert.deepEqual(run('seriesFromComex()'),[{mes:'2026-08',importacao:1,exportacao:null},{mes:'2026-09',importacao:null,exportacao:5}]);
});
test('all history still respects selected final competence',()=>{
  const run=calculations();
  assert.deepEqual(run("janela=Infinity;subset([{mes:'2000-01'},{mes:'2026-10'}])"),[{mes:'2000-01'}]);
});
test('default reference prefers a month shared by every available source',()=>{
  const run=calculations();
  assert.equal(run("defaultReferenceMonth({viracopos:[{mes:'2025-12'},{mes:'2026-01'}],comex:[{mes:'2025-12'},{mes:'2026-01'}],brasil:[{mes:'2025-12'}],macro:[{mes:'2025-12'},{mes:'2026-09'}]})"),'2025-12');
});
test('sparse national context cannot select an empty core airport month',()=>{
  const run=calculations();
  assert.equal(run("defaultReferenceMonth({viracopos:[{mes:'2025-12'}],comex:[{mes:'2025-12'},{mes:'2026-09'}],brasil:[{mes:'2026-09'}],macro:[{mes:'2026-09'}]})"),'2025-12');
});
test('published default period provides all four real headline indicators',()=>{
  const snapshot=JSON.parse(fs.readFileSync('data/dashboard.json','utf8'));
  let month='';
  const context=vm.createContext({app:snapshot,document:{getElementById:()=>({value:month})}});
  vm.runInContext(prefix+'\n'+aggregation,context);
  month=vm.runInContext('defaultReferenceMonth(app)',context);
  assert.ok(month,'a shared reference must be available');
  for(const expression of ["subset(app.viracopos).at(-1)?.carga_internacional_t", "subset(seriesFromComex()).at(-1)?.importacao", "subset(seriesFromComex()).at(-1)?.exportacao", "subset(app.brasil).at(-1)?.exportacoes_usd_bi"]){
    assert.ok(Number.isFinite(vm.runInContext(expression,context)),expression+' must not be an empty placeholder');
  }
});

test('RIMA/RMA preview retains provenance and can distinguish passenger flights with cargo',()=>{
  const comparison=JSON.parse(fs.readFileSync('data/comparativo_rima_rma.json','utf8'));
  assert.equal(comparison.status,'preliminar_com_divergencias');
  assert.equal(comparison.versao,2);
  const manifest=JSON.parse(fs.readFileSync('data/anac/rima/manifesto.json','utf8'));
  const expected=Object.keys(manifest.competencias).sort();
  assert.deepEqual(comparison.perfil_voos.map(item=>item.mes),expected);
  assert.equal(comparison.meses_anac,expected.length);
  const monthSet=new Set(comparison.serie_mensal.map(row=>row.mes));
  assert.equal(comparison.serie_mensal.length,monthSet.size*2);
  for(const month of monthSet){
    assert.deepEqual(comparison.serie_mensal.filter(row=>row.mes===month).map(row=>row.natureza).sort(),['domestica','internacional']);
  }
  assert.equal(comparison.meses_com_duas_fontes,1);
  const sparse2020=comparison.serie_mensal.find(r=>r.mes==='2020-01'&&r.natureza==='internacional');
  assert.equal(sparse2020.rma_carga_t,null);
  const sparse2025=comparison.serie_mensal.find(r=>r.mes==='2025-01'&&r.natureza==='internacional');
  assert.equal(sparse2025.rima_carga_t,null);

  assert.equal(comparison.liberado_para_indicadores,false);
  const international=comparison.recortes.find(r=>r.mes==='2024-01'&&r.natureza==='internacional');
  assert.equal(international.rima_carga_t,16015.919);
  assert.equal(international.rma_carga_t,13962);
  assert.equal(international.qualidade_rma,'transcricao_preliminar_pdf_nao_certificado');
  const p=comparison.perfil_voos.find(r=>r.mes==='2024-01');
  assert.equal(p.movimentos,9348);
  for(const nature of ['internacional','domestica']){
    const n=p.por_natureza[nature];
    assert.equal(n.movimentos,n.com_carga+n.sem_carga+(n.carga_indeterminada||0));
  }
  assert.ok(p.por_natureza.internacional.com_carga__com_passageiros>0);
  assert.equal(p.nao_e_fluxo_aduaneiro,true);
  const template=fs.readFileSync('index.template.html','utf8');
  for(const id of ['comparativo-mes','comparativo-indicador','comparativo-natureza','comparativo-fonte','perfil-mes','perfil-voos-anac','serie-metrica','serie-natureza','grafico-series-fontes']){
    assert.ok(template.includes('id="'+id+'"'));
  }
});

test('history chart respects true missing months and preview source labels',()=>{
  const js=fs.readFileSync('assets/app-blue.js','utf8');
  assert.ok(js.includes('options.fullHistory ? rows : subset(rows)'));
  assert.ok(js.includes('profileMonth.value'));
  assert.ok(js.includes('data.serie_mensal || []'));
});

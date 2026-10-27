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

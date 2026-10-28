'use strict';
let app;
try {
  app = JSON.parse(document.getElementById('dados-incorporados').textContent);
  for (const name of ['brasil', 'viracopos', 'comex', 'macro']) {
    if (!Array.isArray(app[name])) throw new Error('Base inválida: ' + name);
    app[name].sort((a, b) => a.mes.localeCompare(b.mes));
  }
} catch (error) {
  document.getElementById('data-status').classList.remove('sr-only');
  document.getElementById('data-status').textContent = 'Não foi possível carregar a base. Recarregue a página ou consulte os arquivos de dados.';
  throw error;
}
let janela = 12;
let macroMetrica = 'selic_meta_pct_aa';
let fluxo = 'importacao';
let currentView = 'visao-geral';
const byId = id => document.getElementById(id);
const fmt = (value, digits = 1) => Number.isFinite(value) ? value.toLocaleString('pt-BR', {minimumFractionDigits: digits, maximumFractionDigits: digits}) : '—';
const parseMonth = month => new Date(Number(month.slice(0, 4)), Number(month.slice(5, 7)) - 1, 1);
const showMonth = month => month ? parseMonth(month).toLocaleDateString('pt-BR', {month: 'short', year: 'numeric'}).replace('.', '').replace(' de ', '/') : '—';
const last = rows => rows.length ? rows[rows.length - 1] : null;
const monthIndex = month => Number(month.slice(0, 4)) * 12 + Number(month.slice(5, 7)) - 1;
const referenceMonth = () => byId('competencia').value;
const subset = rows => {
  const end = monthIndex(referenceMonth());
  return rows.filter(row => monthIndex(row.mes) <= end && (janela === Infinity || monthIndex(row.mes) > end - janela));
};
const set = (id, value) => {const node = byId(id); if (node) node.textContent = value;};
const node = (tag, className, content) => {const element = document.createElement(tag); if (className) element.className = className; if (content !== undefined) element.textContent = content; return element;};
const dateText = stamp => stamp ? new Date(stamp).toLocaleDateString('pt-BR', {timeZone: 'America/Sao_Paulo'}) : 'Não registrada';
const blue = '#2563b8';
const gold = '#c3931c';
const cargoSeries = [{key: 'carga_internacional_t', label: 'Internacional', color: blue, unit: 't'}, {key: 'carga_domestica_t', label: 'Doméstica', color: gold, unit: 't'}];
const macroLabels = {
  selic_meta_pct_aa: ['Taxa Selic', 'Meta no último registro disponível do mês', '% a.a.'],
  dolar_venda_medio_brl: ['Dólar comercial', 'Média das cotações de venda publicadas no mês', 'R$/US$'],
  ipca_pct_mes: ['Inflação · IPCA', 'Variação mensal do índice de preços', '% no mês']
};
function defaultReferenceMonth(sources) {
  const nonempty = ['viracopos', 'comex', 'brasil', 'macro'].map(key => sources[key] || []).filter(rows => rows.length);
  const months = [...new Set(nonempty.flatMap(rows => rows.map(row => row.mes)))].sort();
  const common = months.filter(month => nonempty.every(rows => rows.some(row => row.mes === month)));
  const core = [sources.viracopos || [], sources.comex || []].filter(rows => rows.length);
  const coreCommon = core.length ? months.filter(month => core.every(rows => rows.some(row => row.mes === month))) : [];
  return common.at(-1) || coreCommon.at(-1) || sources.viracopos?.at(-1)?.mes || sources.comex?.at(-1)?.mes || months.at(-1);
}

function lineChart(target, rows, series, message, options = {}) {
  const element = byId(target);
  if (!element) return;
  element.replaceChildren();
  const selected = subset(rows);
  if (!selected.some(row => series.some(item => Number.isFinite(row[item.key])))) {
    const empty = node('div', 'chart-empty');
    empty.append(node('strong', '', 'Sem observações neste período'), node('p', '', message));
    const link = node('a', '', 'Consultar cobertura e fontes ↗'); link.href = '#metodo'; empty.append(link);
    element.append(empty); return;
  }
  const byMonth = new Map(selected.map(row => [row.mes, row]));
  const data = [];
  for (let index = monthIndex(selected[0].mes); index <= monthIndex(selected.at(-1).mes); index++) {
    const mes = `${Math.floor(index / 12)}-${String(index % 12 + 1).padStart(2, '0')}`;
    data.push(byMonth.get(mes) || {mes});
  }
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  const width = 700, height = 235, left = 55, right = 686, top = 15, bottom = 198;
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('tabindex', '0'); svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', element.getAttribute('aria-label') + '. Utilizar as setas para consultar os meses; valores também disponíveis na tabela.');
  const add = (tag, attributes, text) => {
    const item = document.createElementNS(ns, tag);
    Object.entries(attributes).forEach(([key, value]) => item.setAttribute(key, String(value)));
    if (text !== undefined) item.textContent = text;
    svg.append(item); return item;
  };
  const values = data.flatMap(row => series.map(item => row[item.key])).filter(Number.isFinite);
  let low = Math.min(...values), high = Math.max(...values);
  if (options.zero && low >= 0) low = 0;
  const gap = Math.max(high - low, Math.abs(high) * 0.05, 0.1);
  high += gap * 0.12;
  if (!(options.zero && low >= 0)) low -= gap * 0.1;
  const x = index => data.length === 1 ? (left + right) / 2 : left + (right - left) * index / (data.length - 1);
  const y = value => bottom - (value - low) / (high - low) * (bottom - top);
  for (let index = 0; index < 5; index++) {
    const tickY = top + (bottom - top) * index / 4;
    const tick = high - (high - low) * index / 4;
    add('line', {x1: left, x2: right, y1: tickY, y2: tickY, stroke: '#e6edf4', 'stroke-dasharray': '3,4'});
    add('text', {x: left - 9, y: tickY + 4, fill: '#8494a7', 'text-anchor': 'end', 'font-size': 11}, fmt(tick, options.decimals ?? (high < 10 ? 1 : 0)));
  }
  const labels = [...new Set(Array.from({length: Math.min(5, data.length)}, (_, index) => Math.round(index * (data.length - 1) / Math.max(1, Math.min(5, data.length) - 1))))];
  labels.forEach(index => add('text', {x: x(index), y: height - 7, fill: '#8494a7', 'font-size': 11, 'text-anchor': data.length === 1 ? 'middle' : index === 0 ? 'start' : index === data.length - 1 ? 'end' : 'middle'}, showMonth(data[index].mes)));
  series.forEach((item, seriesIndex) => {
    let path = '', connected = false;
    data.forEach((row, index) => {
      if (!Number.isFinite(row[item.key])) {connected = false; return;}
      path += `${connected ? ' L' : ' M'}${x(index).toFixed(2)},${y(row[item.key]).toFixed(2)}`; connected = true;
    });
    add('path', {d: path, fill: 'none', stroke: item.color, 'stroke-width': 2.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-dasharray': seriesIndex === 1 ? '6,3' : 'none'});
    data.forEach((row, index) => {
      if (!Number.isFinite(row[item.key])) return;
      const point = add('circle', {cx: x(index), cy: y(row[item.key]), r: data.length > 36 ? 2 : 3.1, fill: item.color, stroke: '#fff', 'stroke-width': 1.5});
      const title = document.createElementNS(ns, 'title'); title.textContent = `${showMonth(row.mes)} · ${item.label}: ${fmt(row[item.key], 2)} ${item.unit}`; point.append(title);
    });
  });
  const cursor = add('line', {x1: x(data.length - 1), x2: x(data.length - 1), y1: top, y2: bottom, stroke: '#aebed0', 'stroke-dasharray': '3,4', opacity: 0});
  const readout = node('div', 'chart-readout'); readout.setAttribute('aria-live', 'polite');
  let cursorIndex = data.length - 1;
  const show = index => {
    cursorIndex = Math.max(0, Math.min(data.length - 1, index));
    const row = data[cursorIndex]; cursor.setAttribute('x1', x(cursorIndex)); cursor.setAttribute('x2', x(cursorIndex));
    readout.replaceChildren(node('strong', '', showMonth(row.mes)), ...series.map(item => node('span', '', `${item.label}: ${fmt(row[item.key], 2)} ${item.unit}`)));
  };
  svg.addEventListener('pointermove', event => {
    const bounds = svg.getBoundingClientRect(); const svgX = (event.clientX - bounds.left) / bounds.width * width;
    show(Math.round((svgX - left) / (right - left) * Math.max(data.length - 1, 1))); cursor.setAttribute('opacity', 1);
  });
  svg.addEventListener('pointerleave', () => {cursor.setAttribute('opacity', 0); show(data.length - 1);});
  svg.addEventListener('focus', () => {show(cursorIndex); cursor.setAttribute('opacity', 1);});
  svg.addEventListener('keydown', event => {if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {event.preventDefault(); show(cursorIndex + (event.key === 'ArrowRight' ? 1 : -1));}});
  const plot = node('div', 'chart-plot'); plot.append(svg); element.append(plot, readout); show(data.length - 1);
  const details = node('details'); details.append(node('summary', '', 'Consultar valores e competências'));
  const table = node('table'); table.append(node('caption', '', element.getAttribute('aria-label')));
  const heading = table.createTHead().insertRow();
  ['Competência', ...series.map(item => `${item.label} (${item.unit})`)].forEach(text => {const cell = node('th', '', text); cell.scope = 'col'; heading.append(cell);});
  const body = table.createTBody(); data.forEach(row => {const tr = body.insertRow(); [showMonth(row.mes), ...series.map(item => fmt(row[item.key], 2))].forEach(text => {tr.insertCell().textContent = text;});});
  const scroll = node('div', 'table-scroll'); scroll.append(table); details.append(scroll); element.append(details);
}

function seriesFromComex() {
  const months = new Map();
  app.comex.forEach(item => {
    const row = months.get(item.mes) || {mes: item.mes, importacao: null, exportacao: null};
    row[item.fluxo] = (row[item.fluxo] ?? 0) + item.valor_fob_usd / 1e6; months.set(item.mes, row);
  });
  return [...months.values()].sort((a, b) => a.mes.localeCompare(b.mes));
}
function renderKPIs() {
  const cargo = last(subset(app.viracopos));
  set('kpi-carga', cargo ? fmt(cargo.carga_internacional_t, 0) : '—');
  set('kpi-carga-mes', cargo ? `Ref. ${showMonth(cargo.mes)} · SBKP` : 'Sem observações no período');
  const trade = subset(seriesFromComex());
  const imports = last(trade.filter(row => Number.isFinite(row.importacao)));
  const exports = last(trade.filter(row => Number.isFinite(row.exportacao)));
  set('kpi-imp', imports ? fmt(imports.importacao) : '—'); set('kpi-exp', exports ? fmt(exports.exportacao) : '—');
  set('kpi-imp-mes', imports ? `Ref. ${showMonth(imports.mes)} · recorte aduaneiro` : 'Sem observações no período');
  set('kpi-exp-mes', exports ? `Ref. ${showMonth(exports.mes)} · recorte aduaneiro` : 'Sem observações no período');
  const brazil = last(subset(app.brasil));
  set('kpi-brasil', brazil ? fmt(brazil.exportacoes_usd_bi + brazil.importacoes_usd_bi) : '—');
  set('kpi-brasil-mes', brazil ? `Ref. ${showMonth(brazil.mes)} · todas as vias` : 'Sem observações no período');
  const change = (id, rows, point, calculate) => {
    const target = byId(id); target.replaceChildren();
    if (!point) return;
    const priorMonth = `${Number(point.mes.slice(0, 4)) - 1}${point.mes.slice(4)}`;
    const prior = rows.find(row => row.mes === priorMonth);
    if (!prior || !Number.isFinite(calculate(prior)) || calculate(prior) === 0) return;
    const delta = (calculate(point) / calculate(prior) - 1) * 100;
    target.append(node('b', '', `${delta > 0 ? '+' : ''}${fmt(delta)}%`), document.createTextNode('vs. mesmo mês do ano anterior'));
  };
  change('kpi-carga-delta', app.viracopos, cargo, row => row.carga_internacional_t);
  change('kpi-imp-delta', seriesFromComex(), imports, row => row.importacao);
  change('kpi-exp-delta', seriesFromComex(), exports, row => row.exportacao);
  change('kpi-brasil-delta', app.brasil, brazil, row => row.exportacoes_usd_bi + row.importacoes_usd_bi);
}

function sectorRows(selectedFlow) {
  const rows = subset(app.comex).filter(row => row.fluxo === selectedFlow);
  const month = rows.at(-1)?.mes;
  return rows.filter(row => row.mes === month).sort((a, b) => b.valor_fob_usd - a.valor_fob_usd);
}
function sectorBars(id, rows, limit = 5) {
  const container = byId(id); container.replaceChildren();
  if (!rows.length) {container.append(node('p', 'data-unavailable', 'Sem observações setoriais neste período. Consulte a cobertura da base em Fontes.')); return;}
  const total = rows.reduce((sum, row) => sum + row.valor_fob_usd, 0);
  const maximum = Math.max(...rows.map(row => row.valor_fob_usd));
  rows.slice(0, limit).forEach(row => {
    const item = node('div', 'sector-bar'); const heading = node('div', 'sector-bar-head');
    const label = node('span', '', row.setor); label.title = row.setor;
    heading.append(label, node('strong', '', total ? `${fmt(row.valor_fob_usd / total * 100)}%` : '—'));
    const track = node('div', 'sector-bar-track'); const fill = node('span'); fill.style.width = `${maximum ? row.valor_fob_usd / maximum * 100 : 0}%`; track.append(fill); item.append(heading, track); container.append(item);
  });
}
function renderOverview() {
  lineChart('grafico-overview', app.viracopos, cargoSeries, 'Não há carga aérea disponível para a janela selecionada.', {zero: true});
  const trade = last(subset(seriesFromComex())); set('trade-month', trade ? `Referência: ${showMonth(trade.mes)}` : 'Sem observações no período');
  const composition = byId('trade-composition'); composition.replaceChildren();
  const maximum = trade ? Math.max(trade.importacao ?? 0, trade.exportacao ?? 0) : 0;
  for (const [key, label] of [['importacao', 'Importação'], ['exportacao', 'Exportação']]) {
    const row = node('div', 'trade-row'); const heading = node('div', 'trade-row-head');
    heading.append(node('span', '', label), node('strong', '', fmt(trade?.[key])));
    const track = node('div', 'trade-track'); const fill = node('span'); fill.style.width = `${maximum && Number.isFinite(trade[key]) ? trade[key] / maximum * 100 : 0}%`; track.append(fill); row.append(heading, track); composition.append(row);
  }
  const macros = byId('macro-overview'); macros.replaceChildren();
  Object.entries(macroLabels).forEach(([field, meta]) => {
    const point = last(subset(app.macro).filter(row => Number.isFinite(row[field])));
    const item = node('div', 'macro-item'); item.append(node('span', '', meta[0]), node('strong', '', point ? `${field === 'dolar_venda_medio_brl' ? 'R$ ' : ''}${fmt(point[field], 2)}${field === 'dolar_venda_medio_brl' ? '' : '%'}` : '—'), node('small', '', `${meta[2]} · ${point ? showMonth(point.mes) : 'indisponível'}`)); macros.append(item);
  });
  const sectors = sectorRows('importacao'); set('sector-overview-month', sectors.length ? showMonth(sectors[0].mes) : 'Sem observações no período'); sectorBars('sector-overview', sectors);
}
function renderCharts() {
  lineChart('grafico-carga', app.viracopos, cargoSeries, 'Consulte o intervalo disponível em Fontes ou amplie a janela.', {zero: true});
  lineChart('grafico-comex', seriesFromComex(), [{key: 'importacao', label: 'Importação', color: blue, unit: 'US$ mi'}, {key: 'exportacao', label: 'Exportação', color: gold, unit: 'US$ mi'}], 'O recorte aduaneiro não possui observações no período.', {zero: true});
  lineChart('grafico-brasil', app.brasil, [{key: 'exportacoes_usd_bi', label: 'Exportação', color: blue, unit: 'US$ bi'}, {key: 'importacoes_usd_bi', label: 'Importação', color: gold, unit: 'US$ bi'}], 'Sem dados nacionais nesta janela.', {zero: true});
  const meta = macroLabels[macroMetrica]; set('macro-title', meta[0]); set('macro-desc', meta[1]);
  const point = last(subset(app.macro).filter(row => Number.isFinite(row[macroMetrica])));
  set('macro-valor', point ? `${macroMetrica === 'dolar_venda_medio_brl' ? 'R$ ' : ''}${fmt(point[macroMetrica], 2)}${macroMetrica === 'dolar_venda_medio_brl' ? '' : '%'}` : '—');
  set('macro-meta', point ? `${showMonth(point.mes)} · ${meta[2]}` : 'Sem observações neste período');
  lineChart('grafico-macro', app.macro, [{key: macroMetrica, label: meta[0], color: blue, unit: meta[2]}], 'Sem observações deste indicador na janela selecionada.', {decimals: 2});
  const cargo = last(subset(app.viracopos)); const summary = byId('cargo-summary'); summary.replaceChildren();
  for (const [label, value] of [['Carga internacional', cargo?.carga_internacional_t], ['Carga doméstica', cargo?.carga_domestica_t], ['Courier internacional', cargo?.courier_internacional_t]]) {
    const item = node('div'); item.append(node('span', '', label), node('strong', '', `${fmt(value, 0)} t`), node('small', '', cargo ? showMonth(cargo.mes) : 'Indisponível')); summary.append(item);
  }
  set('cargo-scope', `${app.metadados.viracopos.abrangencia}. ${app.metadados.viracopos.limitacoes}`);
}
function renderTable() {
  const rows = sectorRows(fluxo); const body = byId('tabela-setores'); body.replaceChildren(); sectorBars('sector-detail-bars', rows, 8);
  const total = rows.reduce((sum, row) => sum + row.valor_fob_usd, 0);
  set('sector-table-description', rows.length ? `${fluxo === 'importacao' ? 'Importações' : 'Exportações'} · ${showMonth(rows[0].mes)} · ${rows.length} agrupamentos` : 'Sem observações deste fluxo no período selecionado');
  if (!rows.length) {const row = body.insertRow(); const cell = row.insertCell(); cell.colSpan = 5; cell.className = 'no-data'; cell.textContent = 'Nenhuma observação disponível neste período.'; return;}
  rows.forEach(item => {
    const row = body.insertRow();
    [item.setor, showMonth(item.mes), `US$ ${fmt(item.valor_fob_usd / 1e6, 2)} mi`, `${fmt(item.kg_liquido / 1000, 1)} t`, total ? `${fmt(item.valor_fob_usd / total * 100)}%` : '—'].forEach((text, index) => {const cell = row.insertCell(); cell.textContent = text; if (index >= 2) cell.className = 'numeric';});
  });
}
function renderSources() {
  const labels = {viracopos: ['Carga aérea · Viracopos', 'Carga aérea'], comex: ['Comércio exterior · Viracopos', 'Comex / URF'], brasil: ['Comércio exterior · Brasil', 'Brasil / MDIC'], macro: ['Economia · Brasil', 'BCB / SGS']};
  const sourcePanel = byId('source-status'); const coverage = byId('coverage-list'); sourcePanel.replaceChildren(); coverage.replaceChildren();
  Object.entries(labels).forEach(([key, label]) => {
    const meta = app.metadados[key]; const available = app[key].length > 0;
    const row = node('div', 'coverage-row'); row.append(node('span', `coverage-dot${available ? '' : ' pending'}`));
    const copy = node('div'); copy.append(node('strong', '', label[1]), node('small', '', available ? `${showMonth(meta.referencia_inicial)} — ${showMonth(meta.referencia_final)}` : 'Sem observações')); row.append(copy); coverage.append(row);
    const card = node('article', 'panel source-card'); card.append(node('span', `source-state${available ? '' : ' pending'}`, available ? 'BASE DISPONÍVEL' : 'INTEGRAÇÃO PENDENTE'), node('h2', '', label[0]), node('p', '', meta.abrangencia));
    const info = node('div', 'source-meta'); info.append(node('span', '', `Referência: ${available ? `${showMonth(meta.referencia_inicial)} a ${showMonth(meta.referencia_final)}` : '—'}`), node('span', '', `Coleta/conferência: ${dateText(meta.coletado_em_utc || meta.verificado_em_utc)}`));
    card.append(info, node('p', '', meta.tratamento), node('p', '', meta.limitacoes));
    if (app.coleta_fontes?.[key]?.status?.startsWith('falha')) card.append(node('p', 'notice', 'A última consulta à fonte falhou. O histórico validado foi preservado; a competência exibida continua sendo a referência disponível.'));
    const link = node('a', 'text-link', 'Abrir fonte oficial ↗'); link.href = meta.fonte_original.includes('{') ? 'https://dadosabertos.bcb.gov.br/' : meta.fonte_original; link.target = '_blank'; link.rel = 'noopener'; card.append(link); sourcePanel.append(card);
  });
  const failure = Object.values(app.coleta_bcb || {}).some(value => value && typeof value === 'object' && value.status?.startsWith('falha'));
  if (failure) sourcePanel.append(node('p', 'notice', 'A última consulta econômica teve falhas parciais. Os últimos dados validados foram preservados.'));
  const availableCount = ['viracopos', 'comex', 'brasil', 'macro'].filter(key => app[key].length).length;
  set('status-chip', `${availableCount} de 4 bases disponíveis`); set('last-build', `Consolidação: ${dateText(app.gerado_em_utc)}`);
}
const viewLabels = {
  'visao-geral': ['Visão geral', 'Carga aérea, comércio exterior e economia no mesmo horizonte.'],
  'carga-aerea': ['Carga aérea', 'Movimentação de Viracopos segundo os relatórios oficiais da concessionária.'],
  comex: ['Comércio exterior', 'O recorte aduaneiro de Viracopos e o contexto nacional.'],
  macroeconomia: ['Economia', 'Juros, câmbio e inflação para acompanhar o ambiente econômico.'],
  setores: ['Análise setorial', 'Composição das importações e exportações de Viracopos.'],
  metodo: ['Fontes e metodologia', 'Cobertura, competências e definições para uma leitura consistente.']
};
const mobileToggle = document.querySelector('.mobile-toggle');
function closeMenu() {document.querySelector('.main-nav').classList.remove('open'); mobileToggle.setAttribute('aria-expanded', 'false'); mobileToggle.setAttribute('aria-label', 'Abrir menu');}
function showView(id, navigate = true) {
  if (!viewLabels[id]) id = 'visao-geral'; currentView = id;
  document.querySelectorAll('.view').forEach(view => {view.hidden = view.id !== id; view.classList.toggle('active', view.id === id);});
  document.querySelectorAll('.nav-link').forEach(link => {const active = link.getAttribute('href') === '#' + id; link.classList.toggle('active', active); if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');});
  set('page-title', viewLabels[id][0]); set('page-description', viewLabels[id][1]); closeMenu();
  if (navigate) {history.replaceState(null, '', '#' + id); window.scrollTo({top: 0, behavior: 'instant'}); set('data-status', `Área atual: ${viewLabels[id][0]}`);}
}
function renderAll() {
  renderKPIs(); renderOverview(); renderCharts(); renderTable();
  const allMonths = [...new Set([...app.viracopos, ...app.comex, ...app.brasil, ...app.macro].map(row => row.mes))].sort();
  const startIndex = janela === Infinity ? monthIndex(allMonths[0] || referenceMonth()) : monthIndex(referenceMonth()) - janela + 1;
  const start = `${Math.floor(startIndex / 12)}-${String(startIndex % 12 + 1).padStart(2, '0')}`;
  set('period-summary', `${showMonth(start)} — ${showMonth(referenceMonth())}`);
}
const datasets = [app.viracopos, app.comex, app.brasil, app.macro].filter(rows => rows.length);
const availableMonths = [...new Set(datasets.flatMap(rows => rows.map(row => row.mes)))].sort();
availableMonths.forEach(month => {const option = node('option', '', showMonth(month)); option.value = month; byId('competencia').append(option);});
if (availableMonths.length) byId('competencia').value = defaultReferenceMonth(app);
else {const option = node('option', '', 'Sem competências'); option.value = new Date().toISOString().slice(0, 7); byId('competencia').append(option); byId('competencia').disabled = true;}
byId('competencia').addEventListener('change', () => {renderAll(); set('data-status', `Consulta atualizada até ${showMonth(referenceMonth())}`);});
byId('janela').addEventListener('change', event => {janela = event.target.value === 'all' ? Infinity : Number(event.target.value); renderAll(); set('data-status', 'Histórico atualizado: ' + event.target.selectedOptions[0].textContent);});
byId('fluxo').addEventListener('change', event => {fluxo = event.target.value; renderTable();});
document.querySelectorAll('[data-metric]').forEach(button => button.addEventListener('click', () => {macroMetrica = button.dataset.metric; document.querySelectorAll('[data-metric]').forEach(item => {item.classList.toggle('active', item === button); item.setAttribute('aria-pressed', String(item === button));}); renderCharts();}));
document.addEventListener('click', event => {const link = event.target.closest('a[href^="#"]'); if (!link) return; const id = link.getAttribute('href').slice(1); if (viewLabels[id]) {event.preventDefault(); showView(id);}});
window.addEventListener('hashchange', () => showView(location.hash.slice(1)));
mobileToggle.addEventListener('click', () => {const open = mobileToggle.getAttribute('aria-expanded') !== 'true'; document.querySelector('.main-nav').classList.toggle('open', open); mobileToggle.setAttribute('aria-expanded', String(open)); mobileToggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');});
document.addEventListener('keydown', event => {if (event.key === 'Escape' && mobileToggle.getAttribute('aria-expanded') === 'true') {closeMenu(); mobileToggle.focus();}});
renderAll(); renderSources(); renderComparativoRimaRma(); showView(location.hash.slice(1), false);


function renderComparativoRimaRma() {
  const dataNode = byId('dados-comparativo-rima-rma');
  const result = byId('grafico-comparacao-fontes');
  const profileTarget = byId('perfil-voos-anac');
  if (!dataNode || !result || !profileTarget) return;
  let data;
  try { data = JSON.parse(dataNode.textContent); }
  catch {result.textContent = 'Comparação indisponível: dados inconsistentes.'; return;}
  const rows = Array.isArray(data.recortes) ? data.recortes : [];
  const profiles = Array.isArray(data.perfil_voos) ? data.perfil_voos : [];
  const monthControl = byId('comparativo-mes');
  const months = [...new Set(rows.map(row => row.mes))].sort();
  monthControl.replaceChildren(...months.map(month => {
    const option = node('option', '', showMonth(month)); option.value = month; return option;
  }));
  if (!months.length) {
    result.textContent = 'Ainda não existem competências disponíveis simultaneamente nas duas fontes.';
    profileTarget.textContent = 'Sem movimentos validados para esta comparação.';
    return;
  }
  monthControl.value = months[months.length - 1];
  const render = () => {
    const month = monthControl.value;
    const nature = byId('comparativo-natureza').value;
    const metric = byId('comparativo-indicador').value;
    const source = byId('comparativo-fonte').value;
    const row = rows.find(item => item.mes === month && item.natureza === nature);
    result.replaceChildren();
    set('comparativo-aviso', 'Prévia metodológica · RIMA conferido por SHA-256; RMA ' + showMonth(month) + ' transcrito de PDF ainda não certificado por hash. Sem ajuste de diferenças.');
    if (!row) {
      result.append(node('p', 'chart-empty', 'Não há duas fontes disponíveis para esta combinação.')); set('comparativo-diferenca',''); return;
    }
    byId('comparativo-origem-rma').href = row.rma_url_pdf;
    const field = metric === 'carga' ? 'carga_t' : 'movimentos';
    const unit = metric === 'carga' ? 't' : 'movimentos';
    const a = row['rima_' + field], b = row['rma_' + field];
    const max = Math.max(a, b, 1);
    for (const [code,label,value,css] of [
      ['rima','ANAC / RIMA',a,'blue'], ['rma','Concessionária / RMA',b,'gold']
    ]) {
      if (source !== 'ambas' && source !== code) continue;
      if (!Number.isFinite(value)) continue;
      const item = node('div','compare-bar-item');
      const title = node('div','compare-bar-top');
      title.append(node('strong','',label),node('span','',fmt(value,metric === 'carga' ? (code === 'rima' ? 3 : 0) : 0) + ' ' + unit));
      const track = node('div','compare-bar-track');
      const bar = node('div','compare-bar-fill ' + css);
      bar.style.width = (value / max * 100).toFixed(2) + '%';
      track.append(bar); item.append(title,track); result.append(item);
    }
    if (source === 'ambas' && Number.isFinite(a) && Number.isFinite(b)) {
      const delta = a - b, percent = b !== 0 ? ' (' + fmt(delta / b * 100, 2) + '% do RMA)' : '';
      set('comparativo-diferenca', 'Diferença ANAC − RMA: ' + (delta > 0 ? '+' : '') +
          fmt(delta, metric === 'carga' ? 3 : 0) + ' ' + unit + percent);
    } else set('comparativo-diferenca','Fonte selecionada isoladamente; escolha As duas fontes para ver a diferença.');
  };
  const renderProfile = () => {
    const month = monthControl.value, nature = byId('perfil-natureza').value;
    const selected = profiles.find(item => item.mes === month);
    const vals = selected?.por_natureza?.[nature];
    profileTarget.replaceChildren();
    if (!vals) {profileTarget.append(node('p','chart-empty','Perfil de movimentos ainda indisponível para este mês.'));return;}
    const total = vals.movimentos;
    for (const [key,label,css] of [
      ['com_carga','Com carga registrada (QT_CARGA > 0)','blue'],
      ['sem_carga','Sem carga registrada (QT_CARGA = 0)','gold']
    ]) {
      const amount = vals[key] ?? 0;
      const item = node('div','compare-bar-item');
      const top = node('div','compare-bar-top');
      top.append(node('strong','',label),node('span','',fmt(amount,0)+' de '+fmt(total,0)+' movimentos'));
      const track = node('div','compare-bar-track');
      const bar = node('div','compare-bar-fill '+css);
      bar.style.width = (total ? amount/total*100 : 0).toFixed(2)+'%';
      track.append(bar);item.append(top,track);profileTarget.append(item);
    }
    const both = vals.com_carga__com_passageiros ?? 0;
    const passengersNoCargo = vals.sem_carga__com_passageiros ?? 0;
    profileTarget.append(node('p','compare-profile-note',
      fmt(both,0)+' movimentos com passageiros e carga; '+
      fmt(passengersNoCargo,0)+' com passageiros e sem carga registrada. '+
      'A classificação é por movimento, não por remessa aduaneira.'));
  };
  ['comparativo-mes','comparativo-natureza','comparativo-indicador','comparativo-fonte'].forEach(id => byId(id).addEventListener('change',() => {render();if(id==='comparativo-mes')renderProfile();}));
  byId('perfil-natureza').addEventListener('change',renderProfile);
  render();renderProfile();
}


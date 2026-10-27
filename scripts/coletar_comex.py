"""MDIC oficial: URF Viracopos 0817700, via aérea 04, capítulos SH2.

API indisponível: agrega CSV anual oficial em streaming com curl e TLS normal.
Microdados anuais não são armazenados. Cache agregado fica em data/staging.
"""
import argparse
import csv
import hashlib
import io
import json
import shutil
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/staging/comex"
BASE = "https://balanca.mdic.gov.br/balanca/bd"
CURL = shutil.which("curl.exe") or shutil.which("curl")
URF = 817700
VIA = 4


def small_csv(name):
    url = f"{BASE}/tabelas/{name}.csv"
    raw = subprocess.check_output([CURL, "-L", "--fail", "--silent", "--show-error", "--connect-timeout", "20", "--max-time", "90", url])
    (OUT / f"{name}.csv").write_bytes(raw)
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("latin-1")
    return list(csv.DictReader(io.StringIO(content), delimiter=";")), {"url":url,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}


def aggregate_lines(lines, year, code):
    """Agrega bytes CSV sem rede; hash corresponde a todo o arquivo original."""
    lines = iter(lines)
    header = next(lines)
    digest = hashlib.sha256(header)
    size = len(header)
    columns = [value.strip().strip('"') for value in header.decode("utf-8-sig").split(";")]
    required = {"CO_ANO", "CO_MES", "CO_NCM", "CO_VIA", "CO_URF", "KG_LIQUIDO", "VL_FOB"}
    if not required <= set(columns):
        raise ValueError(f"Cabeçalho inesperado: {columns}")
    indices = {key:columns.index(key) for key in required}
    sectors, national = defaultdict(lambda:[0,0]), defaultdict(int)
    count = selected = 0
    for raw in lines:
        digest.update(raw)
        size += len(raw)
        if not raw.strip():
            continue
        row = [value.strip().strip(b'"') for value in raw.split(b";")]
        row_year, month = int(row[indices['CO_ANO']]), int(row[indices['CO_MES']])
        if row_year != year or not 1 <= month <= 12:
            raise ValueError("Competência inválida")
        reference = f"{year}-{month:02d}"
        fob, kg = int(row[indices['VL_FOB']]), int(row[indices['KG_LIQUIDO']])
        if fob < 0 or kg < 0:
            raise ValueError("FOB/peso líquido negativo")
        national[reference] += fob
        count += 1
        if int(row[indices['CO_URF']]) == URF and int(row[indices['CO_VIA']]) == VIA:
            chapter = row[indices['CO_NCM']].decode().zfill(8)[:2]
            cell = sectors[(reference, chapter)]
            cell[0] += fob
            cell[1] += kg
            selected += 1
        if count % 500000 == 0:
            print(f"{code} {year}: {count:,} linhas; {selected:,} no recorte", flush=True)
    if not count or not selected:
        raise ValueError(f"Nenhuma observação no recorte {year}/{code}")
    receipt = {"url":f"{BASE}/comexstat-bd/ncm/{code}_{year}.csv","sha256":digest.hexdigest(),"bytes":size,"linhas_origem":count,"linhas_recorte":selected,"coletado_em_utc":datetime.now(timezone.utc).isoformat(),"urf":URF,"via":VIA,"fluxo":"exportacao" if code == 'EXP' else 'importacao',"referencia_inicial":min(national),"referencia_final":max(national)}
    return {"receipt":receipt,"sectors":[{"mes":mes,"sh2":chapter,"valor_fob_usd":value[0],"kg_liquido":value[1]} for (mes,chapter),value in sorted(sectors.items())],"brasil":dict(national)}


def aggregate_file(year, code):
    url = f"{BASE}/comexstat-bd/ncm/{code}_{year}.csv"
    process = subprocess.Popen([CURL, "-L", "--fail", "--silent", "--show-error", "--connect-timeout", "20", "--max-time", "1200", url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        result = aggregate_lines(process.stdout, year, code)
        stderr = process.stderr.read().decode(errors="replace")
        if process.wait() != 0:
            raise OSError(stderr)
    except BaseException:
        process.kill()
        process.wait()
        raise
    (OUT / f"{code}_{year}_agregado.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"CONCLUÍDO {code} {year}: {result['receipt']['linhas_origem']:,} linhas",flush=True)
    return result


def merge_month_flows(existing, fresh, covered=None):
    """Uma revisão substitui o mês/fluxo inteiro, inclusive setores removidos."""
    covered = set(covered) if covered is not None else {(row['mes'],row['fluxo']) for row in fresh}
    retained = [row for row in existing if (row['mes'],row['fluxo']) not in covered]
    rows = retained + fresh
    keys = [(row['mes'],row['fluxo'],row['setor']) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Chave mensal/fluxo/setor duplicada")
    return sorted(rows,key=lambda row:(row['mes'],row['fluxo'],row['setor']))


def references():
    OUT.mkdir(parents=True,exist_ok=True)
    via, via_receipt = small_csv('VIA')
    urf, urf_receipt = small_csv('URF')
    sh, sh_receipt = small_csv('NCM_SH')
    via_row = next(row for row in via if int(row.get('CO_VIA','0')) == VIA)
    urf_row = next(row for row in urf if int(row.get('CO_URF','0')) == URF)
    if 'AEREA' not in via_row['NO_VIA'].upper() or 'VIRACOPOS' not in urf_row['NO_URF'].upper():
        raise ValueError('Descrição de URF/via diverge do recorte esperado')
    labels = {str(row['CO_SH2']).zfill(2):row['NO_SH2_POR'] for row in sh}
    return labels, {'fontes_tabelas':[via_receipt,urf_receipt,sh_receipt], 'recorte':{'urf':urf_row,'via':via_row,'classificacao':'capítulo SH2, prefixo NCM com descrição oficial NCM_SH'}}


def datasets_to_rows(datasets, labels):
    rows, covered = [], set()
    for dataset in datasets:
        flow = dataset['receipt']['fluxo']
        covered.update((month,flow) for month in dataset['brasil'])
        for row in dataset['sectors']:
            rows.append({'mes':row['mes'],'fluxo':flow,'setor':f"SH{row['sh2']} · {labels[row['sh2']]}",'valor_fob_usd':row['valor_fob_usd'],'kg_liquido':row['kg_liquido']})
    return rows, covered


def metadata_for(rows, datasets, reference_metadata, now):
    return {'fonte_original':'https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta','coletado_em_utc':now.isoformat(),'unidades':{'valor_fob_usd':'US$ FOB','kg_liquido':'kg líquidos'},'periodicidade':'mensal × fluxo × capítulo SH2','abrangencia':'URF 0817700 Aeroporto Internacional de Viracopos; via 04 aérea; importação/exportação','tratamento':'Soma exata de VL_FOB e KG_LIQUIDO dos CSVs NCM/MDIC por CO_ANO, CO_MES, fluxo e prefixo SH2. Filtros CO_URF=817700 e CO_VIA=4 validados nas tabelas oficiais. Reprocessa ano corrente; revisão substitui todo o grupo mês×fluxo e preserva histórico anterior.','limitacoes':'Recorte aduaneiro de URF de embarque/desembarque declarado e via aérea; não equivale à carga física ANAC/SBKP. Peso líquido não inclui embalagem nem peso volumétrico. Classificações NCM/SH e dados podem sofrer revisão.','status':'validado','recorte_validado':True,'referencia_inicial':rows[0]['mes'] if rows else None,'referencia_final':rows[-1]['mes'] if rows else None,'arquivos':[dataset['receipt'] for dataset in datasets],**reference_metadata}


def brasil_rows_from_datasets(datasets):
    totals = defaultdict(dict)
    for dataset in datasets:
        for month,value in dataset['brasil'].items():
            totals[month][dataset['receipt']['fluxo']] = value
    return [{'mes':month,'exportacoes_usd_bi':values['exportacao']/1e9,'importacoes_usd_bi':values['importacao']/1e9}
            for month,values in sorted(totals.items()) if set(values)=={'exportacao','importacao'}]


def collect_comex(existing_rows=None, now=None):
    """Atualiza último ano encerrado/disponível sem reutilizar cache do corrente.

    Na primeira carga, consulta ano anterior e atual. Com histórico existente,
    reconsulta somente o ano do último mês encerrado; fontes falhas levantam
    exceção para que o chamador preserve o último snapshot validado.
    """
    now = now or datetime.now(timezone.utc)
    existing_rows = existing_rows or []
    end = now.date().replace(day=1) - timedelta(days=1)
    years = [end.year] if existing_rows else [end.year-1,end.year]
    labels, ref = references()
    datasets = []
    for year in years:
        for code in ('EXP','IMP'):
            cache = OUT / f'{code}_{year}_agregado.json'
            # Current/latest year must always go online, including a revised month.
            dataset = json.loads(cache.read_text(encoding='utf-8')) if year < end.year and cache.exists() else aggregate_file(year,code)
            datasets.append(dataset)
    fresh, covered = datasets_to_rows(datasets,labels)
    cutoff = end.strftime('%Y-%m')
    fresh = [row for row in fresh if row['mes'] <= cutoff]
    covered = {group for group in covered if group[0] <= cutoff}
    rows = merge_month_flows(existing_rows,fresh,covered)
    metadata = metadata_for(rows,datasets,ref,now)
    metadata['_brasil_rows'] = [row for row in brasil_rows_from_datasets(datasets) if row['mes'] <= cutoff]
    return rows, metadata


def main(years, refresh=True):
    labels, ref = references()
    datasets=[]
    for year in years:
        for code in ('EXP','IMP'):
            cached=OUT/f'{code}_{year}_agregado.json'
            datasets.append(json.loads(cached.read_text(encoding='utf-8')) if cached.exists() and not refresh else aggregate_file(year,code))
    rows,_ = datasets_to_rows(datasets,labels)
    rows = merge_month_flows([],rows)
    with (OUT/'comex_viracopos.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['mes','fluxo','setor','valor_fob_usd','kg_liquido'],lineterminator='\n');writer.writeheader();writer.writerows(rows)
    totals=defaultdict(dict)
    for dataset in datasets:
        for month,value in dataset['brasil'].items():totals[month][dataset['receipt']['fluxo']]=value
    with (OUT/'brasil.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n');writer.writerow(['mes','exportacoes_usd_bi','importacoes_usd_bi'])
        for month,values in sorted(totals.items()):
            if set(values)=={'exportacao','importacao'}:writer.writerow([month,values['exportacao']/1e9,values['importacao']/1e9])
    metadata=metadata_for(rows,datasets,ref,datetime.now(timezone.utc))
    (OUT/'receipt.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"CSV FINAL: {len(rows)} linhas, {len(totals)} competências",flush=True)
    return rows, metadata


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--years',type=int,nargs='+',default=[2026]);parser.add_argument('--reuse-cache',action='store_true');args=parser.parse_args();main(args.years,refresh=not args.reuse_cache)

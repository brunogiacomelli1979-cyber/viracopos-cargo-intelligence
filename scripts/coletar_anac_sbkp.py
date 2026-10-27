"""ANAC Básica: etapas físicas de voos com origem/destino SBKP, 2020–2024.

Fonte: microdados mensais públicos ANAC. Não é a mesma população do RMA
da concessionária. Este coletor NÃO altera data/viracopos.csv nem o painel.

Executar inicialmente com --start 2024-01 --end 2024-01 para validar
o contrato contra um arquivo real, depois 2020-01 a 2024-12.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import re
import unicodedata
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fontes_http import get_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ("https://www.gov.br/anac/pt-br/assuntos/regulados/empresas-aereas/"
        "Instrucoes-para-a-elaboracao-e-apresentacao-das-demonstracoes-contabeis/"
        "envio-de-informacoes/basica")
FIELDS = ("kg_carga_paga", "kg_carga_gratis", "kg_correio")
REQUIRED = set(FIELDS) | {"nr_ano_referencia", "nr_mes_referencia",
                           "sg_icao_origem", "sg_icao_destino",
                           "ds_natureza_etapa"}
OUTPUT = ["mes", "natureza", "sentido", "carga_paga_t", "carga_gratis_t",
          "correio_t", "carga_sem_correio_t", "etapas"]
MAX_ZIP_BYTES = 100_000_000
MAX_EXPANDED_BYTES = 450_000_000


def norm(value):
    return unicodedata.normalize("NFKD", str(value).strip()).encode(
        "ascii", "ignore").decode().upper()


def weight(value, field):
    value = value.strip()
    if not value:
        return None
    if not re.fullmatch(r"\d+(?:[.,]\d+)?", value):
        raise ValueError(f"{field}: peso inválido: {value!r}")
    try:
        parsed = Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"{field}: peso inválido") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(f"{field}: peso inválido")
    return parsed


def url_for(month):
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", month):
        raise ValueError("Competência inválida")
    year = month[:4]
    return f"{BASE}/{year}/basica{month}.zip"


def aggregate_csv(csv_bytes, month):
    """Fixture-friendly pure transformation; never assumes a missing weight is zero."""
    rows = csv.DictReader(io.StringIO(csv_bytes.decode("latin-1")), delimiter=";")
    if not REQUIRED <= set(rows.fieldnames or []):
        raise ValueError(f"Esquema ANAC divergente: {sorted(REQUIRED - set(rows.fieldnames or []))}")
    totals = defaultdict(lambda: [Decimal(0), Decimal(0), Decimal(0), 0])
    missing = defaultdict(int)
    seen = set()
    selected = 0
    for item in rows:
        origin = norm(item["sg_icao_origem"])
        dest = norm(item["sg_icao_destino"])
        if origin != "SBKP" and dest != "SBKP":
            continue
        if origin == "SBKP" and dest == "SBKP":
            raise ValueError("ANAC: etapa local SBKP→SBKP requer revisão")
        if (item["nr_ano_referencia"].strip() != month[:4]
                or int(item["nr_mes_referencia"]) != int(month[5:])):
            raise ValueError(f"ANAC: competência da linha difere do arquivo {month}")
        nature = norm(item["ds_natureza_etapa"])
        # A terminologia oficial ANAC é "Doméstico" / "Internacional".
        # Também aceitar "Doméstica" em fixtures/documentos legados, mantendo
        # a classificação harmonizada no resultado.
        if nature in {"DOMESTICO", "DOMESTICA"}:
            nature = "domestica"
        elif nature == "INTERNACIONAL":
            nature = "internacional"
        else:
            raise ValueError(f"Natureza ANAC desconhecida: {nature}")
        direction = "embarque" if origin == "SBKP" else "desembarque"
        key = (month, nature, direction)
        selected += 1
        weights = [weight(item[column], column) for column in FIELDS]
        if any(x is None for x in weights):
            missing[key] += 1
        else:
            for i, value in enumerate(weights):
                totals[key][i] += value
            totals[key][3] += 1
    if not selected:
        raise ValueError(f"ANAC: SBKP sem etapas no período {month}")
    if missing:
        raise ValueError(f"ANAC: pesos não informados em {sum(missing.values())} etapas SBKP do mês {month}; investigar antes de consolidar")
    output = []
    for (mes, nature, direction), (paid, free, mail, steps) in sorted(totals.items()):
        output.append({"mes": mes, "natureza": nature, "sentido": direction,
                       "carga_paga_t": float(paid/1000),
                       "carga_gratis_t": float(free/1000),
                       "correio_t": float(mail/1000),
                       "carga_sem_correio_t": float((paid+free)/1000),
                       "etapas": steps})
    return output, {"etapas_sbkp": selected, "grupos": len(output),
                    "sem_carga_inferida": False}


def collect_month(month, fetcher=get_bytes):
    url = url_for(month)
    raw = fetcher(url, timeout=120)
    if len(raw) > MAX_ZIP_BYTES or len(raw) < 100 or raw[:2] != b"PK":
        raise ValueError("Resposta da ANAC não é ZIP plausível")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        entries = [info for info in zf.infolist() if not info.is_dir()]
        # O pacote oficial pode conter arquivo texto delimitado em vez de .csv.
        # Aceitar somente um arquivo de dados, sem inferir formato do conteúdo.
        parts = [info for info in entries
                 if info.filename.lower().endswith((".csv", ".txt"))]
        if len(parts) != 1:
            names = [info.filename for info in entries[:12]]
            raise ValueError(
                f"ZIP ANAC: esperado um CSV/TXT, encontrados {len(parts)}; "
                f"entradas do ZIP: {names}")
        info = parts[0]
        if info.file_size > MAX_EXPANDED_BYTES:
            raise ValueError("Arquivo ANAC expandido excede limite")
        with zf.open(info) as file:
            content = file.read(MAX_EXPANDED_BYTES + 1)
        if len(content) > MAX_EXPANDED_BYTES:
            raise ValueError("CSV ANAC maior que o limite permitido")
    rows, quality = aggregate_csv(content, month)
    receipt = {"url": url, "sha256": hashlib.sha256(raw).hexdigest(),
               "bytes": len(raw), "csv_sha256": hashlib.sha256(content).hexdigest(),
               "csv_bytes": len(content), "competencia": month,
               "coletado_em_utc": datetime.now(timezone.utc).isoformat(),
               **quality}
    return rows, receipt


def months_between(first, final):
    start, end = (int(m[:4])*12 + int(m[5:])-1 for m in (first, final))
    if end < start:
        raise ValueError("Fim anterior ao início")
    return [f"{i//12:04d}-{i%12+1:02d}" for i in range(start, end+1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2020-01")
    parser.add_argument("--end", default="2024-12")
    parser.add_argument("--output-dir", type=Path, default=ROOT/"data/staging/anac")
    parser.add_argument("--strict-complete", action="store_true",
                        help="Exigir todos os meses no intervalo; não publicar base parcial")
    args = parser.parse_args()
    months = months_between(args.start, args.end)
    if not months or any(not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", m) for m in months):
        raise ValueError("Intervalo inválido")
    data, receipts, failures = [], [], []
    for month in months:
        try:
            observations, receipt = collect_month(month)
            data.extend(observations)
            receipts.append(receipt)
            print("OK", month, receipt["etapas_sbkp"], flush=True)
        except Exception as exc:
            failures.append({"competencia": month, "erro": str(exc)})
            print("FALHA", month, str(exc), flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if data:
        output = args.output_dir/"anac_sbkp_carga_mensal.csv"
        with output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=OUTPUT)
            writer.writeheader()
            writer.writerows(data)
    metadata = {"origem": "ANAC — Dados Estatísticos do Transporte Aéreo, Etapa Básica",
                "fonte_metodologica": "https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/dados-estatisticos-do-transporte-aereo/48-dados-estatisticos-do-transporte-aereo",
                "aeroporto": "SBKP", "unidade": "toneladas transportadas por etapa",
                "definicao": "soma carga paga + carga grátis, correio em campo separado",
                "sentido": "embarque na origem SBKP, desembarque no destino SBKP",
                "nao_comparavel_diretamente_com": ["RMA da concessionária", "FOB MDIC", "kg líquido MDIC"],
                "recibos": receipts, "falhas": failures, "meses_esperados": len(months),
                "meses_validados": len(receipts),
                "status": "validado" if len(receipts)==len(months) else "incompleto"}
    (args.output_dir/"anac_sbkp_fontes.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    if args.strict_complete and failures:
        raise SystemExit(f"ANAC: {len(failures)} competências pendentes; saída restrita a staging")
    print(json.dumps({"meses_validados": len(receipts), "meses_pendentes": len(failures)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

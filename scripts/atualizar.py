"""Consolidação de SGS, microdados MDIC e relatórios RMA, com histórico e fallback."""
import argparse
import csv
import hashlib
import io
import json
import logging
import os
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.error import HTTPError

from validar_dados import ROOT, SCHEMAS, read_csv, validate_metadata, validate_rows
from coletar_brasil import collect_brazil
from coletar_carga_vcp import collect_rma
from coletar_comex import collect_comex
from fontes_http import get_bytes

SERIES = {"selic_meta_pct_aa": 432, "dolar_venda_medio_brl": 1, "ipca_pct_mes": 433}


def merge_receipts(previous, incoming):
    documents = {item["url"]: item for item in previous}
    documents.update({item["url"]: item for item in incoming})
    return [documents[url] for url in sorted(documents)]


def brazil_raw_metadata(comex_metadata, previous=None):
    previous = previous or {}
    return {
        "fonte_original": comex_metadata["fonte_original"],
        "coletado_em_utc": comex_metadata["coletado_em_utc"],
        "unidades": {"exportacoes_usd_bi": "US$ bilhões FOB", "importacoes_usd_bi": "US$ bilhões FOB"},
        "periodicidade": "mensal", "abrangencia": "Brasil; todas as vias de transporte e URFs",
        "tratamento": "Soma de VL_FOB de todas as linhas dos mesmos arquivos anuais EXP/IMP oficiais MDIC, sem filtro URF, via ou setor; divisão por 1 bilhão. Histórico preservado por mês. A tabela nacional consolidada é fallback se a leitura dos microdados falhar.",
        "limitacoes": "Totais nacionais não representam Viracopos. Dados podem ser revisados. Fallback de publicação consolidada pode ter arredondamento de US$ 0,1 milhão.",
        "status": "validado",
        "arquivos": merge_receipts(previous.get("arquivos", []), comex_metadata.get("arquivos", [])),
    }


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def fetch_series(code, start, end):
    query = urlencode({"formato": "json", "dataInicial": start.strftime("%d/%m/%Y"), "dataFinal": end.strftime("%d/%m/%Y")})
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?{query}"
    # A API pode devolver HTML temporário com HTTP 200 ou falhar intermitentemente.
    # Retentativas não removem observações anteriores nem contornam TLS.
    for attempt in range(3):
        try:
            raw = get_bytes(url, timeout=30)
            data = json.loads(raw)
            if not isinstance(data, list) or not data:
                raise ValueError("SGS sem observações em formato JSON válido")
            if any(not isinstance(row, dict) or not {"data", "valor"} <= row.keys() for row in data):
                raise ValueError("SGS com registros em formato inesperado")
            return data, {"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "registros": len(data)}
        except (OSError, ValueError) as error:
            if isinstance(error, HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                raise  # erros permanentes de consulta não justificam novas tentativas
            if attempt == 2:
                raise
            logging.warning("SGS %s: resposta inválida/tentativa %s de 3: %s", code, attempt + 1, error)
            time.sleep(2 ** attempt)


def aggregate(field, data, start, end):
    months, seen = {}, set()
    for row in data:
        day = datetime.strptime(row["data"], "%d/%m/%Y").date()
        if day in seen or not start <= day <= end:
            raise ValueError("SGS: data duplicada ou fora da consulta")
        seen.add(day)
        value = float(row["valor"].replace(",", "."))
        months.setdefault(day.strftime("%Y-%m"), []).append((day, value))
    result = {}
    for month, observations in months.items():
        observations.sort()
        values = [value for _, value in observations]
        if field == "ipca_pct_mes" and len(values) != 1:
            raise ValueError("IPCA: mais de uma observação mensal")
        result[month] = round(sum(values) / len(values), 6) if field == "dolar_venda_medio_brl" else values[-1]
    validate_rows("macro", [{"mes": month, **{key: value if key == field else None for key in SERIES}} for month, value in result.items()])
    return result


def collect(existing, metadata, now):
    end = date(now.year, now.month, 1) - timedelta(days=1)
    merged = {row["mes"]: dict(row) for row in existing}
    statuses = {}
    for field, code in SERIES.items():
        history = sorted(row["mes"] for row in existing if row[field] is not None)
        start = date(int(history[-1][:4]) - 1, int(history[-1][5:]), 1) if history else date(max(2000, end.year - 4), 1, 1)
        try:
            data, receipt = fetch_series(code, start, end)
            result = aggregate(field, data, start, end)
            # Never erase historical cells absent from a delayed response.
            for month, value in result.items():
                merged.setdefault(month, {"mes": month, **dict.fromkeys(SERIES)})[field] = value
            statuses[field] = {"status": "ok", "competencia": max(result), "coletado_em_utc": now.isoformat(), **receipt}
            logging.info("SGS %s: %s meses, última competência %s", code, len(result), max(result))
        except Exception as error:
            statuses[field] = {"status": "falha; último histórico preservado", "erro": str(error), "tentativa_em_utc": now.isoformat()}
            logging.warning("SGS %s indisponível: %s", code, error)
    rows = validate_rows("macro", list(merged.values()))
    if any(item["status"] == "ok" for item in statuses.values()):
        metadata["macro"]["coletado_em_utc"] = now.isoformat()
        metadata["macro"]["status"] = "validado"
    previous = metadata["macro"].get("coletas_por_serie", {})
    for field, status in statuses.items():
        if status["status"] == "ok":
            previous[field] = status
    metadata["macro"]["coletas_por_serie"] = previous
    return rows, statuses


def build(offline=False, root=ROOT, rma_start_year=2025):
    if not isinstance(rma_start_year, int) or not 2010 <= rma_start_year <= datetime.now(timezone.utc).year:
        raise ValueError('Ano inicial do RMA deve estar entre 2010 e o ano atual')
    now = datetime.now(timezone.utc)
    datasets = {name: read_csv(name, root) for name in SCHEMAS}
    metadata = json.loads((root / "data/fontes.json").read_text(encoding="utf-8"))
    validate_metadata(metadata, datasets)
    previous_path = root / "data/dashboard.json"
    previous_snapshot = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
    statuses = previous_snapshot.get("coleta_bcb", {"status": "não executada"})
    source_statuses = previous_snapshot.get("coleta_fontes", {})
    if not offline:
        datasets["macro"], statuses = collect(datasets["macro"], metadata, now)
        national_updated = False
        try:
            incoming, receipt = collect_comex(existing_rows=datasets["comex"], now=now)
            national = validate_rows("brasil", receipt.pop("_brasil_rows"))
            if not national:
                raise ValueError("MDIC sem competência nacional comum aos dois fluxos")
            incoming = validate_rows("comex", incoming)
            receipt["arquivos"] = merge_receipts(metadata["comex"].get("arquivos", metadata["comex"].get("documentos", [])), receipt.get("arquivos", []))
            months = {row["mes"]: row for row in datasets["brasil"]}
            months.update({row["mes"]: row for row in national})
            datasets["brasil"] = validate_rows("brasil", list(months.values()))
            datasets["comex"] = incoming
            metadata["comex"] = receipt
            metadata["brasil"] = brazil_raw_metadata(receipt, metadata["brasil"])
            for name in ("comex", "brasil"):
                source_statuses[name] = {"status": "ok", "competencia": datasets[name][-1]["mes"], "coletado_em_utc": receipt["coletado_em_utc"]}
            national_updated = True
            logging.info("MDIC Comex: %s linhas e Brasil: %s meses", len(incoming), len(national))
        except Exception as error:
            source_statuses["comex"] = {"status": "falha; histórico preservado", "erro": str(error), "tentativa_em_utc": now.isoformat()}
            logging.warning("MDIC Comex indisponível: %s", error)
        try:
            if not national_updated:
                incoming, receipt = collect_brazil()
                months = {row["mes"]: row for row in datasets["brasil"]}
                months.update({row["mes"]: row for row in incoming})
                datasets["brasil"] = validate_rows("brasil", list(months.values()))
                receipt["arquivos"] = metadata["brasil"].get("arquivos", [])
                metadata["brasil"] = receipt
                source_statuses["brasil"] = {"status": "ok (fallback consolidado)", "competencia": incoming[-1]["mes"], "coletado_em_utc": receipt["coletado_em_utc"]}
                logging.info("MDIC Brasil (fallback): %s meses, última competência %s", len(incoming), incoming[-1]["mes"])
        except Exception as error:
            source_statuses["brasil"] = {"status": "falha; histórico preservado", "erro": str(error), "tentativa_em_utc": now.isoformat()}
            logging.warning("MDIC Brasil indisponível: %s", error)
        try:
            incoming, receipt = collect_rma(existing_rows=datasets["viracopos"], now=now, start_year=rma_start_year)
            datasets["viracopos"] = validate_rows("viracopos", incoming)
            metadata["viracopos"] = receipt
            source_statuses["viracopos"] = {"status": "ok", "competencia": incoming[-1]["mes"], "coletado_em_utc": receipt["coletado_em_utc"]}
            logging.info("RMA Viracopos: %s meses, última competência %s", len(incoming), incoming[-1]["mes"])
        except Exception as error:
            source_statuses["viracopos"] = {"status": "falha; histórico preservado", "erro": str(error), "tentativa_em_utc": now.isoformat()}
            logging.warning("RMA Viracopos indisponível: %s", error)
    validate_metadata(metadata, datasets)
    for name, rows in datasets.items():
        metadata[name]["referencia_inicial"] = rows[0]["mes"] if rows else None
        metadata[name]["referencia_final"] = rows[-1]["mes"] if rows else None
    snapshot = {"versao": "2.0.0", "gerado_em_utc": now.isoformat(), "modo_compilacao": "offline" if offline else "online", "contexto": "Carga física, valor FOB e peso líquido têm coberturas distintas.", "coleta_bcb": statuses, "coleta_fontes": source_statuses, "metadados": metadata, **datasets}
    compact = json.dumps(snapshot, ensure_ascii=False, allow_nan=False, separators=(",", ":")).replace("<", "\\u003c")
    template = (root / "index.template.html").read_text(encoding="utf-8")
    if template.count("{{DASHBOARD_JSON}}") != 1:
        raise ValueError("template precisa de um único marcador de dados")
    html = template.replace("{{DASHBOARD_JSON}}", compact)
    for asset in ("assets/style-blue.css", "assets/app-blue.js"):
        version = hashlib.sha256((root / asset).read_bytes()).hexdigest()[:12]
        html = html.replace(f'"{asset}"', f'"{asset}?v={version}"')
    # Validate everything before replacing outputs. Each individual replacement is atomic.
    if not offline:
        for name, rows in datasets.items():
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=SCHEMAS[name], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            filename = "comex_viracopos" if name == "comex" else name
            atomic_write(root / "data" / f"{filename}.csv", stream.getvalue())
    atomic_write(root / "data/fontes.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    atomic_write(root / "data/dashboard.json", json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    atomic_write(root / "index.html", html)
    logging.info("Snapshot gerado: %s", {name: len(rows) for name, rows in datasets.items()})
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--rma-start-year", type=int, default=2025, help="Ano inicial para busca de RMA; use por exemplo 2021 em backfill explícito")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    build(args.offline, rma_start_year=args.rma_start_year)

"""Contratos dos CSVs e do snapshot; somente biblioteca padrão Python."""
import csv
import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "brasil": ["mes", "exportacoes_usd_bi", "importacoes_usd_bi"],
    "viracopos": ["mes", "carga_internacional_t", "carga_domestica_t", "courier_internacional_t"],
    "comex": ["mes", "fluxo", "setor", "valor_fob_usd", "kg_liquido"],
    "macro": ["mes", "selic_meta_pct_aa", "dolar_venda_medio_brl", "ipca_pct_mes"],
}


def validate_rows(name, rows, today=None):
    today = today or date.today()
    seen = set()
    for row in rows:
        if set(row) != set(SCHEMAS[name]):
            raise ValueError(f"{name}: colunas inválidas")
        month = row["mes"]
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            raise ValueError(f"{name}: competência inválida {month}")
        if month >= today.strftime("%Y-%m"):
            raise ValueError(f"{name}: mês futuro ou ainda aberto {month}")
        key = (month, row.get("fluxo"), row.get("setor"))
        if key in seen:
            raise ValueError(f"{name}: chave duplicada {key}")
        seen.add(key)
        if name == "comex" and (row["fluxo"] not in ("importacao", "exportacao") or not row["setor"].strip()):
            raise ValueError("comex: fluxo/setor inválido")
        numbers = [k for k in SCHEMAS[name] if k not in ("mes", "fluxo", "setor")]
        for field in numbers:
            value = row[field]
            if value is None and name == "macro":
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name}: número inválido em {field}")
            if field != "ipca_pct_mes" and value < 0:
                raise ValueError(f"{name}: valor negativo em {field}")
        if name == "macro" and all(row[k] is None for k in numbers):
            raise ValueError("macro: linha sem observações")
    return sorted(rows, key=lambda r: (r["mes"], r.get("fluxo", ""), r.get("setor", "")))


def read_csv(name, root=ROOT):
    with (root / "data" / f"{name if name != 'comex' else 'comex_viracopos'}.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != SCHEMAS[name]:
            raise ValueError(f"{name}: cabeçalho inesperado {reader.fieldnames}")
        rows = []
        for row in reader:
            for field in SCHEMAS[name]:
                if field not in ("mes", "fluxo", "setor"):
                    row[field] = None if row[field] == "" and name == "macro" else float(row[field])
            rows.append(row)
    return validate_rows(name, rows)


def validate_metadata(metadata, datasets):
    required = {"fonte_original", "coletado_em_utc", "unidades", "periodicidade", "abrangencia", "tratamento", "limitacoes", "status"}
    for name, rows in datasets.items():
        item = metadata[name]
        if not required <= item.keys():
            raise ValueError(f"{name}: metadados incompletos")
        if rows and (not (item["coletado_em_utc"] or item.get("verificado_em_utc")) or item["status"] != "validado"):
            raise ValueError(f"{name}: dados sem proveniência validada")
        if name == "comex" and rows and not item.get("recorte_validado"):
            raise ValueError("comex: recorte aduaneiro não validado")


def validate_project(root=ROOT):
    datasets = {name: read_csv(name, root) for name in SCHEMAS}
    metadata = json.loads((root / "data/fontes.json").read_text(encoding="utf-8"))
    validate_metadata(metadata, datasets)
    snapshot = json.loads((root / "data/dashboard.json").read_text(encoding="utf-8"))
    for name, rows in datasets.items():
        if snapshot[name] != rows:
            raise ValueError(f"{name}: snapshot diverge do CSV")
    if snapshot["metadados"] != metadata:
        raise ValueError("metadados do snapshot divergentes")
    html = (root / "index.html").read_text(encoding="utf-8")
    embedded = re.search(r'<script type="application/json" id="dados-incorporados">(.*?)</script>', html, re.S)
    if not embedded or json.loads(embedded[1]) != snapshot:
        raise ValueError("index.html diverge do snapshot")
    expected_preview = root / "data/comparativo_rima_rma.json"
    match_preview = re.search(r'<script type="application/json" id="dados-comparativo-rima-rma">(.*?)</script>',html,re.S)
    if expected_preview.is_file():
        if not match_preview or json.loads(match_preview[1]) != json.loads(expected_preview.read_text(encoding="utf-8")):
            raise ValueError("Dados comparativos RIMA/RMA divergem do HTML")
    for asset in ("assets/style-blue.css", "assets/app-blue.js"):
        version = hashlib.sha256((root / asset).read_bytes()).hexdigest()[:12]
        if f'"{asset}?v={version}"' not in html:
            raise ValueError(f"HTML usa versão desatualizada de {asset}; regenere o site")
    return {name: len(rows) for name, rows in datasets.items()}


if __name__ == "__main__":
    print(json.dumps(validate_project(), ensure_ascii=False))

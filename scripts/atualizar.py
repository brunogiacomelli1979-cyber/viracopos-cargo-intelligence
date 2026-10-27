"""Coleta SGS incremental com sobreposição de 12 meses e fallback por série."""
import argparse
import csv
import hashlib
import io
import json
import logging
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from validar_dados import ROOT, SCHEMAS, read_csv, validate_metadata, validate_rows

SERIES = {"selic_meta_pct_aa": 432, "dolar_venda_medio_brl": 1, "ipca_pct_mes": 433}


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
    request = Request(url, headers={"User-Agent": "VCP-Insights/1.1 (public research)"})
    with urlopen(request, timeout=30) as response:
        raw = response.read()
    data = json.loads(raw)
    if not isinstance(data, list) or not data:
        raise ValueError("SGS sem observações")
    return data, {"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "registros": len(data)}


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


def build(offline=False, root=ROOT):
    now = datetime.now(timezone.utc)
    datasets = {name: read_csv(name, root) for name in SCHEMAS}
    metadata = json.loads((root / "data/fontes.json").read_text(encoding="utf-8"))
    validate_metadata(metadata, datasets)
    previous_path = root / "data/dashboard.json"
    previous_snapshot = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
    statuses = previous_snapshot.get("coleta_bcb", {"status": "não executada"})
    if not offline:
        datasets["macro"], statuses = collect(datasets["macro"], metadata, now)
    validate_metadata(metadata, datasets)
    for name, rows in datasets.items():
        metadata[name]["referencia_inicial"] = rows[0]["mes"] if rows else None
        metadata[name]["referencia_final"] = rows[-1]["mes"] if rows else None
    snapshot = {"versao": "1.1.0", "gerado_em_utc": now.isoformat(), "modo_compilacao": "offline" if offline else "online", "contexto": "Carga física, valor FOB e peso líquido têm coberturas distintas.", "coleta_bcb": statuses, "metadados": metadata, **datasets}
    compact = json.dumps(snapshot, ensure_ascii=False, allow_nan=False, separators=(",", ":")).replace("<", "\\u003c")
    template = (root / "index.template.html").read_text(encoding="utf-8")
    if template.count("{{DASHBOARD_JSON}}") != 1:
        raise ValueError("template precisa de um único marcador de dados")
    # Validate everything before replacing outputs. Each individual replacement is atomic.
    if not offline:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=SCHEMAS["macro"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(datasets["macro"])
        atomic_write(root / "data/macro.csv", stream.getvalue())
    atomic_write(root / "data/fontes.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    atomic_write(root / "data/dashboard.json", json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    atomic_write(root / "index.html", template.replace("{{DASHBOARD_JSON}}", compact))
    logging.info("Snapshot gerado: %s", {name: len(rows) for name, rows in datasets.items()})
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    build(args.offline)

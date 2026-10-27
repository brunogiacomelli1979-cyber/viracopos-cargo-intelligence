"""Série mensal real dos RMA da concessionária de Viracopos.

O RMA publica carga internacional total (importação + exportação), sem
separar sentidos. Courier é coluna distinta e não é somado à carga comum.
"""
import csv
import hashlib
import io
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin

from fontes_http import get_bytes

INDEX_URL = "https://www.viracopos.com/pt_br/institucional/estatisticas-e-publicacoes.htm"
MONTHS = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
FIELDS = ["mes", "carga_internacional_t", "carga_domestica_t", "courier_internacional_t"]


def normalized(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def extract_rma(content):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    text = reader.pages[0].extract_text(extraction_mode="layout")
    return parse_rma_text(text)


def parse_rma_text(text):
    """Valida e extrai a primeira página, também testável sem PDFs binários."""
    plain = normalized(text)
    if not all(value in plain for value in ("movimentacao de cargas", "toneladas", "importacoes + exportacoes")):
        raise ValueError("RMA sem cabeçalho/unidade/nota internacional esperados")
    match = re.search(r"movimento operacional[^\n]+?(20\d{2})", plain)
    if not match:
        raise ValueError("Ano do RMA não identificado")
    year = int(match[1])
    rows = []
    source_totals = None
    for line in plain.splitlines():
        row_match = re.match(r"\s*(" + "|".join(MONTHS) + r")\s+([\d.\s]+)$", line)
        if row_match:
            values = [int(value.replace(".", "")) for value in re.findall(r"\d+(?:\.\d{3})*", row_match[2])]
            if len(values) != 12:
                raise ValueError(f"RMA {year}, {row_match[1]}: esperadas 12 colunas, recebidas {len(values)}")
            if values[6] + values[7] != values[8] or values[9] + values[10] != values[11]:
                raise ValueError("Totais mensais de carga inconsistentes no RMA")
            month = MONTHS.index(row_match[1]) + 1
            rows.append({"mes": f"{year}-{month:02d}", "carga_internacional_t": values[7], "carga_domestica_t": values[6], "courier_internacional_t": values[10]})
        elif source_totals is None and re.match(r"\s*soma\s+\d", line):
            source_totals = [int(value.replace(".", "")) for value in re.findall(r"\d+(?:\.\d{3})*", line)]
    if not rows or len(rows) > 12 or len({row["mes"] for row in rows}) != len(rows):
        raise ValueError("RMA sem série mensal única")
    if [row["mes"] for row in rows] != [f"{year}-{month:02d}" for month in range(1, len(rows) + 1)]:
        raise ValueError("RMA com lacuna inesperada no período publicado")
    if source_totals is None or len(source_totals) != 12:
        raise ValueError("RMA sem total de controle")
    for field, index in (("carga_domestica_t", 6), ("carga_internacional_t", 7), ("courier_internacional_t", 10)):
        # RMA values are published as whole tonnes; totals can differ by rounding.
        if abs(sum(row[field] for row in rows) - source_totals[index]) > len(rows):
            raise ValueError(f"RMA: soma mensal de {field} diverge do controle publicado")
    return rows, {"ano": year, "pagina": 1, "meses": len(rows), "controle_publicado_t": {"carga_domestica_t": source_totals[6], "carga_internacional_t": source_totals[7], "courier_internacional_t": source_totals[10]}}


def discover_rma(html, start_year=2025):
    found = {}
    for href in re.findall(r'href=["\x27]([^"\x27]+)', html, re.I):
        url = urljoin(INDEX_URL, href)
        name = unquote(url.rsplit("/", 1)[-1])
        match = re.search(r"20\d{2}", name)
        if "rma" in name.lower() and name.lower().endswith(".pdf") and match and int(match[0]) >= start_year:
            found[url] = int(match[0])
    if not found:
        raise ValueError("Índice oficial sem RMA para os anos selecionados")
    # Preserve source order among versions of the same year; URL hashes are not dates.
    return sorted(found, key=lambda url: found[url])


def collect_rma(existing_rows=None, now=None, fetcher=get_bytes, start_year=2025):
    now = now or datetime.now(timezone.utc)
    collected = now.isoformat()
    html = fetcher(INDEX_URL).decode("utf-8")
    merged = {row["mes"]: dict(row) for row in (existing_rows or [])}
    versions = {}
    for url in discover_rma(html, start_year):
        content = fetcher(url)
        rows, control = extract_rma(content)
        rank = (max(row["mes"] for row in rows), len(rows))
        year = control["ano"]
        if year not in versions or rank > versions[year][0]:
            receipt = {"url": url, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content), "coletado_em_utc": collected, **control}
            versions[year] = (rank, rows, receipt)
    receipts = []
    for year in sorted(versions):
        _, rows, receipt = versions[year]
        closed_rows = [row for row in rows if row["mes"] < now.strftime("%Y-%m")]
        for row in closed_rows:
            merged[row["mes"]] = row
        receipts.append(receipt)
    result = sorted(merged.values(), key=lambda row: row["mes"])
    if not result:
        raise ValueError("RMA sem competências encerradas para publicar")
    metadata = {
        "fonte_original": INDEX_URL,
        "fonte_nome": "Aeroportos Brasil Viracopos / RMA",
        "coletado_em_utc": collected,
        "unidades": {field: "toneladas" for field in FIELDS[1:]},
        "periodicidade": "mensal",
        "abrangencia": "Aeroporto Internacional de Viracopos, movimentação de carga publicada pela concessionária",
        "tratamento": "Página 1 dos RMA anuais: Movimentação de Cargas / INT* (importações + exportações), DOM e Movimentação de Cargas Courier / INT*. Números com ponto de milhar convertidos para toneladas inteiras. Courier mantido separado; meses não publicados omitidos. Havendo vários boletins do mesmo ano, selecionar maior competência e quantidade de meses; empate preserva o primeiro link no índice oficial.",
        "limitacoes": "Fonte da concessionária, não série ANAC. Não permite separar embarque/desembarque nem importação/exportação. Toneladas inteiras publicadas; totais podem diferir por arredondamento. Não somar automaticamente courier à carga comum; o documento apresenta colunas distintas sem explicitar sobreposição. Dados sujeitos a atualização sem aviso prévio.",
        "status": "validado",
        "referencia_inicial": result[0]["mes"] if result else None,
        "referencia_final": result[-1]["mes"] if result else None,
        "documentos": receipts,
    }
    return result, metadata


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    output = root / "data/staging/anac"
    output.mkdir(parents=True, exist_ok=True)
    rows, metadata = collect_rma()
    with (output / "viracopos_rma.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (output / "fontes_rma.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"meses": len(rows), "primeiro": rows[0], "ultimo": rows[-1]}, ensure_ascii=False))

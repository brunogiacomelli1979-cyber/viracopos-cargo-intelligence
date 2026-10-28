"""Estágio isolado dos CSVs mensais ANAC/RIMA para SBKP.

Não baixa arquivos nem modifica data/, index.html ou dashboard.json.
Usar somente depois de obter o CSV original via HTTPS verificado.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


FIELDS_REQUIRED = (
    "ANO", "MES", "NR_AEROPORTO_REFERENCIA", "NR_MOVIMENTO_TIPO",
    "NR_NATUREZA", "QT_CARGA", "QT_CORREIO",
)
NATURES = ("domestica", "internacional")
MOVEMENTS = ("pouso", "decolagem")
OUTPUT_FIELDS = (
    "mes", "natureza", "movimento", "carga_kg", "correio_kg",
    "registros", "carga_ausente", "correio_ausente", "status",
)
MAX_INPUT_BYTES = 200_000_000


def _canonical(value):
    decomposed = unicodedata.normalize("NFKD", (value or "").strip())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def _nonnegative(value, field, line):
    text = (value or "").strip()
    if not text:
        return None
    # Separador decimal: ponto ou vírgula. Não inferir milhar ou sentinelas.
    if not re.fullmatch(r"\d+(?:[.,]\d+)?", text):
        raise ValueError(f"linha {line}: {field} numérico inesperado: {text!r}")
    try:
        number = Decimal(text.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"linha {line}: {field} inválido") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"linha {line}: {field} negativo ou não finito")
    return number


def _decode(data):
    try:
        return data.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        try:
            return data.decode("cp1252"), "cp1252"
        except UnicodeDecodeError as exc:
            raise ValueError("Codificação não aceita: UTF-8 e CP1252 falharam") from exc


def _validate_month(month, today=None):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("competência inválida, usar AAAA-MM")
    if month >= (today or date.today()).strftime("%Y-%m"):
        raise ValueError("competência futura ou mês ainda aberto")


def process_file(file_path, month, *, today=None):
    """Agrega arquivo mensal original. Falha fechada para ambiguidades de SBKP."""
    _validate_month(month, today=today)
    path = Path(file_path)
    size = path.stat().st_size
    if size == 0 or size > MAX_INPUT_BYTES:
        raise ValueError("Arquivo vazio ou maior que o limite de segurança")
    raw = path.read_bytes()
    text, encoding = _decode(raw)
    if "\x00" in text:
        raise ValueError("Arquivo contém bytes nulos; não parece CSV textual")
    lines = text.splitlines(keepends=True)
    header_index = None
    for i, line in enumerate(lines[:20]):
        fields = next(csv.reader([line], delimiter=";", strict=True), [])
        fields = [x.strip().lstrip("\ufeff") for x in fields]
        if len(fields) == len(set(fields)) and set(FIELDS_REQUIRED).issubset(fields):
            header_index = i
            break
    if header_index is None:
        raise ValueError("Cabeçalho oficial RIMA não encontrado nas 20 primeiras linhas")
    preamble = [x.strip().lstrip("\ufeff") for x in lines[:header_index] if x.strip()]
    if not all(x.lower().startswith("atualizado em:") for x in preamble):
        raise ValueError("Preâmbulo RIMA inesperado")
    stream = io.StringIO("".join(lines[header_index:]), newline="")
    reader = csv.DictReader(stream, delimiter=";", strict=True)
    if not reader.fieldnames:
        raise ValueError("Cabeçalho ausente")
    reader.fieldnames = [f.strip() for f in reader.fieldnames]
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("Cabeçalho com colunas duplicadas")
    missing = set(FIELDS_REQUIRED) - set(reader.fieldnames)
    if missing:
        raise ValueError(f"Colunas RIMA ausentes: {', '.join(sorted(missing))}")

    groups = {(nature, movement): {
        "records": 0, "missing_cargo": 0, "missing_mail": 0,
        "cargo": Decimal(0), "mail": Decimal(0),
    } for nature in NATURES for movement in MOVEMENTS}
    rows_all = rows_sbkp = 0
    for row in reader:
        rows_all += 1
        line = reader.line_num
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"linha {line}: número de colunas inesperado")
        if _canonical(row["NR_AEROPORTO_REFERENCIA"]).upper() != "SBKP":
            continue
        rows_sbkp += 1
        year = (row["ANO"] or "").strip()
        mo = (row["MES"] or "").strip()
        if not year.isdigit() or not mo.isdigit() or f"{int(year):04d}-{int(mo):02d}" != month:
            raise ValueError(f"linha {line}: competência da linha não corresponde a {month}")
        nature_code = (row["NR_NATUREZA"] or "").strip().upper()
        movement_code = (row["NR_MOVIMENTO_TIPO"] or "").strip().upper()
        nature = {"D": "domestica", "I": "internacional"}.get(nature_code)
        movement = {"P": "pouso", "D": "decolagem"}.get(movement_code)
        if nature is None or movement is None:
            raise ValueError(f"linha {line}: códigos ANAC desconhecidos: {nature_code!r}/{movement_code!r}")
        cargo = _nonnegative(row["QT_CARGA"], "QT_CARGA", line)
        mail = _nonnegative(row["QT_CORREIO"], "QT_CORREIO", line)
        group = groups[(nature, movement)]
        group["records"] += 1
        if cargo is None:
            group["missing_cargo"] += 1
        else:
            group["cargo"] += cargo
        if mail is None:
            group["missing_mail"] += 1
        else:
            group["mail"] += mail
    if not rows_all or not rows_sbkp:
        raise ValueError("Arquivo sem registros ou sem movimentos de SBKP; não publicar série vazia")

    result = []
    for nature in NATURES:
        for movement in MOVEMENTS:
            group = groups[(nature, movement)]
            count = group["records"]
            result.append({
                "mes": month,
                "natureza": nature,
                "movimento": movement,
                # Subtotal ausente se ao menos um registro não tiver quantidade.
                "carga_kg": "" if not count or group["missing_cargo"] else format(group["cargo"], "f"),
                "correio_kg": "" if not count or group["missing_mail"] else format(group["mail"], "f"),
                "registros": count,
                "carga_ausente": group["missing_cargo"],
                "correio_ausente": group["missing_mail"],
                "status": "sem_movimentos" if not count else ("incompleto" if group["missing_cargo"] or group["missing_mail"] else "completo"),
            })
    return {
        "rows": result,
        "provenance": {
            "mes": month,
            "fonte_estatistica": "ANAC/RIMA - Operador Aeroportuário",
            "aeroporto_icao": "SBKP",
            "nome_arquivo_original": path.name,
            "sha256_original": hashlib.sha256(raw).hexdigest(),
            "bytes_original": len(raw),
            "codificacao_detectada": encoding,
            "linhas_arquivo": rows_all,
            "linhas_sbkp": rows_sbkp,
            "metricas": ["QT_CARGA", "QT_CORREIO"],
            "unidade_original": "kg",
            "populacao": "Movimentos informados por operadores aeroportuários (não RMA da concessionária nem Comex/MDIC)",
            "cobertura_completa": all(r["status"] == "completo" for r in result),
            "aviso": "Resultados são staging local; totais somente por natureza e movimento. Ausência não vira zero.",
        }
    }


def write_staging(result, out_dir):
    """Gera dois arquivos na pasta indicada, nunca no pipeline público."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    month = result["provenance"]["mes"]
    csv_path = directory / f"anac_rima_sbkp_{month}.csv"
    meta_path = directory / f"anac_rima_sbkp_{month}.json"
    if csv_path.exists() or meta_path.exists():
        raise FileExistsError("Saída existente: não sobrescrever série/recibo sem revisão explícita")
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(result["rows"])
    meta_path.write_text(json.dumps(result["provenance"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return csv_path, meta_path


def main():
    parser = argparse.ArgumentParser(description="Processar RIMA/ANAC mensal em staging local, sem publicar")
    parser.add_argument("--input", required=True, type=Path, help="CSV original obtido do portal oficial")
    parser.add_argument("--month", required=True, help="Competência AAAA-MM")
    parser.add_argument("--out-dir", required=True, type=Path, help="Preferir data/staging/anac_rima")
    args = parser.parse_args()
    result = process_file(args.input, args.month)
    outputs = write_staging(result, args.out_dir)
    print(json.dumps({"arquivos": [str(p) for p in outputs], "resumo": result["provenance"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

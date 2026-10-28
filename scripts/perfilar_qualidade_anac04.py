"""ANAC-04: perfil do grão operacional SBKP, só de CSVs arquivados e validados.

Não baixa, não modifica manifesto, não deduplica, não compara tonelagens
RIMA/RMA como se fossem a mesma população e não libera publicação.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from auditar_anac_rima import inspect
from validar_agrupamento_rima import validate

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 100_000_000
REQUIRED = {"ANO", "MES", "NR_AEROPORTO_REFERENCIA", "NR_MOVIMENTO_TIPO",
            "NR_NATUREZA", "QT_CARGA", "QT_CORREIO"}
NUMERIC = re.compile(r"^\d+(?:[.,]\d+)?$")
KEYS = {
    "calco": ("NR_AERONAVE_MARCAS", "NR_MOVIMENTO_TIPO", "DT_CALCO", "HH_CALCO"),
    "toque": ("NR_AERONAVE_MARCAS", "NR_MOVIMENTO_TIPO", "DT_TOQUE", "HH_TOQUE"),
}
DATE_FIELDS = ("DT_CALCO", "DT_TOQUE")
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d",
                "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S")


def _date_status(value, month):
    value = value.strip()
    if not value:
        return "nao_informada"
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
            return "na_competencia" if parsed.strftime("%Y-%m") == month else "fora_da_competencia"
        except ValueError:
            continue
    return "formato_nao_reconhecido"


def _weight(value, column):
    value = value.strip()
    if not value:
        return "ausente"
    if not NUMERIC.fullmatch(value):
        raise ValueError(f"{column}: numero invalido, sem conversao presumida")
    try:
        number = Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"{column}: nao numerico") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"{column}: peso negativo/nao finito")
    return "zero" if number == 0 else "positivo"


def profile_csv(data, month):
    """Perfila distribuição sem presumir chave primária de voo."""
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month) or month < "2020-01":
        raise ValueError("Competencia fora do recorte 2020+")
    reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""),
                            delimiter=";", strict=True)
    header = reader.fieldnames or []
    if not header or len(header) != len(set(header)) or not REQUIRED.issubset(set(header)):
        raise ValueError("Esquema obrigatório ausente ou duplicado")
    volumes = Counter()
    cargo = Counter()
    mail = Counter()
    service = Counter()
    dates = {field: Counter() for field in DATE_FIELDS if field in header}
    seen_exact = set()
    repeated_exact = 0
    keys = {name: {"vistos": set(), "cobertura": 0, "colisoes": 0}
            for name, fields in KEYS.items() if set(fields).issubset(header)}
    total = 0
    for row in reader:
        total += 1
        if None in row or any(value is None or "\x00" in value for value in row.values()):
            raise ValueError(f"Linha {reader.line_num}: colunas ou bytes invalidos")
        if (row["NR_AEROPORTO_REFERENCIA"].strip().upper() != "SBKP"
                or not row["ANO"].strip().isdigit()
                or not row["MES"].strip().isdigit()
                or f"{int(row['ANO']):04d}-{int(row['MES']):02d}" != month):
            raise ValueError(f"Linha {reader.line_num}: aeroporto ou competencia divergente")
        nature, movement = row["NR_NATUREZA"].strip(), row["NR_MOVIMENTO_TIPO"].strip()
        if nature not in ("D", "I") or movement not in ("P", "D"):
            raise ValueError(f"Linha {reader.line_num}: movimento/natureza desconhecidos")
        volumes[f"{nature}/{movement}"] += 1
        cargo_status = _weight(row["QT_CARGA"], "QT_CARGA")
        mail_status = _weight(row["QT_CORREIO"], "QT_CORREIO")
        cargo[cargo_status] += 1
        mail[mail_status] += 1
        service[(row.get("NR_SERVICE_TYPE") or "").strip() or "(nao_informado)"] += 1

        exact = hashlib.sha256("\x1f".join(row[col] for col in header).encode("utf-8")).digest()
        if exact in seen_exact:
            repeated_exact += 1
        else:
            seen_exact.add(exact)
        for name, fields in KEYS.items():
            if name not in keys:
                continue
            values = tuple(row[col].strip() for col in fields)
            if not all(values):
                continue
            metrics = keys[name]
            metrics["cobertura"] += 1
            # Natureza faz parte da chave candidata: códigos ANAC podem
            # representar registros distintos do mesmo movimento físico.
            candidate = (nature, *values)
            if candidate in metrics["vistos"]:
                metrics["colisoes"] += 1
            else:
                metrics["vistos"].add(candidate)
        for field, counts in dates.items():
            counts[_date_status(row[field], month)] += 1
    if not total:
        raise ValueError("Recorte sem movimentos SBKP")
    key_report = {}
    for name, metrics in keys.items():
        key_report[name] = {
            "linhas_com_chave_completa": metrics["cobertura"],
            "linhas_sem_chave_completa": total - metrics["cobertura"],
            "colisoes_adicionais": metrics["colisoes"],
            "pct_cobertura": round(100 * metrics["cobertura"] / total, 4),
            "pct_colisoes_sobre_chaves_completas": (
                round(100 * metrics["colisoes"] / metrics["cobertura"], 4)
                if metrics["cobertura"] else None),
            "significado": "Colisao candidata exige investigacao; NUNCA remover linhas automaticamente",
        }
    alerts = []
    if repeated_exact:
        alerts.append("linhas_idênticas_exigem_analise_de_granularidade")
    if any(stat["colisoes_adicionais"] for stat in key_report.values()):
        alerts.append("colisoes_de_chave_nao_comprovam_duplicacao_fisica")
    if cargo["ausente"] or mail["ausente"]:
        alerts.append("pesos_ausentes_nao_equivalem_a_zero")
    if any(x.get("fora_da_competencia", 0) or x.get("formato_nao_reconhecido", 0)
           for x in dates.values()):
        alerts.append("datas_operacionais_foras_da_competencia_ou_nao_reconhecidas")
    return {
        "competencia": month,
        "registros_movimentacao": total,
        "movimentos_por_natureza": dict(sorted(volumes.items())),
        "carga": {"movimentos_com_carga_positiva": cargo["positivo"],
                  "movimentos_com_carga_zero": cargo["zero"],
                  "movimentos_com_carga_ausente": cargo["ausente"],
                  "pct_carga_positiva": round(100*cargo["positivo"]/total, 4),
                  "nota": "Contagem de registros com QT_CARGA positiva; nao equivale automaticamente a numero de voos cargueiros"},
        "correio": {"positivo": mail["positivo"], "zero": mail["zero"], "ausente": mail["ausente"]},
        "service_type": dict(sorted(service.items())),
        "duplicatas_exatas_adicionais": repeated_exact,
        "chaves_operacionais_candidatas": key_report,
        "datas_operacionais": {k: dict(sorted(v.items())) for k, v in dates.items()},
        "alertas_investigacao": alerts,
        "apto_publicacao": False,
    }


def profile_archive(root=ROOT):
    root = Path(root).resolve()
    verified = inspect(root)
    cross = validate(root)
    if (verified.get("erros_criticos") or verified.get("integridade_arquivos") != "aprovada"
            or cross.get("erros") or cross.get("resultado") != "aprovado_tecnicamente"):
        raise ValueError("ANAC-04 bloqueada por falha de integridade ou agregacao independente")
    manifest = json.loads((root / "data/anac/rima/manifesto.json").read_text(encoding="utf-8"))
    months = manifest["competencias"]
    profiles, alerts = {}, []
    for month, entry in sorted(months.items()):
        source = (root / entry["caminho_sbkp"]).resolve()
        if not source.is_relative_to((root / "data/anac/rima").resolve()) or not source.is_file():
            raise ValueError("Caminho ANAC invalido")
        if source.stat().st_size > 10_000_000:
            raise ValueError("Gzip fora do limite")
        with gzip.open(source, "rb") as archive:
            data = archive.read(LIMIT + 1)
        if len(data) > LIMIT or hashlib.sha256(data).hexdigest() != entry["conteudo_sbkp_sha256"]:
            raise ValueError("CSV de competencia nao confere com manifesto")
        item = profile_csv(data, month)
        expected = verified["competencias"][month]
        if (item["registros_movimentacao"] != entry["linhas_sbkp"]
                or item["registros_movimentacao"] != cross["comparacoes"][month]["registros"]
                or item["movimentos_por_natureza"] != expected["movimentos_por_natureza"]
                or item["duplicatas_exatas_adicionais"] != expected["duplicatas_linha_inteira"]):
            raise ValueError(f"{month}: perfil de qualidade diverge dos auditores")
        profiles[month] = item
        if item["alertas_investigacao"]:
            alerts.append({"competencia": month, "tipos": item["alertas_investigacao"]})
    return {
        "schema": "anac04-perfil-qualidade-v1",
        "escopo": "somente competencias arquivadas e tecnicamente verificadas",
        "competencias_analisadas": sorted(profiles),
        "quantidade_competencias": len(profiles),
        "total_movimentacoes": sum(item["registros_movimentacao"] for item in profiles.values()),
        "quantidade_movimentacoes_com_carga_positiva": sum(
            item["carga"]["movimentos_com_carga_positiva"] for item in profiles.values()),
        "perfis": profiles,
        "alertas": alerts,
        "limites": ["Sem chave primária única homologada",
                    "Duplicatas exatas e colisoes de chaves sao alertas, nao exclusoes",
                    "RIMA vs RMA: populacao, processo e periodicidade exigem conciliacao",
                    "Os quatro meses nao representam serie temporal completa 2020-2025"],
        "liberado_dashboard": False,
        "liberado_nova_coleta": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = profile_archive(args.root)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()

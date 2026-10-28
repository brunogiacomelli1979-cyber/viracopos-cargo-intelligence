"""Perfil exploratório RIMA/SBKP: tipo de serviço e direção em 2024-01.

Somente leitura de arquivo já arquivado; não baixa nem publica novos dados.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
from collections import Counter
from pathlib import Path

from conciliar_rima_rma import _weight
from validar_agrupamento_rima import validate

ROOT = Path(__file__).resolve().parents[1]


def _date_month(value):
    """Lê formatos conhecidos; não interpreta formatos desconhecidos."""
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d",
                "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m")
        except ValueError:
            pass
    return "formato_desconhecido"


def profile_csv(data, month):
    stream = io.StringIO(data.decode("utf-8"), newline="")
    reader = csv.DictReader(stream, delimiter=";", strict=True)
    required = {"ANO", "MES", "NR_AEROPORTO_REFERENCIA", "NR_NATUREZA",
                "NR_MOVIMENTO_TIPO", "NR_SERVICE_TYPE", "QT_CARGA"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise ValueError("Esquema insuficiente para perfil de serviço")
    groups = defaultdict(lambda: {"registros": 0, "carga_kg": Decimal(0), "carga_zero": 0})
    directions = defaultdict(lambda: {"registros": 0, "carga_kg": Decimal(0)})
    date_counts = Counter()
    by_nature = defaultdict(Counter)
    date_samples = {}
    has_calco = "DT_CALCO" in (reader.fieldnames or [])
    keys = (
        ("calco", ("NR_AERONAVE_MARCAS", "NR_MOVIMENTO_TIPO", "DT_CALCO", "HH_CALCO")),
        ("toque", ("NR_AERONAVE_MARCAS", "NR_MOVIMENTO_TIPO", "DT_TOQUE", "HH_TOQUE")),
    )
    key_coverage = Counter()
    key_seen = defaultdict(set)
    key_collisions = Counter()
    key_by_nature = defaultdict(Counter)
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("CSV com coluna ausente")
        if row["NR_AEROPORTO_REFERENCIA"] != "SBKP" or f"{int(row['ANO']):04d}-{int(row['MES']):02d}" != month:
            raise ValueError("Aeroporto ou competência incompatível")
        if row["NR_NATUREZA"] not in ("D", "I") or row["NR_MOVIMENTO_TIPO"] not in ("P", "D"):
            raise ValueError("Natureza ou movimento fora do domínio")
        code = row["NR_SERVICE_TYPE"].strip() or "(nao_informado)"
        cargo = _weight(row["QT_CARGA"], "QT_CARGA")
        key = (row["NR_NATUREZA"], row["NR_MOVIMENTO_TIPO"], code)
        groups[key]["registros"] += 1
        groups[key]["carga_kg"] += cargo
        if cargo == 0:
            groups[key]["carga_zero"] += 1
        agg = directions[(row["NR_NATUREZA"], row["NR_MOVIMENTO_TIPO"])]
        agg["registros"] += 1
        agg["carga_kg"] += cargo
        for key_type, fields in keys:
            if not all(field in row for field in fields):
                continue
            values = tuple(row[field].strip() for field in fields)
            if not all(values):
                continue
            key_coverage[key_type] += 1
            composite = (row["NR_NATUREZA"], values)
            if composite in key_seen[key_type]:
                key_collisions[key_type] += 1
                key_by_nature[row["NR_NATUREZA"]][key_type] += 1
            else:
                key_seen[key_type].add(composite)
        if has_calco:
            raw_calco = row["DT_CALCO"].strip()
            calco_month = _date_month(raw_calco)
            label = ("data_ausente" if calco_month is None
                     else "formato_desconhecido" if calco_month == "formato_desconhecido"
                     else "na_competencia" if calco_month == month
                     else "fora_da_competencia")
            date_counts[label] += 1
            by_nature[row["NR_NATUREZA"]][label] += 1
            if label in ("formato_desconhecido", "fora_da_competencia"):
                key_name = f"{row['NR_NATUREZA']}/{row['NR_MOVIMENTO_TIPO']}/{label}"
                if len(date_samples.setdefault(key_name, [])) < 3:
                    date_samples[key_name].append(raw_calco[:60])
    totals = {nat: sum((v["carga_kg"] for (n, m), v in directions.items() if n == nat),
                       Decimal(0)) for nat in ("D", "I")}
    entries = []
    for (nature, movement, service), value in groups.items():
        denom = totals[nature]
        entries.append({
            "natureza": "internacional" if nature == "I" else "domestica",
            "movimento": "pouso" if movement == "P" else "decolagem",
            "service_type": service,
            "registros": value["registros"],
            "carga_zero": value["carga_zero"],
            "carga_kg": format(value["carga_kg"], "f"),
            "participacao_na_natureza_pct": (format(value["carga_kg"] * 100 / denom, ".4f")
                                          if denom else None)
        })
    entries.sort(key=lambda x: (-Decimal(x["carga_kg"]), x["natureza"], x["service_type"]))
    return {
        "mes": month,
        "registros": sum(x["registros"] for x in entries),
        "total_domestica_kg": format(totals["D"], "f"),
        "total_internacional_kg": format(totals["I"], "f"),
        "grupos_por_servico": entries,
        "auditoria_chaves_movimento": {
            "cobertura": dict(key_coverage),
            "colisoes_potenciais": dict(key_collisions),
            "colisoes_por_natureza": {"domestica": dict(key_by_nature["D"]),
                                      "internacional": dict(key_by_nature["I"])},
            "interpretacao": "Chaves compostas matrícula+tipo de movimento+data+hora; colisão não prova duplicação física. Não remover linhas automaticamente."
        },
        "auditoria_calco": {
            "campo_disponivel": has_calco,
            "ocorrencias": dict(date_counts),
            "por_natureza": {"domestica": dict(by_nature["D"]),
                             "internacional": dict(by_nature["I"])},
            "amostras_sem_identificadores": date_samples,
            "criterio": "DT_CALCO = calço (pouso) ou descalço (decolagem). Datas fora do mês não são excluídas automaticamente."
        },
        "publicavel": False,
        "alerta": "Service Type é dado descritivo: não excluir categorias para forçar equivalência RMA."
    }


def profile_archived(root=ROOT, month="2024-01"):
    prior = validate(root)
    if prior["resultado"] != "aprovado_tecnicamente":
        raise ValueError("Validação ANAC insuficiente")
    entry = json.loads((root/"data/anac/rima/manifesto.json").read_text())["competencias"][month]
    path = (root/entry["caminho_sbkp"]).resolve()
    if not path.is_relative_to((root/"data/anac/rima").resolve()):
        raise ValueError("Caminho do acervo inválido")
    compressed = path.read_bytes()
    if hashlib.sha256(compressed).hexdigest() != entry["sha256_sbkp_gzip"]:
        raise ValueError("Hash do arquivo não confere")
    with gzip.open(path, "rb") as handle:
        data = handle.read(100_000_001)
    if len(data) > 100_000_000 or hashlib.sha256(data).hexdigest() != entry["conteudo_sbkp_sha256"]:
        raise ValueError("Conteúdo não confere")
    report = profile_csv(data, month)
    expected_groups = prior["comparacoes"][month]["grupos"]
    for nature, code in (("domestica", "D"), ("internacional", "I")):
        expected = sum((Decimal(expected_groups[f"{nature}/{m}"]["carga_kg"])
                       for m in ("pouso", "decolagem")), Decimal(0))
        if Decimal(report[f"total_{nature}_kg"]) != expected:
            raise ValueError(f"Perfil de serviço diverge da conciliação ANAC: {nature}")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = profile_archived()
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

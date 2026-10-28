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
from pathlib import Path

from conciliar_rima_rma import _weight
from validar_agrupamento_rima import validate

ROOT = Path(__file__).resolve().parents[1]


def profile_csv(data, month):
    stream = io.StringIO(data.decode("utf-8"), newline="")
    reader = csv.DictReader(stream, delimiter=";", strict=True)
    required = {"ANO", "MES", "NR_AEROPORTO_REFERENCIA", "NR_NATUREZA",
                "NR_MOVIMENTO_TIPO", "NR_SERVICE_TYPE", "QT_CARGA"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise ValueError("Esquema insuficiente para perfil de serviço")
    groups = defaultdict(lambda: {"registros": 0, "carga_kg": Decimal(0), "carga_zero": 0})
    directions = defaultdict(lambda: {"registros": 0, "carga_kg": Decimal(0)})
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

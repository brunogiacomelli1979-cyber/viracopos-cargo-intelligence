"""Planeja a cobertura ANAC/RIMA SBKP usando somente inventario e manifesto locais.

NENHUMA operacao de rede, download, commit ou alteracao do acervo.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRST = "2020-01"
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def validate_month(value):
    if not isinstance(value, str) or not MONTH.fullmatch(value) or value < FIRST:
        raise ValueError(f"Competencia invalida ou anterior a {FIRST}: {value!r}")
    return value


def range_months(first, last):
    first, last = validate_month(first), validate_month(last)
    if first > last:
        raise ValueError("Periodo invertido")
    year, month = map(int, first.split("-"))
    while f"{year:04d}-{month:02d}" <= last:
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year, month = year + 1, 1


def plan(inventory, manifest, start="2020-01", end="2025-12"):
    if inventory.get("schema") != "anac-rima-inventario-v1":
        raise ValueError("Contrato de inventario ANAC desconhecido")
    if manifest.get("schema") != "anac_rima_sbkp_v1" or manifest.get("aeroporto") != "SBKP":
        raise ValueError("Manifesto ANAC/SBKP desconhecido")
    listed = set()
    for year, spec in inventory.get("anos", {}).items():
        if not re.fullmatch(r"20\d{2}", year):
            raise ValueError(f"Ano de inventario invalido: {year}")
        months = spec.get("meses_csv", [])
        if not isinstance(months, list) or len(months) != len(set(months)):
            raise ValueError(f"Meses repetidos ou formato invalido em {year}")
        for month in months:
            if type(month) is not int or not 1 <= month <= 12:
                raise ValueError(f"Mes invalido em {year}: {month}")
            listed.add(validate_month(f"{year}-{month:02d}"))
    archive = manifest.get("competencias", {})
    if not isinstance(archive, dict):
        raise ValueError("Manifesto sem mapa de competencias")
    for month in archive:
        validate_month(month)
    output = []
    for month in range_months(start, end):
        if month in archive:
            status = "arquivado_pendente_reauditoria"
        elif month in listed:
            status = "listado_pendente_captura"
        elif month[:4] in inventory.get("anos", {}):
            status = "nao_listado_no_indice"
        elif month[:4] in inventory.get("indices_indisponiveis", []):
            status = "indice_indisponivel"
        else:
            status = "nao_inventariado"
        output.append({"competencia": month, "estado": status})
    return {
        "schema": "anac-rima-plano-v1",
        "fonte_inventario": inventory.get("evidencia"),
        "sem_download": True,
        "sem_publicacao": True,
        "resumo": dict(sorted(Counter(item["estado"] for item in output).items())),
        "competencias": output,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventario", type=Path, default=ROOT / "data/anac/rima/inventario_disponibilidade.json")
    parser.add_argument("--manifesto", type=Path, default=ROOT / "data/anac/rima/manifesto.json")
    parser.add_argument("--inicio", default="2020-01")
    parser.add_argument("--fim", default="2025-12")
    parser.add_argument("--saida", type=Path)
    args = parser.parse_args()
    inventory = json.loads(args.inventario.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifesto.read_text(encoding="utf-8"))
    result = json.dumps(plan(inventory, manifest, args.inicio, args.fim), ensure_ascii=False, indent=2) + "\n"
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()

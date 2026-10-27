"""Auditoria de lotes ANAC SBKP sem misturar dados RMA.

Entrada: diretórios de artefatos por ano, com CSV agregado e recibos ANAC.
Saída: arquivos completos da série 2020–2024 prontos para revisão no PR.
Este módulo NÃO publica nada no dashboard.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

FIELDS = ["mes", "natureza", "sentido", "carga_paga_t", "carga_gratis_t",
          "correio_t", "carga_sem_correio_t", "etapas"]
NUMERIC = ["carga_paga_t", "carga_gratis_t", "correio_t", "carga_sem_correio_t"]
START_YEAR, END_YEAR = 2020, 2024


def validate_parts(staging):
    combined = []
    receipts = []
    review = []
    for year in range(START_YEAR, END_YEAR + 1):
        directory = staging / f"anac-sbkp-{year}"
        csv_path = directory / "anac_sbkp_carga_mensal.csv"
        json_path = directory / "anac_sbkp_fontes.json"
        if not csv_path.is_file() or not json_path.is_file():
            raise ValueError(f"Artefato anual incompleto: {year}")
        info = json.loads(json_path.read_text(encoding="utf-8"))
        if info.get("status") != "validado" or info.get("falhas"):
            raise ValueError(f"Ano {year}: extração não integralmente validada")
        if info.get("meses_esperados") != 12 or info.get("meses_validados") != 12:
            raise ValueError(f"Ano {year}: esperadas 12 competências validadas")
        monthly_receipts = info.get("recibos", [])
        if len(monthly_receipts) != 12:
            raise ValueError(f"Ano {year}: recibos ausentes ou duplicados")
        for month in range(1, 13):
            expected = f"{year}-{month:02d}"
            r = monthly_receipts[month-1]
            if r.get("competencia") != expected:
                raise ValueError(f"Recibo mensal fora de sequência: {expected}")
            if (not re.fullmatch(r"[0-9a-f]{64}", r.get("sha256", ""))
                    or not re.fullmatch(r"[0-9a-f]{64}", r.get("csv_sha256", ""))
                    or not isinstance(r.get("etapas_sbkp"), int)
                    or r["etapas_sbkp"] <= 0
                    or not isinstance(r.get("etapas_locais_sbkp"), int)
                    or r["etapas_locais_sbkp"] < 0):
                raise ValueError(f"Recibo incompleto: {expected}")
        with csv_path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDS:
                raise ValueError(f"Esquema agregado divergente: {year}")
            rows = list(reader)
        by_month = {}
        keys = set()
        for row in rows:
            month = row["mes"]
            if not re.fullmatch(fr"{year}-(0[1-9]|1[0-2])", month):
                raise ValueError(f"Ano ou competência inválida: {month}")
            key = (row["mes"], row["natureza"], row["sentido"])
            if key in keys:
                raise ValueError(f"Chave ANAC repetida: {key}")
            keys.add(key)
            if row["natureza"] not in ("domestica", "internacional") or row["sentido"] not in ("embarque","desembarque","local"):
                raise ValueError(f"Classe ANAC não prevista: {key}")
            try:
                numbers = [float(row[field]) for field in NUMERIC]
                steps = int(row["etapas"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Número inválido em {key}") from exc
            if not all(math.isfinite(v) and v >= 0 for v in numbers) or steps <= 0:
                raise ValueError(f"Medida ANAC inválida: {key}")
            if not math.isclose(numbers[0]+numbers[1], numbers[3], abs_tol=1e-6, rel_tol=0):
                raise ValueError(f"Soma paga+grátis incorreta: {key}")
            by_month.setdefault(month, []).append(row)
        for month in range(1,13):
            expected = f"{year}-{month:02d}"
            sample = by_month.get(expected,[])
            regular = {(r["natureza"],r["sentido"]) for r in sample if r["sentido"] != "local"}
            expected_regular = {(n,d) for n in ("domestica","internacional") for d in ("embarque","desembarque")}
            if regular != expected_regular:
                raise ValueError(f"Sem quatro grupos regulares: {expected}; obtidos {regular}")
            receipt = monthly_receipts[month-1]
            total = sum(int(r["etapas"]) for r in sample)
            local = sum(int(r["etapas"]) for r in sample if r["sentido"]=="local")
            if total != receipt["etapas_sbkp"] or local != receipt["etapas_locais_sbkp"]:
                raise ValueError(f"Contagem de etapas não reconcilia: {expected}")
            review.append({"mes":expected,"etapas_sbkp":total,"etapas_locais":local,
                           "grupos":len(sample),
                           "internacional_embarque_t":sum(float(r["carga_sem_correio_t"]) for r in sample if r["natureza"]=="internacional" and r["sentido"]=="embarque"),
                           "internacional_desembarque_t":sum(float(r["carga_sem_correio_t"]) for r in sample if r["natureza"]=="internacional" and r["sentido"]=="desembarque")})
        combined.extend(rows)
        receipts.extend(monthly_receipts)
    if len(review) != 60 or len(receipts) != 60:
        raise ValueError("Expectativa de sessenta meses não atendida")
    combined.sort(key=lambda r:(r["mes"],r["natureza"],r["sentido"]))
    metadata={"fonte":"ANAC Etapa Básica — dados oficiais do transporte aéreo",
              "aeroporto":"SBKP","competencias":"2020-01 a 2024-12",
              "unidade":"toneladas por etapa básica","abrangencia":"etapas com SBKP como origem ou destino",
              "carga_t":"(kg_carga_paga+kg_carga_gratis)/1000; correio separado",
              "etapas_locais":"SBKP→SBKP isoladas, não incluídas nas somas de embarque/desembarque",
              "nao_equivale_a":"toneladas RMA concessionária ou valores/pesos aduaneiros MDIC",
              "competencias_validadas":60,"registros_agregados":len(combined),
              "recibos":receipts}
    return combined,metadata,review


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--staging",type=Path,default=Path("data/staging/anac-downloads"))
    p.add_argument("--dest",type=Path,default=Path("data"))
    args=p.parse_args()
    rows,metadata,diagnostics=validate_parts(args.staging)
    args.dest.mkdir(parents=True,exist_ok=True)
    with (args.dest/"anac_sbkp_2020_2024.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (args.dest/"anac_sbkp_fontes_2020_2024.json").write_text(
        json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.dest/"anac_sbkp_auditoria_2020_2024.json").write_text(
        json.dumps({"status":"validado","registros":len(rows),
                    "competencias":diagnostics,
                    "observacao":"Série aeronáutica ANAC independente da RMA"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"VALIDADO: {len(diagnostics)} meses, {len(rows)} grupos, {len(metadata['recibos'])} recibos")


if __name__=="__main__":
    main()

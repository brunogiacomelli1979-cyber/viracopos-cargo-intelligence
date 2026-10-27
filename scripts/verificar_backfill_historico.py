"""Reconciliação independente do backfill 2020–2024 antes do merge.

Executa-se somente no workflow histórico/staging. Os valores nacionais anuais
são uma referência da tabela oficial MDIC consultada em 27/10/2026;
revisões legítimas exigem atualizar esta referência com documentação.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from validar_dados import ROOT, read_csv, validate_project

FIRST_YEAR, LAST_YEAR = 2020, 2024
# Fonte: https://balanca.mdic.gov.br/balanca/publicacoes_dados_consolidados/pg.html
# Unidades: US$ bilhões FOB (publicação original em US$ milhões).
MDIC_ANNUAL_REFERENCE = {
    2020: (209.1802, 158.7868),
    2021: (280.8146, 219.4080),
    2022: (334.1360, 272.6107),
    2023: (339.6958, 240.7928),
    2024: (337.0462, 262.8696),
}
MAX_ANNUAL_DIFF_USD_BI = 0.001  # US$ 1 milhão, maior que o arredondamento de referência.


def verify(root: Path = ROOT) -> dict:
    validate_project(root)
    data = json.loads((root / "data/dashboard.json").read_text(encoding="utf-8"))
    metadata = data["metadados"]
    months = {f"{y}-{m:02d}" for y in range(FIRST_YEAR, LAST_YEAR + 1)
              for m in range(1, 13)}
    counts = {}
    for name in ("brasil", "comex", "macro"):
        rows = read_csv(name, root)
        observed = {r["mes"] for r in rows}
        missing = sorted(months - observed)
        if missing:
            raise ValueError(f"{name}: meses 2020–2024 ausentes: {missing}")
        counts[name] = len(rows)

    comex = read_csv("comex", root)
    for flow in ("importacao", "exportacao"):
        present = {r["mes"] for r in comex if r["fluxo"] == flow}
        missing = sorted(months - present)
        if missing:
            raise ValueError(f"Comex/{flow}: meses ausentes: {missing}")

    receipts = {}
    for item in metadata["comex"]["arquivos"]:
        match = re.fullmatch(r"https://balanca\.mdic\.gov\.br/balanca/bd/comexstat-bd/ncm/(EXP|IMP)_(20\d{2})\.csv", item["url"])
        if not match:
            continue  # Outros períodos continuam na mesma lista de recibos.
        flow, year = match[1], int(match[2])
        if not FIRST_YEAR <= year <= LAST_YEAR:
            continue
        key = (flow, year)
        if key in receipts:
            raise ValueError(f"Recibo duplicado: {key}")
        if (not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", ""))
                or item.get("bytes", 0) <= 0
                or item.get("linhas_origem", 0) <= 0
                or item.get("linhas_recorte", 0) <= 0
                or item.get("referencia_inicial") != f"{year}-01"
                or item.get("referencia_final") != f"{year}-12"
                or item.get("urf") != 817700 or item.get("via") != 4):
            raise ValueError(f"Recibo não verificável ou incompleto: {key}")
        receipts[key] = item
    expected = {(flow, year) for year in range(FIRST_YEAR, LAST_YEAR + 1)
                for flow in ("EXP", "IMP")}
    if set(receipts) != expected:
        raise ValueError(f"Recibos faltantes: {sorted(expected - set(receipts))}")

    by_year = {}
    for year, official in MDIC_ANNUAL_REFERENCE.items():
        rows = [r for r in read_csv("brasil", root) if r["mes"].startswith(f"{year}-")]
        if len(rows) != 12:
            raise ValueError(f"Brasil {year}: esperado 12 competências")
        calculated = (math.fsum(r["exportacoes_usd_bi"] for r in rows),
                      math.fsum(r["importacoes_usd_bi"] for r in rows))
        errors = [round(value - expected_value, 8)
                  for value, expected_value in zip(calculated, official)]
        if max(abs(value) for value in errors) > MAX_ANNUAL_DIFF_USD_BI:
            raise ValueError(f"Brasil {year}: divergência frente à fonte oficial: {errors} US$ bi")
        by_year[str(year)] = {"exportacoes_usd_bi": round(calculated[0], 6),
                              "importacoes_usd_bi": round(calculated[1], 6),
                              "diferencas_fonte_usd_bi": errors}

    for row in read_csv("macro", root):
        if row["mes"] in months:
            if any(row[key] is None for key in ("selic_meta_pct_aa", "dolar_venda_medio_brl", "ipca_pct_mes")):
                raise ValueError(f"Macro {row['mes']}: série incompleta")

    cargo_present = {r["mes"] for r in read_csv("viracopos", root)}
    cargo_missing = sorted(months - cargo_present)
    cargo_status = ("completo" if not cargo_missing
                    else f"pendente: {len(cargo_missing)} meses operacionais em 2020–2024")
    return {
        "status": "integracao_parcial" if cargo_missing else "bases_2020_2024_completas",
        "anos": [FIRST_YEAR, LAST_YEAR],
        "meses_pareados_comex": 60,
        "recibos_mdic": len(receipts),
        "contagem_registros": counts,
        "conciliacao_mdic_anual": by_year,
        "carga_operacional": cargo_status,
        "nota": "CSV, JSON, recibos e agregados nacionais conferidos; nunca extrapolar validação física RMA a partir de MDIC."
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))

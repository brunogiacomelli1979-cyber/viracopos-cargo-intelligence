"""Diagnóstico persistente de execução ANAC incompleta, sem publicar dados parciais.

Lê os metadados das cinco tarefas anuais baixadas como artefatos da execução
corrente e grava relatório JSON em docs/ para facilitar a correção das falhas.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/staging/anac-downloads"
DEST = ROOT / "docs/anac-backfill-diagnostico.json"


def summarize(base=BASE):
    years = {}
    for year in range(2020, 2025):
        directory = base / f"anac-sbkp-{year}"
        receipt_path = directory / "anac_sbkp_fontes.json"
        csv_path = directory / "anac_sbkp_carga_mensal.csv"
        if not receipt_path.is_file():
            years[str(year)] = {
                "status": "artefato_ausente",
                "meses_ok": [],
                "falhas": [{"erro": "Recibo anual não disponível no artefato"}],
            }
            continue
        try:
            metadata = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipts = metadata.get("recibos", [])
            failures = metadata.get("falhas", [])
            months = [r["competencia"] for r in receipts]
            expected = [f"{year}-{month:02d}" for month in range(1, 13)]
            missing = sorted(set(expected) - set(months))
            status = "validado" if (
                metadata.get("status") == "validado"
                and len(receipts) == 12 and not failures
                and not missing and csv_path.is_file()
            ) else "incompleto"
            years[str(year)] = {
                "status": status,
                "meses_ok": sorted(months),
                "meses_faltantes": missing,
                "falhas": failures,
                "csv_agregado_presente": csv_path.is_file(),
                "etapas_sbkp_de_meses_ok": sum(r.get("etapas_sbkp", 0) for r in receipts),
            }
        except (ValueError, KeyError, TypeError) as error:
            years[str(year)] = {"status": "recibo_invalido", "meses_ok": [],
                                 "falhas": [{"erro": str(error)}]}
    return {
        "objetivo": "Auditoria de coleta ANAC SBKP 2020–2024",
        "fonte": "ANAC Etapa Básica — SBKP",
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "anos": years,
        "anos_validados": [int(y) for y, record in years.items()
                            if record["status"] == "validado"],
        "anos_pendentes": [int(y) for y, record in years.items()
                           if record["status"] != "validado"],
        "publicacao_habilitada": False,
        "nota": "Relatório técnico apenas. Não substituir série RMA nem divulgar valores incompletos.",
    }


def main():
    report = summarize()
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for year, item in report["anos"].items():
        print(f"{year}: {item['status']} — {len(item['meses_ok'])}/12 meses válidos")
        for failure in item.get("falhas", []):
            print("  ", failure)
    print(f"Relatório salvo em {DEST}")
    return report


if __name__ == "__main__":
    main()

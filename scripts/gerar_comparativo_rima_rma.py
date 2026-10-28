"""Gera comparativo exploratório RIMA/RMA e perfil de carga por movimento.

Usa somente arquivos locais validados; não baixa nem altera série principal.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from conciliar_rima_rma import reconcile, load_preliminary, load_rma
from validar_agrupamento_rima import validate

ROOT = Path(__file__).resolve().parents[1]
PAX_FIELDS = ("QT_PAX_LOCAL", "QT_PAX_CONEXAO_DOMESTICO", "QT_PAX_CONEXAO_INTERNACIONAL")


def measure(row):
    raw = row.get("QT_CARGA")
    if raw is None or not raw.strip():
        return "carga_indeterminada"
    try:
        n = Decimal(raw.replace(",", ".").strip())
    except InvalidOperation as exc:
        raise ValueError("QT_CARGA não numérica") from exc
    if not n.is_finite() or n < 0:
        raise ValueError("QT_CARGA negativa ou inválida")
    return "com_carga" if n > 0 else "sem_carga"


def pax_status(row):
    values = []
    for field in PAX_FIELDS:
        raw = row.get(field)
        if raw is None or not raw.strip():
            values.append(None)
            continue
        try:
            n = Decimal(raw.replace(",", ".").strip())
        except InvalidOperation as exc:
            raise ValueError(f"Quantidade de passageiros inválida: {field}") from exc
        if not n.is_finite() or n < 0 or n != n.to_integral_value():
            raise ValueError(f"Quantidade de passageiros inválida: {field}")
        values.append(n)
    if any(v is not None and v > 0 for v in values):
        return "com_passageiros"
    if all(v is not None for v in values):
        return "sem_passageiros_registrados"
    return "passageiros_indeterminados"


def profile_csv(csv_bytes, month):
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"), newline=""), delimiter=";", strict=True)
    required = {"ANO","MES","NR_AEROPORTO_REFERENCIA","NR_NATUREZA","NR_MOVIMENTO_TIPO",
                "QT_CARGA","NR_SERVICE_TYPE", *PAX_FIELDS}
    if not required.issubset(set(reader.fieldnames or [])):
        raise ValueError("Colunas insuficientes para classificar carga e passageiros")
    groups = {}
    for nature, name in (("D", "domestica"), ("I", "internacional")):
        groups[nature] = Counter()
    total = 0
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("Linha com quantidade incorreta de campos")
        if (row["NR_AEROPORTO_REFERENCIA"] != "SBKP"
                or f"{int(row['ANO']):04d}-{int(row['MES']):02d}" != month
                or row["NR_NATUREZA"] not in groups
                or row["NR_MOVIMENTO_TIPO"] not in ("P", "D")):
            raise ValueError("Movimento fora da competência/escopo")
        cargo = measure(row)
        pax = pax_status(row)
        counter = groups[row["NR_NATUREZA"]]
        counter["movimentos"] += 1
        counter[cargo] += 1
        counter[pax] += 1
        counter[f"{cargo}__{pax}"] += 1
        service = row["NR_SERVICE_TYPE"].strip() or "nao_informado"
        counter[f"service_type:{service}"] += 1
        total += 1
    result = {}
    for key, nature in (("D","domestica"),("I","internacional")):
        c = groups[key]
        if c["movimentos"] != c["com_carga"] + c["sem_carga"] + c["carga_indeterminada"]:
            raise ValueError("Movimentos não conciliados")
        result[nature] = dict(sorted(c.items()))
    return {"mes":month,"movimentos":total,"por_natureza":result,
            "criterio": "com_carga é QT_CARGA > 0, não implica importação/exportação. Passageiros baseados em QT_PAX_* disponíveis. Um voo de passageiros pode transportar carga.",
            "nao_e_fluxo_aduaneiro":True}


def generate(root=ROOT):
    report = validate(root)
    if report["resultado"] != "aprovado_tecnicamente":
        raise ValueError("Agregação RIMA incompleta")
    preliminary = load_preliminary(root / "docs/referencias/rma/rma_2024_01_preliminar.json")
    comparison = reconcile(report, load_rma(root/"data/viracopos.csv"), preliminary)
    entry = json.loads((root/"data/anac/rima/manifesto.json").read_text(encoding="utf-8"))["competencias"]["2024-01"]
    file = (root/entry["caminho_sbkp"]).resolve()
    if not file.is_relative_to((root/"data/anac/rima").resolve()):
        raise ValueError("Caminho inválido")
    binary = file.read_bytes()
    if hashlib.sha256(binary).hexdigest() != entry["sha256_sbkp_gzip"]:
        raise ValueError("Gzip ANAC adulterado")
    with gzip.open(file, "rb") as stream:
        data = stream.read(100_000_001)
    if len(data) > 100_000_000 or hashlib.sha256(data).hexdigest() != entry["conteudo_sbkp_sha256"]:
        raise ValueError("Conteúdo ANAC inválido")
    profile = profile_csv(data, "2024-01")
    if profile["movimentos"] != entry["linhas_sbkp"]:
        raise ValueError("Contagem total de movimentos diverge")
    item = comparison["comparacoes"]["2024-01"]
    if profile["por_natureza"]["domestica"]["movimentos"] != 8407 or profile["por_natureza"]["internacional"]["movimentos"] != 941:
        raise ValueError("Contagens não conferem com reconciliação RIMA")
    pairs = {
        "domestica": ("comparacao_domestica","movimentos_domesticos"),
        "internacional": ("comparacao_internacional","movimentos_internacionais"),
    }
    rows = []
    for nature,(cargo_key,movement_key) in pairs.items():
        cargo = item[cargo_key]
        movement = item[movement_key]
        if not cargo.get("comparavel") or not movement.get("comparavel"):
            raise ValueError("Referência sem valores suficientes")
        rows.append({
            "mes":"2024-01", "natureza":nature,
            "rima_carga_t":float(cargo["anac_t"]), "rma_carga_t":float(cargo["rma_t"]),
            "rima_movimentos":movement["anac"], "rma_movimentos":movement["rma"],
            "qualidade_rima":"conferido_sha256", "qualidade_rma":"transcricao_preliminar_pdf_nao_certificado",
            "rima_sha256":entry["sha256_sbkp_gzip"],
            "rma_url_pdf":preliminary["url_pdf"]
        })
    return {
        "versao":1, "status":"preliminar_com_divergencias",
        "recortes":rows,
        "perfil_voos":[profile],
        "atencao":"RMA janeiro/2024 transcrito de PDF ainda sem inspeção/hash; comparação exploratória e não equivalente ao Comex.",
        "cobertura":"Somente competências com duas fontes disponíveis; não preencher meses ausentes.",
        "sem_ajuste_de_diferenca":True,
        "liberado_para_indicadores":False
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--output",type=Path,required=True)
    args = p.parse_args()
    result = generate(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"resumo":"Gerado comparativo exploratório sem download",
                      "recortes":result["recortes"],
                      "perfil_voos":result["perfil_voos"]},ensure_ascii=False))


if __name__=="__main__":
    main()

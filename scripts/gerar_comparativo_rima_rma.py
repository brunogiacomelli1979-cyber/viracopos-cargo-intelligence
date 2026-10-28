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


def _verified_archive_bytes(root, entry):
    """Lê um extrato por competência com limites, caminho e hash conferidos."""
    archive_root = (root / "data/anac/rima").resolve()
    path = (root / entry["caminho_sbkp"]).resolve()
    if not path.is_relative_to(archive_root):
        raise ValueError("Caminho de extrato fora do acervo")
    compressed = path.read_bytes()
    if len(compressed) > 10_000_000 or len(compressed) != entry["bytes_sbkp_gzip"]:
        raise ValueError("Tamanho do arquivo ANAC inválido")
    if hashlib.sha256(compressed).hexdigest() != entry["sha256_sbkp_gzip"]:
        raise ValueError("SHA-256 do gzip ANAC divergente")
    with gzip.open(path, "rb") as stream:
        raw = stream.read(100_000_001)
    if len(raw) > 100_000_000 or hashlib.sha256(raw).hexdigest() != entry["conteudo_sbkp_sha256"]:
        raise ValueError("SHA-256 do conteúdo ANAC divergente")
    return raw


def _profile_all_months(root, report, manifest):
    """Não pressupõe janeiro/2024 nem presença de pares RMA."""
    profiles = []
    months = manifest["competencias"]
    if set(months) != set(report["comparacoes"]):
        raise ValueError("Manifesto e agregação validada não cobrem os mesmos meses")
    for month, entry in sorted(months.items()):
        profile = profile_csv(_verified_archive_bytes(root, entry), month)
        verified = report["comparacoes"][month]
        if profile["movimentos"] != entry["linhas_sbkp"] or profile["movimentos"] != verified["registros"]:
            raise ValueError(f"{month}: contagem SBKP difere do validador independente")
        for nature in ("domestica", "internacional"):
            group = profile["por_natureza"][nature]
            expected = sum(verified["grupos"][f"{nature}/{movement}"]["registros"]
                           for movement in ("pouso", "decolagem"))
            if group["movimentos"] != expected:
                raise ValueError(f"{month}/{nature}: movimentos não conciliam")
            if group["movimentos"] != sum(group.get(k, 0) for k in
                                          ("com_carga", "sem_carga", "carga_indeterminada")):
                raise ValueError(f"{month}/{nature}: perfil de carga incompleto")
        profile["sha256_sbkp_gzip"] = entry["sha256_sbkp_gzip"]
        profiles.append(profile)
    return profiles


def _number(value, *, integer=False):
    """Mantém ausência como None; não confunde dado inexistente com zero."""
    if value is None:
        return None
    return int(value) if integer else float(value)


def _month_sources(report, rma_current, preliminary, manifest):
    """Gera séries esparsas: ANAC 2020+ e RMA nos meses efetivamente disponíveis."""
    rima = report["comparacoes"]
    rma = dict(rma_current)
    if preliminary is not None:
        month = preliminary["mes"]
        if month in rma:
            raise ValueError("RMA preliminar sobrepõe série validada")
        rma[month] = {**preliminary, "status": "transcricao_preliminar_nao_certificada"}
    comparison = reconcile(report, rma_current, preliminary)
    series = []
    pairs = {"domestica": ("comparacao_domestica", "movimentos_domesticos", "carga_domestica_t"),
             "internacional": ("comparacao_internacional", "movimentos_internacionais", "carga_internacional_t")}
    for month in sorted(set(rima) | set(rma)):
        for nature,(cargo_key,movement_key,rma_field) in pairs.items():
            groups = rima[month]["grupos"] if month in rima else None
            src = rma.get(month)
            from conciliar_rima_rma import _anac_tonnes, _anac_movements
            at = _anac_tonnes(groups, nature) if groups else None
            am = _anac_movements(groups, nature) if groups else None
            rm = Decimal(src[rma_field]) if src else None
            rv = src.get(movement_key) if src else None
            series.append({
                "mes": month, "natureza": nature,
                "rima_carga_t": _number(at), "rma_carga_t": _number(rm),
                "rima_movimentos": am, "rma_movimentos": rv,
                "qualidade_rima": "conferido_sha256" if groups else "nao_disponivel",
                "qualidade_rma": ("transcricao_preliminar_pdf_nao_certificado"
                                  if src and src.get("status") == "transcricao_preliminar_nao_certificada"
                                  else "serie_rma_dashboard" if src else "nao_disponivel"),
                "rima_sha256": manifest["competencias"][month]["sha256_sbkp_gzip"] if groups else None,
                "rma_url_pdf": src.get("url_pdf") if src else None,
            })
    recortes = []
    for row in series:
        if row["rima_carga_t"] is not None and row["rma_carga_t"] is not None:
            recortes.append(row)
    return series, recortes, comparison


def generate(root=ROOT):
    report = validate(root)
    if report["resultado"] != "aprovado_tecnicamente" or report["erros"]:
        raise ValueError("Agregação RIMA incompleta")
    manifest = json.loads((root/"data/anac/rima/manifesto.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "anac_rima_sbkp_v1" or manifest.get("aeroporto") != "SBKP":
        raise ValueError("Manifesto incompatível")
    current = load_rma(root/"data/viracopos.csv")
    preliminary_file = root/"docs/referencias/rma/rma_2024_01_preliminar.json"
    preliminary = load_preliminary(preliminary_file) if preliminary_file.exists() else None
    profiles = _profile_all_months(root, report, manifest)
    series, rows, comparison = _month_sources(report, current, preliminary, manifest)
    if len(profiles) != len(manifest["competencias"]):
        raise ValueError("Alguma competência ANAC não recebeu perfil")
    return {
        "versao": 2,
        "status": "preliminar_com_divergencias" if preliminary else "fontes_em_paralelo",
        "recortes": rows,
        "serie_mensal": series,
        "perfil_voos": profiles,
        "meses_anac": len(profiles),
        "meses_com_duas_fontes": len({x["mes"] for x in rows}),
        "atencao": "Fontes distintas e dados esparsos; RMA 2024 em transcrição preliminar sem PDF integral verificado.",
        "cobertura": "Só meses efetivamente observados, nenhum preenchimento ou extrapolação.",
        "sem_ajuste_de_diferenca": True,
        "liberado_para_indicadores": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--output",type=Path,required=True)
    args = p.parse_args()
    result = generate(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("COMPARATIVO_JSON=" + json.dumps(result, ensure_ascii=False, separators=(",",":")))
    print(json.dumps({"resumo":"Gerado comparativo exploratório sem download",
                      "recortes":result["recortes"],
                      "perfil_voos":result["perfil_voos"]},ensure_ascii=False))


if __name__=="__main__":
    main()

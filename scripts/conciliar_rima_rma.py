"""Conciliação exploratória ANAC/RIMA versus RMA da concessionária.

Somente leitura. Nunca publica dados ou compara meses diferentes.
Documentos RMA não verificados fisicamente são sempre não-certificados.
"""

import argparse
import csv
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from validar_agrupamento_rima import validate

ROOT = Path(__file__).resolve().parents[1]
RMA_FIELDS = ("carga_domestica_t", "carga_internacional_t",
              "courier_internacional_t")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _month(month):
    if not isinstance(month, str) or not MONTH_RE.fullmatch(month) or month < "2020-01":
        raise ValueError(f"Competência inválida ou anterior ao recorte 2020: {month!r}")
    return month


def _weight(text, source, *, allow_zero=True):
    if text is None or str(text).strip() == "":
        raise ValueError(f"Medida {source} ausente: não imputar zero")
    try:
        raw = str(text).strip()
        if not re.fullmatch(r"\d+(?:\.\d+)?", raw):
            raise ValueError("número fora do formato decimal canônico")
        amount = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Medida {source} inválida: {text!r}") from exc
    if not amount.is_finite() or amount < 0 or (amount == 0 and not allow_zero):
        raise ValueError(f"Medida {source} inválida")
    return amount


def load_rma(path):
    """Leitura estrita do RMA já validado no dashboard, sem preenchimento de lacunas."""
    months = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        if set(reader.fieldnames or ()) != {"mes", *RMA_FIELDS}:
            raise ValueError("Contrato CSV RMA divergente")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Número de colunas RMA inválido")
            month = _month(row["mes"])
            if month in months:
                raise ValueError(f"Duplicata de competência RMA: {month}")
            months[month] = {
                "mes": month,
                "fonte": "RMA_concessionaria_dashboard",
                "verificacao_pdf_completa": True,
                "status": "rma_painel_atual",
                **{key: str(_weight(row[key], key)) for key in RMA_FIELDS},
            }
    if not months:
        raise ValueError("CSV RMA vazio")
    return months


def load_preliminary(path):
    """Permite comparação apenas marcada como prévia e nunca publicável."""
    if path is None:
        return None
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    month = _month(obj.get("mes"))
    url = obj.get("url_pdf", "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ("www.viracopos.com", "viracopos.com") or not parsed.path.lower().endswith(".pdf"):
        raise ValueError("Referência RMA não aponta para PDF oficial HTTPS da concessionária")
    if obj.get("verificacao_pdf_completa") is not False or obj.get("sha256_pdf") is not None:
        raise ValueError("Referência preliminar deve declarar PDF sem hash e não verificado")
    if obj.get("status") != "transcricao_preliminar_nao_certificada":
        raise ValueError("Status da referência preliminar inesperado")
    for field in RMA_FIELDS:
        _weight(obj.get(field), field)
    counts = ("movimentos_domesticos", "movimentos_internacionais")
    if any(key in obj for key in counts):
        if not all(key in obj for key in counts):
            raise ValueError("Contagens RMA precisam ser fornecidas juntas")
        for key in counts:
            _movement_count(obj[key], key)
    return obj


def _movement_count(value, source):
    if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value)):
        raise ValueError(f"Contagem de movimentos {source} inválida")
    return int(value)


def _anac_movements(groups, nature):
    total = 0
    for movement in ("pouso", "decolagem"):
        group = groups.get(f"{nature}/{movement}")
        if group is None or not isinstance(group.get("registros"), int) or group["registros"] < 0:
            return None
        total += group["registros"]
    return total


def _compare_movements(anac_count, rma_count):
    if anac_count is None:
        return {"comparavel": False, "motivo": "contagem ANAC ausente"}
    if rma_count is None:
        return {"comparavel": False, "motivo": "contagem RMA não informada"}
    rma = _movement_count(rma_count, "RMA")
    return {"comparavel": True, "anac": anac_count, "rma": rma,
            "diferenca": anac_count-rma,
            "alerta": "contagens_divergentes" if anac_count != rma else "contagens_iguais_nao_comprovam_conciliacao"}


def _anac_tonnes(groups, nature):
    values = []
    for movement in ("pouso", "decolagem"):
        group = groups.get(f"{nature}/{movement}")
        if not group or group.get("status") != "completo":
            return None
        number = group.get("carga_kg")
        if number is None:
            return None
        values.append(_weight(number, f"ANAC {nature}/{movement}") )
    return sum(values, Decimal(0)) / Decimal(1000)


def _compare(anac_t, rma_t):
    if anac_t is None:
        return {"comparavel": False, "motivo": "grupo ANAC incompleto"}
    rma = _weight(rma_t, "RMA", allow_zero=True)
    diff = anac_t - rma
    # RMA em toneladas inteiras. Sem garantir regra de arredondamento, sinalizar
    # somente magnitude, nunca validar igualdade de universos.
    return {
        "comparavel": True,
        "anac_t": format(anac_t, "f"),
        "rma_t": format(rma, "f"),
        "diferenca_t": format(diff, "f"),
        "diferenca_pct_sobre_rma": (format(diff * 100 / rma, ".4f") if rma else None),
        "alerta": ("discrepancia_acima_de_meia_tonelada" if abs(diff) > Decimal("0.5")
                   else "diferenca_ate_meia_tonelada_nao_prova_equivalencia"),
    }


def reconcile(rima_report, rma_current, preliminary=None):
    """Alinha pelo mês; nunca junta eventos RIMA às linhas aduaneiras."""
    if rima_report.get("resultado") != "aprovado_tecnicamente" or rima_report.get("erros"):
        raise ValueError("RIMA sem validação técnica completa")
    rima = rima_report.get("comparacoes", {})
    if not rima:
        raise ValueError("Nenhum período ANAC validado")
    rma = dict(rma_current)
    preliminary_months = []
    if preliminary:
        month = _month(preliminary["mes"])
        if month in rma:
            raise ValueError("Referência preliminar conflita com RMA já validado")
        rma[month] = {**preliminary, "fonte": "RMA_pdf_transcricao_preliminar"}
        preliminary_months.append(month)

    overlapping = sorted(set(rma) & set(rima))
    summary = {
        "janela_anac": [min(rima), max(rima)],
        "janela_rma": [min(rma), max(rma)],
        "meses_anac_validados": len(rima),
        "meses_rma_disponiveis": len(rma),
        "meses_coincidentes": len(overlapping),
        "meses_com_referencia_preliminar": preliminary_months,
        "comparacoes": {},
        "alertas": [],
        "liberado_dashboard": False,
        "liberado_modelagem": False,
        "criterio": "Mesmo aeroporto e competência; RMA/RIMA do operador têm obrigação regulatória comum, mas versões e critérios de contabilização exigem conciliação documental."
    }
    for month in overlapping:
        groups = rima[month]["grupos"]
        src = rma[month]
        provisional = src["status"] == "transcricao_preliminar_nao_certificada"
        result = {
            "rma_fonte": src["fonte"],
            "referencia_pdf_verificada": not provisional,
            "relacao_regulatoria": "RMA e RIMA são apresentados pelo operador à ANAC sob a Resolução 464/2018; classificação, datas, publicação e revisões devem ser reconciliadas",
            "comparacao_domestica": _compare(_anac_tonnes(groups, "domestica"), src["carga_domestica_t"]),
            "comparacao_internacional": _compare(_anac_tonnes(groups, "internacional"), src["carga_internacional_t"]),
            "movimentos_domesticos": _compare_movements(
                _anac_movements(groups, "domestica"), src.get("movimentos_domesticos")),
            "movimentos_internacionais": _compare_movements(
                _anac_movements(groups, "internacional"), src.get("movimentos_internacionais")),
            "courier_rma_t_nao_comparado_ao_correio_anac": src["courier_internacional_t"],
            "status": ("preliminar_nao_publicavel" if provisional else "diferencas_a_reconciliar_metodologicamente"),
        }
        for nature in ("domestica", "internacional"):
            if result[f"comparacao_{nature}"].get("alerta", "").startswith("discrepancia"):
                summary["alertas"].append({"mes": month, "natureza": nature,
                                           "tipo": "divergencia_fisica_conceitual_a_investigar"})
        for nature in ("domesticos", "internacionais"):
            if result[f"movimentos_{nature}"].get("alerta") == "contagens_divergentes":
                summary["alertas"].append({
                    "mes": month, "natureza": nature,
                    "tipo": "movimentos_RIMA_RMA_divergentes_revisao_a_investigar"
                })
        summary["comparacoes"][month] = result
    summary["situacao"] = (
        "sem_mes_coincidente" if not overlapping
        else "apenas_confronto_preliminar" if any(m in overlapping for m in preliminary_months)
        else "comparacao_disponivel_metodologia_nao_conciliada")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Confronto offline RIMA/RMA, não publicável")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--rma-csv", type=Path)
    parser.add_argument("--referencia-preliminar", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    rima = validate(root)
    rma = load_rma(args.rma_csv or root / "data/viracopos.csv")
    provisional = load_preliminary(args.referencia_preliminar)
    report = reconcile(rima, rma, provisional)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()

"""Auditoria estatística reproduzível de VCP Insights (sem extrapolação causal).

Somente biblioteca padrão. A auditoria é informativa: nunca gera previsões
quando a amostra, a continuidade mensal ou o protocolo não forem suficientes.
"""
import argparse
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

from validar_dados import ROOT, validate_project


def month_index(month):
    year, m = map(int, month.split("-"))
    return year * 12 + m - 1


def next_month(month):
    index = month_index(month) + 1
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def monthly_profile(rows, field):
    """Métricas descritivas em observações mensais válidas e sem duplicatas."""
    observations = [(r["mes"], r[field]) for r in rows if isinstance(r.get(field), (int, float))
                    and not isinstance(r.get(field), bool) and math.isfinite(r[field])]
    observations.sort()
    months = [m for m, _ in observations]
    if len(months) != len(set(months)):
        raise ValueError(f"{field}: meses duplicados")
    if not observations:
        return {"n": 0, "primeiro": None, "ultimo": None, "lacunas": [],
                "media": None, "desvio_padrao_amostral": None, "cv_pct": None}
    by_month = dict(observations)
    missing = []
    cursor = months[0]
    while month_index(cursor) <= month_index(months[-1]):
        if cursor not in by_month:
            missing.append(cursor)
        cursor = next_month(cursor)
    values = list(by_month.values())
    avg = sum(values) / len(values)
    sd = (math.sqrt(sum((v-avg)**2 for v in values)/(len(values)-1))
          if len(values) > 1 else None)
    return {"n": len(values), "primeiro": months[0], "ultimo": months[-1],
            "lacunas": missing, "media": round(avg, 4),
            "desvio_padrao_amostral": round(sd, 4) if sd is not None else None,
            "cv_pct": round(100 * sd / avg, 4) if sd is not None and avg else None}


def same_month_yoy(rows, field):
    by_month = {r["mes"]: r.get(field) for r in rows}
    result = []
    for month in sorted(by_month):
        year = int(month[:4]) - 1
        prior = f"{year:04d}{month[4:]}"
        x, base = by_month[month], by_month.get(prior)
        if isinstance(x, (int, float)) and isinstance(base, (int, float)) and base != 0:
            result.append({"mes": month, "comparacao": prior, "variacao_pct": round(100*(x/base-1), 4)})
    return result


def matched_ytd(rows, field, year):
    """Acumulado comparável apenas para pares completos desde janeiro."""
    by_month = {r["mes"]: r.get(field) for r in rows}
    current, prior = [], []
    month = 1
    while month <= 12:
        a, b = f"{year:04d}-{month:02d}", f"{year-1:04d}-{month:02d}"
        if a not in by_month or b not in by_month:
            break
        current.append(by_month[a]); prior.append(by_month[b])
        month += 1
    if not current or any(not isinstance(v, (int, float)) for v in current + prior):
        return None
    if sum(prior) == 0:
        return None
    return {"ano": year, "meses_pareados": len(current), "fim": f"{year:04d}-{month-1:02d}",
            "total_ano_t": round(sum(current), 4), "total_ano_anterior_t": round(sum(prior), 4),
            "variacao_pct": round(100*(sum(current)/sum(prior)-1), 4)}


def rolling_benchmark(rows, field, mode="naive", horizon=1,
                      min_train=24, min_test=12):
    """Backtest temporal de h=1, origens crescentes, sem olhar o mês previsto.

    O benchmark sazonal precisa também de no mínimo 36 observações de treino.
    Mínimos são guardrails do projeto, não teoremas universais.
    """
    if horizon != 1:
        raise ValueError("A implementação avalia somente horizonte de um mês")
    if mode not in ("naive", "seasonal_naive"):
        raise ValueError("Benchmark desconhecido")
    if mode == "seasonal_naive":
        min_train = max(36, min_train)
    p = monthly_profile(rows, field)
    if p["lacunas"] or p["n"] < min_train + min_test:
        return {"status": "bloqueado", "motivo": "histórico insuficiente ou com lacunas",
                "n": p["n"], "minimo_exigido": min_train + min_test,
                "lacunas": p["lacunas"], "metodo": mode, "horizonte_meses": horizon}
    ordered = sorted(rows, key=lambda r: r["mes"])
    values = [r[field] for r in ordered]
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or
           not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("Série do benchmark contém valores inválidos")
    folds = []
    # Cada previsão usa apenas valores com índice inferior ao mês-alvo.
    for i in range(min_train, len(values)):
        predicted = values[i - 1] if mode == "naive" else values[i - 12]
        folds.append({"mes": ordered[i]["mes"], "previsao": predicted, "realizado": values[i],
                      "origem": ordered[i-1]["mes"]})
    errors = [r["previsao"] - r["realizado"] for r in folds]
    mae = sum(abs(e) for e in errors)/len(errors)
    rmse = math.sqrt(sum(e**2 for e in errors)/len(errors))
    denominator = sum(abs(r["realizado"]) for r in folds)
    return {"status": "avaliacao_retroativa", "metodo": mode, "horizonte_meses": 1,
            "treino_inicial_meses": min_train, "dobras": len(folds),
            "inicio_teste": folds[0]["mes"], "fim_teste": folds[-1]["mes"],
            "mae": round(mae, 4), "rmse": round(rmse, 4),
            "wape_pct": round(100*sum(abs(e) for e in errors)/denominator, 4)
            if denominator else None,
            "observacao": "Diagnóstico de referência, não validação causal nem previsão publicada."}


def audit(snapshot):
    sources = snapshot["metadados"]
    cargo_meta = sources["viracopos"]
    if "RMA" not in cargo_meta.get("fonte_nome", ""):
        raise ValueError("Fonte operacional não identificada como RMA")
    if "concessionária" not in cargo_meta["abrangencia"].lower():
        raise ValueError("Abrangência operacional sem identificação da concessionária")
    comex_meta = sources["comex"]
    if not comex_meta.get("recorte_validado"):
        raise ValueError("Recorte da URF e da via aérea não validado")
    if str(comex_meta.get("recorte", {}).get("urf", {}).get("CO_URF", "")) != "0817700":
        raise ValueError("Código da URF difere do contrato")
    if str(comex_meta.get("recorte", {}).get("via", {}).get("CO_VIA", "")) != "04":
        raise ValueError("Código da via difere do contrato")
    cargo = snapshot["viracopos"]
    yoy = same_month_yoy(cargo, "carga_internacional_t")
    ytd = matched_ytd(cargo, "carga_internacional_t", int(cargo[-1]["mes"][:4])) if cargo else None
    p = monthly_profile(cargo, "carga_internacional_t")
    data_count = {name: len(snapshot[name]) for name in ("viracopos", "comex", "brasil", "macro")}
    months = defaultdict(set)
    for row in snapshot["comex"]:
        months[row["mes"]].add(row["fluxo"])
    incomplete_flows = [month for month, values in sorted(months.items())
                        if values != {"importacao", "exportacao"}]
    diagnostics = {
        "carga_internacional": p,
        "ultimo_yoy": yoy[-1] if yoy else None,
        "acumulado_pareado": ytd,
        "fontes_linhas": data_count,
        "comex_competencias_sem_ambos_fluxos": incomplete_flows,
        "benchmark_ingenuo": rolling_benchmark(cargo, "carga_internacional_t"),
        "benchmark_sazonal": rolling_benchmark(cargo, "carga_internacional_t", mode="seasonal_naive"),
    }
    forecasting_ready = diagnostics["benchmark_ingenuo"]["status"] == "avaliacao_retroativa" and diagnostics["benchmark_sazonal"]["status"] == "avaliacao_retroativa"
    return {
        "protocolo": "VCP-SCI-01", "versao": 1,
        "competencia_carga": p["ultimo"],
        "status_metodologico": "apto_a_avaliacao_de_benchmarks" if forecasting_ready else "descritivo_apenas",
        "previsao_validada": False,
        "correlacao_causal_demonstrada": False,
        "diagnosticos": diagnostics,
        "restricoes": [
            "Séries com abrangências físicas e aduaneiras distintas não são diretamente reconciliáveis.",
            "Correlação entre níveis seriados não comprova causalidade; não divulgar p-valores sem investigar autocorrelação/estacionariedade.",
            "Indicadores econômicos como preditores exigem calendário de disponibilidade observado na origem da previsão.",
            "Backtesting é retrospectivo e necessita origem móvel temporal, comparações e diagnóstico de erros."
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, help="Salvar diagnóstico JSON em caminho escolhido")
    args = parser.parse_args()
    validate_project(args.root)
    snapshot = json.loads((args.root/"data/dashboard.json").read_text(encoding="utf-8"))
    result = audit(snapshot)
    encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()

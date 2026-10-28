"""ANAC-04 — examina excecoes de toque sem expor identificadores.

Somente arquivos RIMA/SBKP ja arquivados, previamente auditados. Nao baixa,
nao altera o manifesto, nao remove nenhuma linha e nao publica indicadores.
Fonte normativa: Portaria 1.017/SRA/SIA/2018 (compilada com alteracao de
2019), art. 8, paragrafo 1: mes do RIMA segue calco/descalco, nao toque.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from perfilar_qualidade_anac04 import ROOT, LIMIT, profile_archive

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d",
                "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S")
DIFFERENT_FIELDS = (
    "NR_VOO_NUMERO", "NR_VOO_OUTRO_AEROPORTO", "NR_AERONAVE_OPERADOR",
    "NR_AERONAVE_TIPO", "NR_SERVICE_TYPE", "DT_CALCO", "HH_CALCO",
    "QT_CARGA", "QT_CORREIO",
)
# Codigos IATA divulgados no dicionario ANAC; Y/Z na Portaria 1017/2018,
# alterada pela Portaria 2176/2019. Nenhum codigo implica necessariamente
# que uma linha com carga positiva representa voo exclusivamente cargueiro.
SERVICE_GROUPS = {
    "J": "passageiro_programado",
    "S": "passageiro_programado",
    "U": "passageiro_programado",
    "F": "passageiro_programado_com_carga",
    "V": "passageiro_programado",
    "M": "correio_programado",
    "Q": "misto_programado",
    "G": "passageiro_adicional",
    "B": "passageiro_adicional",
    "A": "carga_correio_adicional",
    "R": "misto_adicional",
    "C": "passageiro_charter",
    "O": "charter_especial",
    "H": "carga_correio_charter",
    "L": "misto_charter",
    "P": "posicionamento_ou_sem_receita",
    "T": "teste_tecnico",
    "K": "treinamento",
    "D": "aviacao_geral",
    "E": "governamental",
    "W": "militar",
    "X": "parada_tecnica",
    "I": "estado_diplomatico_ambulancia",
    "N": "aviacao_executiva_taxi_aereo",
    "Y": "voo_alternado_portaria",
    "Z": "voo_retorno_portaria",
}


def parse_date(value):
    value = (value or "").strip()
    if not value or value.lower() == "null":
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError("Data operacional nao reconhecida")


def parse_hour(value):
    value = (value or "").strip()
    if not value or value.lower() == "null":
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def _delta(row):
    """Minutos calco-toque (pouso) ou toque-descalco (decolagem)."""
    calco, toque = parse_date(row["DT_CALCO"]), parse_date(row["DT_TOQUE"])
    hh_calco, hh_toque = parse_hour(row["HH_CALCO"]), parse_hour(row["HH_TOQUE"])
    if None in (calco, toque, hh_calco, hh_toque):
        return None
    a = datetime.combine(calco, hh_calco)
    b = datetime.combine(toque, hh_toque)
    return round(((a-b) if row["NR_MOVIMENTO_TIPO"] == "P" else (b-a)).total_seconds()/60, 3)


def _duration_bucket(minutes):
    if minutes is None:
        return "duracao_nao_verificavel"
    if minutes < 0:
        return "sequencia_temporal_negativa_a_investigar"
    if minutes <= 120:
        return "diferenca_ate_120_minutos"
    if minutes <= 360:
        return "diferenca_121_a_360_minutos"
    return "diferenca_acima_360_minutos_a_investigar"


def inspect_csv(data, month):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""),
                            delimiter=";", strict=True)
    header = reader.fieldnames or []
    required = {"ANO", "MES", "NR_AEROPORTO_REFERENCIA", "NR_MOVIMENTO_TIPO",
                "NR_NATUREZA", "DT_CALCO", "HH_CALCO", "DT_TOQUE", "HH_TOQUE",
                "NR_AERONAVE_MARCAS", "NR_SERVICE_TYPE"}
    if not required.issubset(header) or len(set(header)) != len(header):
        raise ValueError("Layout de datas/chaves insuficiente para auditoria normativa")
    calco_status = Counter()
    toque_status = Counter()
    duracao = Counter()
    distance_days = Counter()
    outside_service = Counter()
    outside_movement = Counter()
    services = Counter()
    collision_details = []
    collisions_by_month = Counter()
    seen = {}
    n = 0
    for row in reader:
        n += 1
        if None in row or any(v is None for v in row.values()):
            raise ValueError("Linha inconsistente no CSV")
        if row["NR_AEROPORTO_REFERENCIA"] != "SBKP" or (row["ANO"]+"-"+row["MES"].zfill(2)) != month:
            raise ValueError("Aeroporto/mes divergente")
        move = row["NR_MOVIMENTO_TIPO"].strip()
        nature = row["NR_NATUREZA"].strip()
        if move not in ("P", "D") or nature not in ("D", "I"):
            raise ValueError("Categoria ANAC inesperada")
        service = row["NR_SERVICE_TYPE"].strip()
        services[service] += 1
        calco, toque = parse_date(row["DT_CALCO"]), parse_date(row["DT_TOQUE"])
        if calco is None:
            calco_status["nao_informado"] += 1
        elif calco.strftime("%Y-%m") != month:
            calco_status["fora_da_competencia"] += 1
        else:
            calco_status["na_competencia"] += 1
        if toque is None:
            toque_status["nao_informado"] += 1
        elif toque.strftime("%Y-%m") != month:
            toque_status["fora_da_competencia"] += 1
            outside_service[service] += 1
            outside_movement[move] += 1
            if calco:
                distance_days[str((toque-calco).days)] += 1
            duracao[_duration_bucket(_delta(row))] += 1
        else:
            toque_status["na_competencia"] += 1
        if toque is not None and row["NR_AERONAVE_MARCAS"].strip() and row["HH_TOQUE"].strip() not in ("", "null"):
            key = (nature, move, row["NR_AERONAVE_MARCAS"].strip(),
                   row["DT_TOQUE"].strip(), row["HH_TOQUE"].strip())
            old = seen.get(key)
            if old is None:
                seen[key] = row
            else:
                collisions_by_month["com_data_toque_reconhecida"] += 1
                diff = [field for field in DIFFERENT_FIELDS if field in row and row[field] != old[field]]
                # Nenhuma matricula, numero de voo, data/hora exata ou valor
                # de carga e reportado. Somente campos que divergiram.
                collision_details.append({
                    "competencia": month,
                    "campos_distintos": diff,
                    "campos_distintos_quantidade": len(diff),
                    "valores_de_carga_diferem": "QT_CARGA" in diff,
                    "calco_difere": "DT_CALCO" in diff or "HH_CALCO" in diff,
                    "tipo_de_servico_difere": "NR_SERVICE_TYPE" in diff,
                    "interpretacao": "chave candidata coincidente; identidade de movimento nao certificada"
                })
    unknown_services = {k: v for k, v in services.items() if k not in SERVICE_GROUPS}
    known_groups = Counter()
    for code, total in services.items():
        known_groups[SERVICE_GROUPS.get(code, "codigo_nao_mapeado")] += total
    return {
        "competencia": month,
        "registros": n,
        "calco_norma": dict(calco_status),
        "toque_status": dict(toque_status),
        "toque_fora_mes_por_tipo_movimento": dict(sorted(outside_movement.items())),
        "toque_fora_mes_por_servico": dict(sorted(outside_service.items())),
        "toque_fora_mes_diferenca_dias_toque_menos_calco": dict(sorted(distance_days.items())),
        "toque_fora_mes_duracao_operacional": dict(sorted(duracao.items())),
        "colisoes_toque_com_data_reconhecida": collisions_by_month["com_data_toque_reconhecida"],
        "colisoes_perfil_anonimizado": collision_details,
        "service_type_codes": dict(sorted(services.items())),
        "service_type_grupos_descritivos": dict(sorted(known_groups.items())),
        "service_type_nao_mapeados": dict(sorted(unknown_services.items())),
        "norma_competencia_calco_respeitada": (
            n > 0 and calco_status["na_competencia"] == n
        ),
        "nenhum_registro_excluido": True,
    }


def inspect_archive(root=ROOT):
    root = Path(root).resolve()
    base = profile_archive(root)  # faz auditoria de hashes, grupos e duplicatas
    manifest = json.loads((root / "data/anac/rima/manifesto.json").read_text(encoding="utf-8"))
    monthly = {}
    for month, meta in sorted(manifest["competencias"].items()):
        path = (root / meta["caminho_sbkp"]).resolve()
        if not path.is_relative_to((root / "data/anac/rima").resolve()) or path.stat().st_size > 10_000_000:
            raise ValueError("Caminho fora do acervo ou gzip excessivo")
        with gzip.open(path, "rb") as fh:
            raw = fh.read(LIMIT+1)
        if len(raw) > LIMIT or hashlib.sha256(raw).hexdigest() != meta["conteudo_sbkp_sha256"]:
            raise ValueError("Hash do CSV em conflito")
        item = inspect_csv(raw, month)
        q = base["perfis"][month]
        if item["registros"] != q["registros_movimentacao"]:
            raise ValueError("Contagem de movimentos diverge")
        if (item["toque_status"].get("fora_da_competencia",0) !=
            q["datas_operacionais"]["DT_TOQUE"].get("fora_da_competencia",0)):
            raise ValueError("Datas fora de mes divergem do auditor anterior")
        if (item["colisoes_toque_com_data_reconhecida"] !=
            q["chaves_operacionais_candidatas"]["toque"]["colisoes_com_data_reconhecida"]):
            raise ValueError("Colisoes divergem do auditor anterior")
        monthly[month] = item
    return {
        "schema": "anac04-excecoes-norma-v1",
        "fonte": "Portaria ANAC 1017/2018 compilada, alterada em 2019; metadados ANAC",
        "regra_mes": "RIMA usa calco no pouso e descalco na decolagem, nao o toque",
        "competencias": monthly,
        "total_registros": sum(item["registros"] for item in monthly.values()),
        "total_toque_fora_mes": sum(item["toque_status"].get("fora_da_competencia",0) for item in monthly.values()),
        "total_toque_nao_informado": sum(item["toque_status"].get("nao_informado",0) for item in monthly.values()),
        "total_colisoes_toque_data_reconhecida": sum(item["colisoes_toque_com_data_reconhecida"] for item in monthly.values()),
        "total_calco_fora_mes": sum(item["calco_norma"].get("fora_da_competencia",0) for item in monthly.values()),
        "todos_calcos_no_mes": all(item["norma_competencia_calco_respeitada"] for item in monthly.values()),
        "nao_liberado_para_publicacao": True,
        "nao_liberado_para_nova_coleta": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = inspect_archive(args.root)
    out = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()

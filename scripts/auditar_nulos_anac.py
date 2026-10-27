"""Auditoria pontual dos campos de peso ausentes nos arquivos públicos ANAC.

Não atribui zeros nem publica tonelagens. Registra quantidades por campo e
o contexto técnico mínimo de cada linha incompleta para revisão.
"""
import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from coletar_anac_sbkp import FIELDS, get_bytes, norm, url_for

DEFAULT_MONTHS = ("2020-02", "2020-10", "2021-08", "2023-07")


def audit_month(month, fetcher=get_bytes):
    raw=fetcher(url_for(month), timeout=120)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members=[x for x in archive.infolist()
                 if not x.is_dir() and x.filename.lower().endswith((".csv",".txt"))]
        if len(members)!=1:
            raise ValueError(f"{month}: arquivos de dados encontrados: {len(members)}")
        if members[0].file_size>450_000_000:
            raise ValueError("Arquivo expandido excede limite")
        content=archive.read(members[0])
    reader=csv.DictReader(io.StringIO(content.decode("latin-1")),delimiter=";")
    required={"sg_icao_origem","sg_icao_destino","ds_natureza_etapa"}|set(FIELDS)
    if not required<=set(reader.fieldnames or []):
        raise ValueError(f"{month}: esquema inesperado")
    cases=[]
    sbkp=0
    for line_number,row in enumerate(reader,start=2):
        orig,dest=norm(row["sg_icao_origem"]),norm(row["sg_icao_destino"])
        if orig!="SBKP" and dest!="SBKP":
            continue
        sbkp+=1
        blanks=[name for name in FIELDS if not (row[name] or "").strip()]
        if not blanks:
            continue
        cases.append({"linha_fonte":line_number,
                      "origem_icao":orig,"destino_icao":dest,
                      "natureza":row.get("ds_natureza_etapa",""),
                      "grupo_voo":row.get("ds_grupo_di","") or row.get("ds_grupo_voo",""),
                      "campos_vazios":blanks,
                      "campos_presentes":{k:row[k] for k in FIELDS if k not in blanks},
                      "aeronave_ou_cia":row.get("sg_icao_empresa_aerea",""),
                      "etapa_local":orig==dest=="SBKP"})
    counts=Counter(key for case in cases for key in case["campos_vazios"])
    return {"mes":month,"url":url_for(month),
            "sha256_zip":hashlib.sha256(raw).hexdigest(),
            "sha256_dados":hashlib.sha256(content).hexdigest(),
            "etapas_sbkp":sbkp,"etapas_campos_ausentes":len(cases),
            "ausencia_por_medida":dict(sorted(counts.items())),
            "linhas_para_revisao":cases}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("meses", nargs="*", default=list(DEFAULT_MONTHS))
    p.add_argument("--output",type=Path,
                   default=Path("docs/anac-auditoria-campos-ausentes.json"))
    args=p.parse_args()
    findings=[]
    for month in args.meses:
        findings.append(audit_month(month))
        print(month, findings[-1]["etapas_sbkp"],
              findings[-1]["etapas_campos_ausentes"],
              findings[-1]["ausencia_por_medida"],flush=True)
    result={"fonte":"ANAC Etapa Básica — arquivos públicos",
            "gerado_em_utc":datetime.now(timezone.utc).isoformat(),
            "interpretacao":"Campo vazio não foi substituído por zero",
            "meses":findings}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
    print("Gravado",args.output)


if __name__=="__main__":
    main()

"""Etapa 1: arquivar documentação oficial ANAC, sem tocar nos dados.

Baixa PDFs/HTML da ANAC com HTTPS verificado, checa assinatura/conteúdo,
salva SHA-256, URI final e status de cada documento. Falha fechada para os
documentos essenciais; documentos complementares podem permanecer pendentes.
"""
import hashlib
import json
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/referencias/anac/originais"
CATALOG = ROOT / "docs/referencias/anac/manifesto.json"
SOURCES = [
    {
        "id": "metadados_etapa_basica", "type": "html", "essential": True,
        "file": "01_metadados_etapa_basica.html",
        "check": "Etapa Básica",
        "url": "https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/dados-estatisticos-do-transporte-aereo/48-dados-estatisticos-do-transporte-aereo",
    },
    {
        "id": "resolucao_191_2011", "type": "html", "essential": True,
        "file": "02_resolucao_191_2011.html",
        "check": "RESOLUÇÃO",
        "url": "https://www.anac.gov.br/assuntos/legislacao/legislacao-1/resolucoes/resolucoes-2011/resolucao-no-191-de-16-06-2011",
    },
    {
        "id": "portaria_3506_2019_compilada", "type": "pdf", "essential": True,
        "file": "03_portaria_3506_2019_compilada.pdf",
        "url": "https://www.anac.gov.br/assuntos/legislacao/legislacao-1/portarias/2019/portaria-no-3506-sas-11-11-2019/@@display-file/arquivo_norma/PA2019-3506.pdf",
    },
    {
        "id": "portaria_3507_2019_compilada", "type": "pdf", "essential": True,
        "file": "04_portaria_3507_2019_compilada.pdf",
        "url": "https://www.anac.gov.br/assuntos/legislacao/legislacao-1/portarias/2019/portaria-no-3507-sas-11-11-2019/@@display-file/arquivo_norma/PA2019-3507%20-%20Compilado%20at%C3%A9%20PA2019-3902.pdf",
    },
    {
        "id": "resolucao_464_2018", "type": "html", "essential": True,
        "file": "05_resolucao_464_2018.html",
        "check": "RESOLUÇÃO",
        "url": "https://www.anac.gov.br/assuntos/legislacao/legislacao-1/resolucoes/2018/resolucao-no-464-22-02-2018",
    },
    {
        "id": "portaria_1017_2018_compilada_2176_2019", "type": "pdf", "essential": True,
        "file": "06_portaria_1017_2018_compilada.pdf",
        "url": "https://www.anac.gov.br/assuntos/legislacao/legislacao-1/portarias/2018/portaria-no-1017-sra-sia-26-03-2018/@@display-file/arquivo_norma/PA2018-1017%20-%20Compilado%20at%C3%A9%20PA2019-2176.pdf",
    },
    {
        "id": "metadados_movimentacao_aeroportuaria", "type": "html",
        "essential": True, "file": "07_metadados_movimentacao_aeroportuaria.html",
        "check": "QT_CARGA",
        "url": "https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/operador-aeroportuario/dados-de-movimentacao-aeroportuaria/60-dados-de-movimentacao-aeroportuaria",
    },
    {
        "id": "portaria_3902_2019_alteracao", "type": "pdf", "essential": False,
        "file": "08_portaria_3902_2019_alteracao.pdf",
        "url": "https://www.anac.gov.br/assuntos/legislacao/legislacao-1/portarias/2019/portaria-no-3902-sas-20-12-2019/@@display-file/arquivo_norma/PA2019-3902.pdf",
    },
    {
        "id": "pagina_referencias_concessionaria_vcp", "type": "html",
        "essential": False, "file": "09_pagina_referencias_concessionaria.html",
        "check": "Viracopos",
        "url": "https://www.viracopos.com/pt_br/institucional/estatisticas-e-publicacoes.htm",
    },
]
ALLOWED_HOSTS = {"www.anac.gov.br", "pergamum.anac.gov.br",
                 "www.gov.br", "www.viracopos.com"}
TLS = ssl.create_default_context()


def download(source):
    req = Request(source["url"], headers={
        "User-Agent": "VCP-Insights-documentation-archiver/1.0",
        "Accept": "application/pdf,text/html,*/*",
    })
    last_error = ""
    for attempt in range(3):
        try:
            with urlopen(req, timeout=45, context=TLS) as response:
                final_url = response.geturl()
                host = urlparse(final_url).hostname
                if urlparse(final_url).scheme != "https" or host not in ALLOWED_HOSTS:
                    raise ValueError("Redirecionamento para origem não autorizada")
                raw = response.read(18_000_001)
                if not 200 <= response.status < 300 or len(raw) > 18_000_000:
                    raise ValueError("Resposta HTTP incorreta ou tamanho excessivo")
                if source["type"] == "pdf":
                    if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-4096:]:
                        raise ValueError("Resposta não contém PDF completo")
                else:
                    if b"<html" not in raw[:5000].lower() or (
                        source["check"].encode("utf-8").lower() not in raw.lower()
                        and source["check"].encode("latin-1", "ignore").lower() not in raw.lower()
                    ):
                        raise ValueError("HTML inesperado, captcha ou página indisponível")
                DEST.mkdir(parents=True, exist_ok=True)
                file = DEST / source["file"]
                file.write_bytes(raw)
                return {
                    "status": "baixado", "file": str(file.relative_to(ROOT)),
                    "url_final": final_url, "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "tipo_resposta": response.headers.get("Content-Type", ""),
                }
        except (HTTPError, URLError, ValueError, OSError) as exc:
            last_error = str(exc)
            if attempt < 2:
                time.sleep(2**attempt)
    return {"status": "pendente", "erro": last_error}


def main():
    details = []
    for s in SOURCES:
        result = download(s)
        details.append({k: v for k, v in s.items() if k != "check"} | result)
        print(s["id"], result["status"], result.get("erro", ""), flush=True)
    catalog = {
        "projeto": "Viracopos Cargo Intelligence",
        "etapa": "1_documentacao_apenas",
        "capturado_em_utc": datetime.now(timezone.utc).isoformat(),
        "documentos": details,
        "essenciais_pendentes": [r["id"] for r in details
                                if r["essential"] and r["status"] != "baixado"],
        "nota": "Captura do arquivo público original, sem interpretar nulos nem modificar datasets.",
    }
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+"\n",
                       encoding="utf-8")
    print("Documentos baixados:", sum(r["status"]=="baixado" for r in details))
    print("Essenciais pendentes:", catalog["essenciais_pendentes"])
    if catalog["essenciais_pendentes"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

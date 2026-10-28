"""Inventário SOMENTE de listagem oficial ANAC/RIMA, sem baixar microdados."""
import argparse
import json
import re
import ssl
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

from arquivar_anac_rima import BASE_URL, FIRST_MONTH, lagged_month, month_sequence

MAX_DIRECTORY_BYTES = 2_000_000
NAME = re.compile(r"^Movimentacoes_Aeroportuarias_(\d{6})\.(csv(?:\.csv)?|json)$", re.I)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def parse_listing(html, year):
    """Retorna formatos listados por competência. Não confirma conteúdo dos CSV."""
    parser = Links()
    parser.feed(html)
    observed = {}
    for href in parser.hrefs:
        name = unquote(urlsplit(href).path).split("/")[-1]
        match = NAME.fullmatch(name)
        if not match:
            continue
        compact, extension = match.groups()
        month = compact[:4] + "-" + compact[4:]
        if (not compact.startswith(str(year))
                or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month)):
            continue
        observed.setdefault(month, set()).add(extension.lower())
    return {month: sorted(formats) for month, formats in sorted(observed.items())}


def fetch_directory(year, opener=urlopen):
    url = BASE_URL + f"{year}/"
    request = Request(url, headers={
        "User-Agent": "VCP-Insights-ANAC-RIMA-index/1.0",
        "Accept": "text/html",
    })
    with opener(request, timeout=30, context=ssl.create_default_context()) as response:
        if response.status != 200:
            raise ValueError(f"HTTP inesperado para o índice: {response.status}")
        final = urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname != "sistemas.anac.gov.br":
            raise ValueError("Redirecionamento fora do servidor HTTPS ANAC")
        data = response.read(MAX_DIRECTORY_BYTES + 1)
    if not data or len(data) > MAX_DIRECTORY_BYTES:
        raise ValueError("Índice vazio ou muito grande")
    page = data.decode("utf-8-sig", errors="replace")
    if "<a " not in page.lower() and "<a\n" not in page.lower():
        raise ValueError("Índice sem links HTML; pode ser bloqueio ou página incorreta")
    return parse_listing(page, year), url, len(data)


def build_inventory(*, today=None, fetcher=fetch_directory):
    now = today or date.today()
    last = lagged_month(now)
    if last < FIRST_MONTH:
        raise ValueError("Nenhum mês dentro da janela 2020+")
    result = {
        "fonte": "ANAC/RIMA - índice público de arquivos por ano",
        "inicio": FIRST_MONTH, "ultimo_mes_elegivel_indicativo": last,
        "consultado_em_utc": datetime.now(timezone.utc).isoformat(),
        "observacao": "Nome listado ≠ CSV integral baixado, cobertura SBKP ou qualidade validada. A defasagem de seis meses é margem, não confirmação de publicação.",
        "anos": {}, "competencias": {}, "falhas_indice": [],
        "contagens": {"listadas": 0, "nao_listadas": 0, "indice_inacessivel": 0},
    }
    indexes = {}
    for year in range(2020, int(last[:4]) + 1):
        try:
            listing, url, size = fetcher(year)
            indexes[year] = listing
            result["anos"][str(year)] = {
                "situacao": "indice_lido", "url": url,
                "bytes_indice": size, "competencias_listadas": len(listing),
            }
        except (OSError, ValueError, TimeoutError) as exc:
            result["anos"][str(year)] = {
                "situacao": "indice_inacessivel", "erro": str(exc)[:250]
            }
            result["falhas_indice"].append(str(year))
    for month in month_sequence(FIRST_MONTH, last):
        year = int(month[:4])
        if year not in indexes:
            status, formats = "indice_inacessivel", []
        else:
            formats = indexes[year].get(month, [])
            status = "listado" if formats else "nao_listado"
        result["competencias"][month] = {"status": status, "formatos": formats}
        result["contagens"][status if status != "listado" else "listadas"] += 1
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"inicio": result["inicio"], "fim_indicativo": result["ultimo_mes_elegivel_indicativo"],
                      "contagens": result["contagens"], "falhas_indice": result["falhas_indice"],
                      "nao_listados": [m for m, v in result["competencias"].items()
                                      if v["status"] == "nao_listado"]}, ensure_ascii=False))
    if len(result["falhas_indice"]) == len(result["anos"]):
        raise SystemExit("Nenhum diretório oficial acessível: inventário NÃO confirmado")


if __name__ == "__main__":
    main()

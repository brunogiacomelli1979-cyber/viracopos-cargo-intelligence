"""Totais mensais nacionais da tabela consolidada oficial MDIC (US$ milhões)."""
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser

from fontes_http import get_bytes
from validar_dados import validate_rows

URL = "https://balanca.mdic.gov.br/balanca/publicacoes_dados_consolidados/pg.html"


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
        elif self.table is not None and tag == "tr":
            self.row = []
        elif self.row is not None and tag in ("td", "th"):
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def parse_brazil(raw):
    parser = Tables()
    parser.feed(raw.decode("utf-8-sig"))
    for table in parser.tables:
        headers = " ".join(" ".join(row) for row in table[:4])
        if not all(label in headers for label in ("Exportações", "Importações", "Saldo", "Corrente")):
            continue
        rows = []
        for item in table:
            if len(item) < 5 or not re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", item[0]):
                continue
            def number(text):
                return Decimal(text.replace(".", "").replace(",", "."))
            exp, imp, balance, total = map(number, item[1:5])
            if abs(exp + imp - total) > Decimal("0.2") or abs(exp - imp - balance) > Decimal("0.2"):
                raise ValueError("MDIC: totais da tabela não reconciliam")
            month, year = item[0].split("/")
            rows.append({"mes": f"{year}-{month}", "exportacoes_usd_bi": float(exp / 1000), "importacoes_usd_bi": float(imp / 1000)})
        if rows:
            return validate_rows("brasil", rows)
    raise ValueError("Tabela nacional mensal MDIC não identificada")


def collect_brazil():
    raw = get_bytes(URL)
    rows = parse_brazil(raw)
    stamp = datetime.now(timezone.utc).isoformat()
    return rows, {"fonte_original": URL, "coletado_em_utc": stamp, "status": "validado", "sha256_resposta": hashlib.sha256(raw).hexdigest(), "unidades": {"exportacoes_usd_bi": "US$ bilhões FOB", "importacoes_usd_bi": "US$ bilhões FOB"}, "periodicidade": "mensal", "abrangencia": "Brasil; todas as vias de transporte", "tratamento": "Tabela oficial Totais > Mensal em US$ FOB milhões; divisão por 1.000 para bilhões; soma/corrente e diferença/saldo reconciliadas. Mesclagem por competência preserva histórico anterior.", "limitacoes": "Valores arredondados a US$ 0,1 milhão na publicação; sujeitos a revisão. Indicador nacional não representa Viracopos."}


if __name__ == "__main__":
    rows, receipt = collect_brazil()
    print(json.dumps({"rows": rows, "receipt": receipt}, ensure_ascii=False))

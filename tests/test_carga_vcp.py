"""Regressões do contrato RMA; fixtures sintéticas só para testes, sem PDFs."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from coletar_carga_vcp import INDEX_URL, collect_rma, discover_rma, parse_rma_text


def fixture_text(month_count=2, january_international=20):
    # 3 colunas aeronaves + 3 passageiros + 3 carga + 3 courier.
    january = [101, 102, 203, 1001, 1002, 2003, 10, january_international, 10 + january_international, 0, 3, 3]
    february = [111, 112, 223, 1101, 1102, 2203, 11, 21, 32, 0, 4, 4]
    rows = [january, february][:month_count]
    lines = ["Resumo de Movimentação Aeroportuária (RMA)",
             "Movimento Operacional de Viracopos: Janeiro a Fevereiro de 2026",
             "Movimentação de Cargas (toneladas) / Movimentação de Cargas Courier (toneladas)"]
    for month, values in zip(("Janeiro", "Fevereiro"), rows):
        lines.append(month + "  " + "  ".join(f"{value:,}".replace(",", ".") for value in values))
    lines += ["Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    totals = [sum(values[index] for values in rows) for index in range(12)]
    lines.append("SOMA  " + "  ".join(str(value) for value in totals))
    lines.append("* importações + exportações")
    return "\n".join(lines)


class CargoRmaTests(unittest.TestCase):
    def test_selects_cargo_columns_without_passenger_or_courier_sum(self):
        rows, receipt = parse_rma_text(fixture_text())
        self.assertEqual(rows[0], {"mes": "2026-01", "carga_internacional_t": 20, "carga_domestica_t": 10, "courier_internacional_t": 3})
        self.assertEqual(receipt["controle_publicado_t"]["carga_internacional_t"], 41)
        self.assertNotEqual(rows[0]["carga_internacional_t"], 23)

    def test_blank_months_are_omitted(self):
        rows, _ = parse_rma_text(fixture_text())
        self.assertEqual([row["mes"] for row in rows], ["2026-01", "2026-02"])

    def test_schema_drift_is_rejected(self):
        text = fixture_text().replace("Janeiro  101  102  203", "Janeiro  101  102")
        with self.assertRaisesRegex(ValueError, "12 colunas"):
            parse_rma_text(text)

    def test_scope_note_is_required(self):
        with self.assertRaisesRegex(ValueError, "cabeçalho/unidade/nota"):
            parse_rma_text(fixture_text().replace("* importações + exportações", ""))

    def test_monthly_control_must_reconcile(self):
        with self.assertRaisesRegex(ValueError, "Totais mensais"):
            parse_rma_text(fixture_text().replace("10  20  30", "10  20  31"))

    def test_most_complete_year_version_wins_in_any_url_order(self):
        latest = "https://www.viracopos.com/data/a/RMA%202026%20FEV.pdf"
        older = "https://www.viracopos.com/data/z/RMA%202026%20JAN.pdf"
        payloads = {latest: fixture_text(2, 99).encode(), older: fixture_text(1, 20).encode()}
        for order in ((latest, older), (older, latest)):
            with self.subTest(order=order):
                html = "".join(f'<a href="{url}">RMA</a>' for url in order).encode()
                def fetch(url):
                    return html if url == INDEX_URL else payloads[url]
                with patch("coletar_carga_vcp.extract_rma", side_effect=lambda content: parse_rma_text(content.decode())):
                    rows, metadata = collect_rma(fetcher=fetch, now=datetime(2026, 3, 10, tzinfo=timezone.utc))
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["carga_internacional_t"], 99)
                self.assertEqual([item["url"] for item in metadata["documentos"]], [latest])

    def test_current_month_is_excluded_and_old_history_preserved(self):
        url = "https://www.viracopos.com/data/a/RMA%202026%20FEV.pdf"
        html = f'<a href="{url}">RMA</a>'.encode()
        previous = {"mes": "2025-12", "carga_internacional_t": 5, "carga_domestica_t": 6, "courier_internacional_t": 1}
        def fetch(target):
            return html if target == INDEX_URL else fixture_text().encode()
        with patch("coletar_carga_vcp.extract_rma", side_effect=lambda content: parse_rma_text(content.decode())):
            rows, _ = collect_rma([previous], fetcher=fetch, now=datetime(2026, 2, 20, tzinfo=timezone.utc))
        self.assertEqual([row["mes"] for row in rows], ["2025-12", "2026-01"])
        self.assertEqual(rows[0], previous)


if __name__ == "__main__":
    unittest.main()

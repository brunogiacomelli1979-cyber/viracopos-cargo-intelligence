import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inventariar_anac_rima import build_inventory, parse_listing


class IndexInventoryTests(unittest.TestCase):
    def test_parses_csv_json_and_doubled_extension(self):
        html = """<html>
        <a href="Movimentacoes_Aeroportuarias_202001.csv">jan</a>
        <a href="/some/path/Movimentacoes_Aeroportuarias_202002.json">fev</a>
        <a href="Movimentacoes_Aeroportuarias_202012.csv.csv">dez</a>
        <a href="Movimentacoes_Aeroportuarias_201912.csv">fora</a>
        <a href="../">voltar</a></html>"""
        actual = parse_listing(html, 2020)
        self.assertEqual(actual, {"2020-01": ["csv"], "2020-02": ["json"],
                                   "2020-12": ["csv.csv"]})

    def test_marks_missing_without_claiming_zero_data(self):
        def fetcher(year):
            if year == 2020:
                return ({"2020-01": ["csv"], "2020-02": ["csv"]}, "https://example.invalid", 80)
            raise TimeoutError("DNS temporariamente indisponível")
        data = build_inventory(today=date(2021, 9, 1), fetcher=fetcher)
        self.assertEqual(data["ultimo_mes_elegivel_indicativo"], "2021-03")
        self.assertEqual(data["competencias"]["2020-01"]["status"], "listado")
        self.assertEqual(data["competencias"]["2020-03"]["status"], "nao_listado")
        self.assertEqual(data["competencias"]["2021-01"]["status"], "indice_inacessivel")
        self.assertEqual(data["falhas_indice"], ["2021"])

    def test_excludes_2019_and_future_months(self):
        def fetcher(year):
            if year != 2020:
                raise AssertionError("Data fora do intervalo esperado")
            return ({}, "https://example.invalid", 50)
        result = build_inventory(today=date(2020, 8, 1), fetcher=fetcher)
        self.assertEqual(list(result["competencias"]), ["2020-01", "2020-02"])
        self.assertNotIn("2019-12", result["competencias"])
        self.assertNotIn("2020-03", result["competencias"])


if __name__ == "__main__":
    unittest.main()

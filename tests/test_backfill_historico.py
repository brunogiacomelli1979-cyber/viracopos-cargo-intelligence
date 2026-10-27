"""Contratos de retroalimentação MDIC e reconsulta BCB."""
import sys
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from coletar_comex import collect_comex
from atualizar import build

class HistoricalBackfillTests(unittest.TestCase):
    def test_refuses_open_year(self):
        with self.assertRaisesRegex(ValueError, "anos encerrados"):
            collect_comex(years=[datetime.now(timezone.utc).year])

    def test_refuses_invalid_year(self):
        for years in ([1996], [], ["2020"]):
            with self.subTest(years=years), self.assertRaises(ValueError):
                collect_comex(years=years)

    def test_build_refuses_undocumented_backfill_year(self):
        for years in ([1996], [2030], []):
            with self.subTest(years=years), self.assertRaises(ValueError):
                build(offline=True, mdic_years=years)

    def test_macro_backfill_start_is_explicit(self):
        for year in (1989, 3000):
            with self.subTest(year=year), self.assertRaises(ValueError):
                build(offline=True, macro_start_year=year)

if __name__ == "__main__":
    unittest.main()

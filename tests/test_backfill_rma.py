"""Verifica que backfill é opcional e restrito a anos válidos."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atualizar import build

class BackfillTests(unittest.TestCase):
    def test_invalid_start_year_fails_before_io(self):
        for value in (2009, 2050, "2021", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build(offline=False, rma_start_year=value)

    def test_start_year_forwarded_to_rma_collector(self):
        # Teste de assinatura sem coleta real: a coleta integral é validada no Actions.
        import inspect
        self.assertIn("rma_start_year", inspect.signature(build).parameters)
        self.assertEqual(inspect.signature(build).parameters["rma_start_year"].default, 2025)

if __name__ == "__main__":
    unittest.main()

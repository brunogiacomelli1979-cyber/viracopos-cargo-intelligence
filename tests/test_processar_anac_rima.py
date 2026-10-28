"""Testes offline com dados artificiais; nunca atribuir fixtures à ANAC."""
import csv
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from processar_anac_rima import process_file, write_staging

HEADER = "ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n"


class RimaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.csv_file = self.root / "Movimentacoes_Aeroportuarias_202501.csv"
        self.today = date(2026, 10, 28)

    def make(self, text):
        self.csv_file.write_text(text, encoding="utf-8")
        return self.csv_file

    def runfile(self):
        return process_file(self.csv_file, "2025-01", today=self.today)

    def test_reject_period_before_project_start(self):
        with self.assertRaisesRegex(ValueError, "2020-01"):
            process_file(self.csv_file, "2019-12", today=self.today)

    def test_real_preamble_and_codes(self):
        self.make("Atualizado em: 2025-11-01\n" +
                  HEADER + "2025;01;SBKP;P;I;120;5\n")
        r = self.runfile()["rows"][2]
        self.assertEqual(r["carga_kg"], "120")
        self.assertEqual(r["correio_kg"], "5")

    def test_reject_unexpected_preamble(self):
        self.make("Erro interno\n" + HEADER +
                  "2025;01;SBKP;P;I;100;0\n")
        with self.assertRaises(ValueError):
            self.runfile()

    def test_grouped_valid_and_zero(self):
        self.make(HEADER +
                  "2025;01;SBKP;P;I;100,5;0\n"
                  "2025;01;SBKP;P;I;200;5\n"
                  "2025;01;SBKP;D;I;50;2\n"
                  "2025;01;SBKP;P;D;0;0\n"
                  "2025;01;SBGR;D;I;9000;100\n")
        result = self.runfile()
        rows = {(r["natureza"], r["movimento"]): r for r in result["rows"]}
        self.assertEqual(rows[("internacional", "pouso")]["carga_kg"], "300.5")
        self.assertEqual(rows[("internacional", "pouso")]["correio_kg"], "5")
        self.assertEqual(rows[("domestica", "pouso")]["carga_kg"], "0")
        self.assertEqual(rows[("domestica", "decolagem")]["carga_kg"], "")
        self.assertEqual(rows[("domestica", "decolagem")]["status"], "sem_movimentos")
        self.assertEqual(result["provenance"]["linhas_sbkp"], 4)
        self.assertFalse(result["provenance"]["cobertura_completa"])

    def test_missing_does_not_become_partial_sum(self):
        self.make(HEADER +
                  "2025;01;SBKP;P;I;100;10\n"
                  "2025;01;SBKP;P;I;;\n")
        r = self.runfile()["rows"][2]
        self.assertEqual(r["status"], "incompleto")
        self.assertEqual(r["carga_kg"], "")
        self.assertEqual(r["correio_kg"], "")
        self.assertEqual(r["carga_ausente"], 1)

    def test_reject_wrong_month_and_unknown_codes(self):
        for line in [
            "2025;02;SBKP;P;I;100;10\n",
            "2025;01;SBKP;P;X;100;10\n",
            "2025;01;SBKP;X;I;100;10\n",
        ]:
            with self.subTest(line=line):
                self.make(HEADER + line)
                with self.assertRaises(ValueError):
                    self.runfile()

    def test_bad_quantity_and_missing_column(self):
        for quantity in ["-2", "nan", "1.234,5", "N/D"]:
            with self.subTest(quantity=quantity):
                self.make(HEADER + f"2025;01;SBKP;P;I;{quantity};0\n")
                with self.assertRaises(ValueError):
                    self.runfile()
        self.make("ANO;MES;NR_AEROPORTO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n2025;01;SBKP;Internacional;5;0\n")
        with self.assertRaises(ValueError):
            self.runfile()

    def test_only_other_airport_and_future_month_rejected(self):
        self.make(HEADER + "2025;01;SBGR;P;I;12;4\n")
        with self.assertRaises(ValueError):
            self.runfile()
        self.make(HEADER + "2026;10;SBKP;P;I;12;4\n")
        with self.assertRaises(ValueError):
            process_file(self.csv_file, "2026-10", today=self.today)

    def test_output_only_staging_and_no_overwrite(self):
        self.make(HEADER + "2025;01;SBKP;P;I;1;2\n")
        r = self.runfile()
        path, meta = write_staging(r, self.root / "data" / "staging" / "anac_rima")
        self.assertTrue(path.exists())
        self.assertEqual(len(list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))), 4)
        self.assertEqual(json.loads(meta.read_text())["linhas_sbkp"], 1)
        with self.assertRaises(FileExistsError):
            write_staging(r, path.parent)

    def test_cp1252_and_incomplete_mail(self):
        content = HEADER.replace("QT_CORREIO\n", "QT_CORREIO;OBS\n") + "2025;01;SBKP;P;D;9;;ação\n"
        self.csv_file.write_bytes(content.encode("cp1252"))
        result = self.runfile()
        self.assertEqual(result["provenance"]["codificacao_detectada"], "cp1252")
        self.assertEqual(result["rows"][0]["status"], "incompleto")
        self.assertEqual(result["rows"][0]["carga_kg"], "9")
        self.assertEqual(result["rows"][0]["correio_kg"], "")


if __name__ == "__main__":
    unittest.main()

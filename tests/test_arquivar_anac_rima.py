import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from arquivar_anac_rima import month_sequence, filter_sbkp, store_month, load_manifest, official_url, choose_months

HEADER = "ANO;MES;NR_AEROPORTO;NR_MOVIMENTO_TIPO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n"
ROWS = (HEADER + "2024;01;SBKP;Pouso;Internacional;100;1\n" +
        "2024;01;SBGR;Pouso;Internacional;800;9\n" +
        "2024;01;SBKP;Decolagem;Doméstica;;0\n").encode("utf-8")

class ArchiveTests(unittest.TestCase):
    def test_months(self):
        self.assertEqual(list(month_sequence("2023-12","2024-02")), ["2023-12","2024-01","2024-02"])
        self.assertIn("2024/Movimentacoes_Aeroportuarias_202401.csv", official_url("2024-01"))

    def test_filter_keeps_sbkp_and_missing(self):
        compressed, meta = filter_sbkp(ROWS, "2024-01")
        text = gzip.decompress(compressed).decode("utf-8")
        self.assertEqual(meta["linhas_sbkp"], 2)
        self.assertNotIn("SBGR",text)
        self.assertIn(";;0",text)

    def test_official_update_preamble(self):
        sample = b"Atualizado em: 2025-01-01\n" + ROWS
        compressed, meta = filter_sbkp(sample, "2024-01")
        self.assertEqual(meta["linhas_sbkp"], 2)
        self.assertIn("SBKP", gzip.decompress(compressed).decode("utf-8"))

    def test_reject_unexpected_preamble(self):
        with self.assertRaises(ValueError):
            filter_sbkp(b"Erro inesperado\n" + ROWS, "2024-01")

    def test_reject_empty_and_bad_month(self):
        with self.assertRaises(ValueError):
            filter_sbkp(HEADER.encode(), "2024-01")
        with self.assertRaises(ValueError):
            filter_sbkp(ROWS, "2024-02")

    def test_manifest_and_no_overwrite_when_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/"data"/"anac"/"rima"
            manifest=load_manifest(root)
            status=store_month(root,manifest,"2024-01",ROWS,official_url("2024-01"),"2026-10-28T00:00:00+00:00")
            self.assertEqual(status,"novo")
            self.assertEqual(store_month(root,manifest,"2024-01",ROWS,official_url("2024-01"),"2026-10-28T00:00:00+00:00"),"sem_mudanca")
            saved=json.loads((root/"manifesto.json").read_text())
            self.assertEqual(saved["competencias"]["2024-01"]["sha256_original"],hashlib.sha256(ROWS).hexdigest())
            self.assertTrue((root/"sbkp/2024/2024-01.csv.gz").exists())

    def test_monthly_selects_missing_and_refresh(self):
        manifest={"competencias":{"2024-01":{}}}
        months=choose_months(manifest,"mensal","2024-01","2024-03",1,0)
        self.assertEqual(months,["2024-02","2024-03"])
if __name__ == "__main__":
    unittest.main()

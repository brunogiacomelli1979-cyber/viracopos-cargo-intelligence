import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acervo_bruto_anac import register
from reprocessar_bruto_anac import prepare
from test_ingestao_controlada_anac import URL, HEADER, DATA


class ReprocessOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.vault = self.root / "cofre"
        self.stage = self.root / "staging"
        self.raw = self.root / "original.csv"
        self.raw.write_bytes(DATA + b"2020;04;SBGR;D;D;900;0\n"
                                 + b"2020;04;SBKP;D;D;;1\n")

    def archive(self):
        return register(self.raw, "2020-04", URL, self.vault,
                        captured_at="2026-10-28T00:00:00+00:00")

    def test_reuse_original_without_network_or_raw_file(self):
        receipt = self.archive()
        self.raw.unlink()  # input temporario pode desaparecer
        result = prepare(self.vault, "2020-04", receipt["sha256"], self.stage)
        self.assertEqual(result["estado"], "staging_validado_local")
        info = result["resumo"]
        self.assertEqual(info["linhas_origem"], 3)
        self.assertEqual(info["linhas_sbkp"], 2)
        self.assertEqual(info["sha256_original"], receipt["sha256"])
        data = gzip.decompress((Path(result["pasta"]) / "sbkp.csv.gz").read_bytes())
        self.assertIn(b"SBKP", data)
        self.assertNotIn(b"SBGR", data)
        self.assertEqual(info["estado"], "staging_validado_local_nao_publicado")
        self.assertFalse((Path(result["pasta"]) / "sbkp.csv").exists())
        incompletos = [g for g in info["grupos"] if g["status"] == "incompleto"]
        self.assertEqual(len(incompletos), 1)
        self.assertEqual(incompletos[0]["carga_kg"], "")
        self.assertEqual(incompletos[0]["carga_ausente"], 1)

    def test_idempotent_and_no_overwrite(self):
        receipt = self.archive()
        first = prepare(self.vault, "2020-04", receipt["sha256"], self.stage)
        second = prepare(self.vault, "2020-04", receipt["sha256"], self.stage)
        self.assertEqual(second["estado"], "staging_reutilizado")
        self.assertEqual(second["resumo"], first["resumo"])

    def test_staging_corruption_is_detected(self):
        receipt = self.archive()
        first = prepare(self.vault, "2020-04", receipt["sha256"], self.stage)
        (Path(first["pasta"]) / "sbkp.csv.gz").write_bytes(b"corrompido")
        with self.assertRaisesRegex(ValueError, "diverge"):
            prepare(self.vault, "2020-04", receipt["sha256"], self.stage)

    def test_original_corruption_is_detected_before_filtering(self):
        receipt = self.archive()
        (self.vault / receipt["objeto"]).write_bytes(b"corrompido")
        with self.assertRaisesRegex(ValueError, "corrompido"):
            prepare(self.vault, "2020-04", receipt["sha256"], self.stage)
        self.assertFalse(self.stage.exists())

    def test_bad_sha_is_not_selected_implicitly(self):
        self.archive()
        with self.assertRaises(ValueError):
            prepare(self.vault, "2020-04", "../outra", self.stage)
        with self.assertRaises(FileNotFoundError):
            prepare(self.vault, "2020-04", "0" * 64, self.stage)

    def test_revisions_are_distinct(self):
        first = self.archive()
        self.raw.write_bytes(self.raw.read_bytes().replace(b"100;0", b"200;0"))
        second = self.archive()
        a = prepare(self.vault, "2020-04", first["sha256"], self.stage)
        b = prepare(self.vault, "2020-04", second["sha256"], self.stage)
        self.assertNotEqual(a["pasta"], b["pasta"])
        self.assertTrue(Path(a["pasta"]).is_dir())
        self.assertTrue(Path(b["pasta"]).is_dir())

    def test_bad_weight_stays_in_quarantine(self):
        self.raw.write_bytes(HEADER + b"2020;04;SBKP;P;I;-5;0\n")
        receipt = self.archive()
        with self.assertRaisesRegex(ValueError, "inesperado"):
            prepare(self.vault, "2020-04", receipt["sha256"], self.stage)
        self.assertFalse((self.stage / "2020-04" / receipt["sha256"]).exists())

    def test_no_sbkp_cannot_become_zero(self):
        self.raw.write_bytes(HEADER + b"2020;04;SBGR;P;I;8;0\n")
        receipt = self.archive()
        with self.assertRaisesRegex(ValueError, "sem movimentos SBKP"):
            prepare(self.vault, "2020-04", receipt["sha256"], self.stage)

    def test_cp1252_extra_column_is_preserved(self):
        text = ("ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;"
                "QT_CARGA;QT_CORREIO;OBS\n2020;04;SBKP;P;I;10;0;São Paulo\n")
        self.raw.write_bytes(text.encode("cp1252"))
        receipt = self.archive()
        result = prepare(self.vault, "2020-04", receipt["sha256"], self.stage)
        self.assertEqual(result["resumo"]["codificacao_original"], "cp1252")
        self.assertIn("São Paulo", gzip.decompress(
            (Path(result["pasta"]) / "sbkp.csv.gz").read_bytes()).decode("utf-8"))

    def test_public_output_and_main_archive_are_protected(self):
        receipt = self.archive()
        with self.assertRaises(ValueError):
            prepare(self.vault, "2020-04", receipt["sha256"], ROOT / "data/anac/rima/sbkp")
        with self.assertRaises(ValueError):
            prepare(self.vault, "2020-04", receipt["sha256"], ROOT / "_site/test")
        self.assertFalse((self.stage / "2020-04").exists())

    def test_unexpected_preamble_stays_in_quarantine(self):
        self.raw.write_bytes(b"ERRO DE SERVIDOR\n" + DATA)
        receipt = self.archive()
        with self.assertRaisesRegex(ValueError, "Preambulo"):
            prepare(self.vault, "2020-04", receipt["sha256"], self.stage)
        self.assertFalse((self.stage / "2020-04" / receipt["sha256"]).exists())


if __name__ == "__main__":
    unittest.main()

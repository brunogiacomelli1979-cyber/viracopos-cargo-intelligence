import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acervo_bruto_anac import register, digest_file
from arquivar_anac_rima import load_manifest, store_month, official_url
from simular_promocao_anac import simulate
from reprocessar_bruto_anac import prepare
from test_ingestao_controlada_anac import DATA, URL


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / "base"
        self.archive = self.base / "data/anac/rima"
        self.store = self.root / "raw-vault"
        self.stage = self.root / "stage"
        self.source_file = self.root / "original-202004.csv"
        self.source_file.write_bytes(DATA + b"2020;04;SBGR;P;I;1000;0\n")
        self.receipt = register(self.source_file, "2020-04", URL, self.store)
        initial = DATA.replace(b"2020;04", b"2020;01")
        store_month(self.archive, load_manifest(self.archive), "2020-01", initial,
                    official_url("2020-01"), "2026-10-28T00:00:00+00:00")

    def test_existing_acervo_and_manifest_unchanged(self):
        baseline = {p.relative_to(self.base): p.read_bytes()
                    for p in self.base.rglob("*") if p.is_file()}
        res = simulate(self.store, "2020-04", self.receipt["sha256"], self.stage, self.base)
        self.assertEqual(res["estado"], "simulacao_aprovada_nao_publicada")
        self.assertEqual(res["meses_base"], 1)
        self.assertEqual(res["meses_simulados"], 2)
        self.assertEqual(res["novos_registros_sbkp"], 1)
        self.assertEqual(res["registros_simulados"], 2)
        after = {p.relative_to(self.base): p.read_bytes()
                 for p in self.base.rglob("*") if p.is_file()}
        self.assertEqual(baseline, after)
        self.assertNotIn("2020-04", load_manifest(self.archive)["competencias"])

    def test_repeat_is_safe(self):
        a = simulate(self.store, "2020-04", self.receipt["sha256"], self.stage, self.base)
        b = simulate(self.store, "2020-04", self.receipt["sha256"], self.stage, self.base)
        self.assertEqual(a, b)

    def test_wrong_hash_fails(self):
        with self.assertRaises(FileNotFoundError):
            simulate(self.store, "2020-04", "0" * 64, self.stage, self.base)
        self.assertNotIn("2020-04", load_manifest(self.archive)["competencias"])

    def test_corrupted_stage_never_accepted(self):
        original = prepare(self.store, "2020-04", self.receipt["sha256"], self.stage)
        (Path(original["pasta"]) / "sbkp.csv.gz").write_bytes(b"corrompido")
        with self.assertRaises(ValueError):
            simulate(self.store, "2020-04", self.receipt["sha256"], self.stage, self.base)

    def test_existing_month_is_not_overwritten(self):
        with self.assertRaisesRegex(ValueError, "ja arquivada"):
            simulate(self.store, "2020-01", self.receipt["sha256"], self.stage, self.base)

    def test_corrupted_base_is_not_used(self):
        entry = load_manifest(self.archive)["competencias"]["2020-01"]
        (self.base / entry["caminho_sbkp"]).write_bytes(b"corrompido")
        with self.assertRaises(ValueError):
            simulate(self.store, "2020-04", self.receipt["sha256"], self.stage, self.base)

    def test_missing_manifest_is_not_created(self):
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaisesRegex(ValueError, "Manifesto base inexistente"):
            simulate(self.store, "2020-04", self.receipt["sha256"], self.stage, empty)
        self.assertEqual(list(empty.iterdir()), [])

    def test_failed_candidate_does_not_modify_valid_archive(self):
        before = digest_file(self.archive / "manifesto.json")
        invalid = DATA.replace(b"100;0", b"-100;0")
        self.source_file.write_bytes(invalid)
        bad = register(self.source_file, "2020-04", URL, self.store)
        with self.assertRaises(ValueError):
            simulate(self.store, "2020-04", bad["sha256"], self.stage, self.base)
        self.assertEqual(digest_file(self.archive / "manifesto.json"), before)


if __name__ == "__main__":
    unittest.main()

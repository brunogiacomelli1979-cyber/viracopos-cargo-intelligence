import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from acervo_bruto_anac import audit, register
from backup_acervo_anac import backup
from ensaio_recuperacao_g2_anac import drill
from test_ingestao_controlada_anac import DATA, URL


class G2DrillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.primary = self.parent / "volumeA"
        self.backups = self.parent / "volumeB"
        self.recovery = self.parent / "restore-root"
        self.backups.mkdir()
        self.recovery.mkdir()
        self.csv_path = self.parent / "input.csv"
        self.csv_path.write_bytes(DATA)
        self.receipt = register(self.csv_path, "2020-04", URL, self.primary,
                                captured_at="2026-10-28T12:00:00+00:00")
        self.sha = self.receipt["sha256"]

    def run_drill(self, mode="simulado"):
        return drill(self.primary, self.backups, self.recovery,
                     "2020-04", self.sha, mode=mode)

    def test_full_restore_and_replay_with_no_promotion(self):
        before = {p.relative_to(self.primary).as_posix(): p.read_bytes()
                  for p in self.primary.rglob("*") if p.is_file()}
        result = self.run_drill()
        self.assertEqual(result["schema"], "anac-g2-drill-v1")
        self.assertEqual(result["estado"], "ensaio_tecnico_aprovado_sem_homologacao_operacional")
        self.assertFalse(result["g2_operacional_aprovado"])
        self.assertEqual(result["arquivos_verificados"], 2)
        self.assertEqual(result["recibos_verificados"], 1)
        self.assertEqual(result["linhas_sbkp_reprocessadas"], 1)
        self.assertTrue(result["copia_restaurada_temporaria_removida_apos_auditoria"])
        self.assertEqual(list(self.recovery.iterdir()), [])
        after = {p.relative_to(self.primary).as_posix(): p.read_bytes()
                 for p in self.primary.rglob("*") if p.is_file()}
        self.assertEqual(after, before)
        self.assertTrue(audit(self.primary)["aprovado"])
        self.assertTrue((self.backups / "snapshots" / result["snapshot_id"]).exists())

    def test_idempotent_run_reuses_verified_snapshot(self):
        first = self.run_drill()
        second = self.run_drill()
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertFalse(second["g2_operacional_aprovado"])

    def test_operational_preflight_rejects_same_device(self):
        with patch("ensaio_recuperacao_g2_anac._check_devices", return_value={
            "volumes_so_distintos": False, "ressalva": "simulacao"
        }):
            with self.assertRaisesRegex(ValueError, "volumes distintos"):
                self.run_drill("pre_homologacao")
        self.assertEqual(list(self.recovery.iterdir()), [])
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_even_different_devices_do_not_autocertify_g2(self):
        with patch("ensaio_recuperacao_g2_anac._check_devices", return_value={
            "volumes_so_distintos": True, "ressalva": "simulado em teste"
        }):
            result = self.run_drill("pre_homologacao")
        self.assertFalse(result["g2_operacional_aprovado"])
        self.assertEqual(result["modo"], "pre_homologacao")
        self.assertGreaterEqual(len(result["pendencias_externas"]), 3)

    def test_invalid_sha_fails_before_creating_backup(self):
        with self.assertRaises((FileNotFoundError, ValueError)):
            drill(self.primary, self.backups, self.recovery,
                  "2020-04", "0" * 64)
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_corruption_at_source_fails_before_backup(self):
        (self.primary / self.receipt["objeto"]).write_bytes(b"CORRUPT")
        with self.assertRaises(ValueError):
            self.run_drill()
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_corrupted_preexisting_backup_does_not_reuse(self):
        previous = backup(self.primary, self.backups)
        p = self.backups / "snapshots" / previous["snapshot_id"] / "files" / self.receipt["objeto"]
        p.write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            self.run_drill()
        self.assertEqual(list(self.recovery.iterdir()), [])

    def test_paths_must_not_be_nested(self):
        with self.assertRaises(ValueError):
            drill(self.primary, self.primary, self.recovery, "2020-04", self.sha)
        with self.assertRaises(ValueError):
            drill(self.primary, self.backups, self.backups, "2020-04", self.sha)

    def test_missing_recovery_parent_is_not_automatically_created(self):
        absent = self.parent / "unmounted-or-missing"
        with self.assertRaisesRegex(ValueError, "diretorio existente"):
            drill(self.primary, self.backups, absent, "2020-04", self.sha)
        self.assertFalse(absent.exists())

    def test_missing_primary_is_not_automatically_replaced(self):
        shutil.rmtree(self.primary)
        with self.assertRaisesRegex(ValueError, "diretorio existente"):
            self.run_drill()
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_source_with_second_revision_both_versions_survive(self):
        self.csv_path.write_bytes(DATA.replace(b"100;0", b"200;0"))
        second = register(self.csv_path, "2020-04", URL, self.primary)
        self.assertNotEqual(self.sha, second["sha256"])
        result = self.run_drill()
        self.assertEqual(result["recibos_verificados"], 2)
        self.assertEqual(result["arquivos_verificados"], 4)


if __name__ == "__main__":
    unittest.main()

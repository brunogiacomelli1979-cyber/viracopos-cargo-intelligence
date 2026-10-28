import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acervo_bruto_anac import register, audit
from backup_acervo_anac import backup, verify, restore
from reprocessar_bruto_anac import prepare
from test_ingestao_controlada_anac import DATA, URL


class BackupRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / "input.csv"
        self.original.write_bytes(DATA)
        self.source = self.root / "primary-vault"
        self.backups = self.root / "second-volume"
        self.recovered = self.root / "recovered-vault"
        self.first = register(self.original, "2020-04", URL, self.source,
                              captured_at="2026-10-28T00:00:00+00:00")

    def snapshot(self):
        return backup(self.source, self.backups)["snapshot_id"]

    def snapshot_files(self, snapshot):
        return self.backups / "snapshots" / snapshot / "files"

    def test_backup_verification_and_idempotence(self):
        snap = self.snapshot()
        result = verify(self.backups, snap)
        self.assertEqual(result["estado"], "backup_verificado")
        self.assertEqual(result["arquivos"], 2)
        self.assertEqual(result["recibos"], 1)
        self.assertEqual(backup(self.source, self.backups)["estado"], "backup_ja_existente")

    def test_restore_after_loss_reprocesses_without_download(self):
        snap = self.snapshot()
        shutil.rmtree(self.source)
        self.original.unlink()
        restored = restore(self.backups, snap, self.recovered)
        self.assertEqual(restored["estado"], "backup_verificado")
        self.assertTrue(audit(self.recovered)["aprovado"])
        prepared = prepare(self.recovered, "2020-04", self.first["sha256"],
                           self.root / "offline-staging")
        self.assertEqual(prepared["resumo"]["linhas_sbkp"], 1)
        self.assertEqual(prepared["resumo"]["sha256_original"], self.first["sha256"])

    def test_preserve_two_revisions(self):
        self.original.write_bytes(DATA.replace(b"100;0", b"200;0"))
        second = register(self.original, "2020-04", URL, self.source)
        self.assertNotEqual(self.first["sha256"], second["sha256"])
        snap = self.snapshot()
        restore(self.backups, snap, self.recovered)
        self.assertEqual(audit(self.recovered)["recibos_validos"], 2)
        self.assertEqual(len(list((self.recovered / "receipts" / "2020-04").glob("*.json"))), 2)

    def test_corrupt_source_fails_before_backup_creation(self):
        (self.source / self.first["objeto"]).write_bytes(b"corrompido")
        with self.assertRaises(ValueError):
            backup(self.source, self.backups)
        self.assertFalse((self.backups / "snapshots").exists())

    def test_corrupt_backup_prevents_restore(self):
        snap = self.snapshot()
        backup_object = self.snapshot_files(snap) / self.first["objeto"]
        backup_object.write_bytes(b"corrompido")
        with self.assertRaises(ValueError):
            verify(self.backups, snap)
        with self.assertRaises(ValueError):
            restore(self.backups, snap, self.recovered)
        self.assertFalse(self.recovered.exists())

    def test_missing_receipt_is_detected_in_backup(self):
        snap = self.snapshot()
        p = self.snapshot_files(snap) / "receipts" / "2020-04" / (self.first["sha256"] + ".json")
        p.unlink()
        with self.assertRaises(ValueError):
            verify(self.backups, snap)

    def test_restoration_never_overwrites_existing_vault(self):
        snap = self.snapshot()
        self.recovered.mkdir()
        sentinel = self.recovered / "important.txt"
        sentinel.write_text("original")
        with self.assertRaises(ValueError):
            restore(self.backups, snap, self.recovered)
        self.assertEqual(sentinel.read_text(), "original")

    def test_backup_destination_cannot_be_nested_in_source(self):
        with self.assertRaises(ValueError):
            backup(self.source, self.source / "backup")
        self.assertFalse((self.source / "backup").exists())

    def test_restore_destination_cannot_be_nested_in_backup(self):
        snap = self.snapshot()
        with self.assertRaises(ValueError):
            restore(self.backups, snap, self.backups / "recovered")
        self.assertFalse((self.backups / "recovered").exists())

    def test_orphan_rejected_before_snapshot(self):
        obj = self.source / "objects" / ("0" * 2) / (("0" * 64) + ".csv")
        obj.parent.mkdir(parents=True, exist_ok=True)
        obj.write_bytes(b"orphan")
        with self.assertRaises(ValueError):
            backup(self.source, self.backups)

    def test_extra_file_in_snapshot_is_rejected(self):
        snap = self.snapshot()
        extra = self.snapshot_files(snap) / "objects" / "aa" / (("a" * 64) + ".csv")
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_bytes(b"unexpected")
        with self.assertRaises(ValueError):
            verify(self.backups, snap)

    def test_backup_inventory_tampering_is_detected(self):
        snap = self.snapshot()
        manifest_path = self.backups / "snapshots" / snap / "manifesto_backup.json"
        info = json.loads(manifest_path.read_text())
        info["arquivos"][0]["bytes"] += 1
        manifest_path.write_text(json.dumps(info))
        with self.assertRaises(ValueError):
            verify(self.backups, snap)

    def test_wrong_snapshot_identifier_fails_closed(self):
        self.snapshot()
        with self.assertRaises(ValueError):
            verify(self.backups, "../outside")
        with self.assertRaises(FileNotFoundError):
            verify(self.backups, "0" * 64)

    def test_backup_does_not_change_primary_vault(self):
        before = sorted((p.relative_to(self.source).as_posix(), p.read_bytes())
                        for p in self.source.rglob("*") if p.is_file())
        self.snapshot()
        after = sorted((p.relative_to(self.source).as_posix(), p.read_bytes())
                       for p in self.source.rglob("*") if p.is_file())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

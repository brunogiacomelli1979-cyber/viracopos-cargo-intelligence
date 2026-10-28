import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from planejar_coleta_anac import plan, range_months
from acervo_bruto_anac import register, audit

URL = "https://sistemas.anac.gov.br/dadosabertos/Operador%20Aeroportu%C3%A1rio/Dados%20de%20Movimenta%C3%A7%C3%A3o%20Aeroportu%C3%A1rias/2020/Movimentacoes_Aeroportuarias_202004.csv"
HEADER = b"Atualizado em: 2026-10-01\nANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n"
DATA = HEADER + b"2020;04;SBKP;P;I;100;0\n"

class PlannerTests(unittest.TestCase):
    def test_72_months_and_four_archived(self):
        inventory = json.loads((ROOT / "data/anac/rima/inventario_disponibilidade.json").read_text())
        manifest = {"schema": "anac_rima_sbkp_v1", "aeroporto": "SBKP", "competencias":
                    {x: {} for x in ("2020-01", "2020-02", "2020-03", "2024-01")}}
        result = plan(inventory, manifest)
        self.assertTrue(result["sem_download"])
        self.assertEqual(result["resumo"], {"arquivado_pendente_reauditoria": 4,
                                            "listado_pendente_captura": 68})
        extended = plan(inventory, manifest, "2026-01", "2026-04")
        self.assertEqual(extended["resumo"], {"indice_indisponivel": 4})

    def test_reject_bad_period_inventory_and_manifest(self):
        manifest = {"schema": "anac_rima_sbkp_v1", "aeroporto": "SBKP", "competencias": {}}
        inventory = {"schema": "anac-rima-inventario-v1", "anos": {"2022": {"meses_csv": [1,1]}}}
        with self.assertRaises(ValueError):
            plan(inventory, manifest)
        with self.assertRaises(ValueError):
            list(range_months("2019-12", "2020-01"))
        with self.assertRaises(ValueError):
            plan({"schema":"unknown"}, manifest)


class RawStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "input.csv"
        self.src.write_bytes(DATA)
        self.store = self.root / "vault"

    def test_archive_idempotent_and_audit(self):
        record = register(self.src, "2020-04", URL, self.store, captured_at="2026-10-28T00:00:00+00:00")
        self.assertEqual(record["sha256"], hashlib.sha256(DATA).hexdigest())
        self.assertEqual(record["status"], "bruto_preservado_nao_validado")
        self.assertEqual(record, register(self.src, "2020-04", URL, self.store))
        self.assertEqual(audit(self.store)["recibos_validos"], 1)
        self.assertTrue(audit(self.store)["aprovado"])

    def test_revision_keeps_both_files(self):
        first = register(self.src, "2020-04", URL, self.store)
        self.src.write_bytes(DATA.replace(b"100;0", b"200;0"))
        second = register(self.src, "2020-04", URL, self.store)
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual(audit(self.store)["recibos_validos"], 2)
        self.assertTrue(audit(self.store)["aprovado"])

    def test_corruption_is_detected(self):
        receipt = register(self.src, "2020-04", URL, self.store)
        (self.store / receipt["objeto"]).write_bytes(b"corrompido")
        self.assertFalse(audit(self.store)["aprovado"])
        self.assertTrue(audit(self.store)["erros"])

    def test_html_and_oversize_leave_no_object(self):
        for bad, limit in ((b"<html>Erro</html>", 100), (DATA, 10)):
            with self.subTest(content=bad[:10]):
                self.src.write_bytes(bad)
                with self.assertRaises(ValueError):
                    register(self.src, "2020-04", URL, self.store, limit=limit)
                self.assertEqual(list((self.store / "objects").glob("*/*.csv")), [])
                self.assertEqual(list((self.store / "incoming").glob("*.partial")), [])

    def test_wrong_month_url_fails_closed(self):
        with self.assertRaises(ValueError):
            register(self.src, "2020-05", URL, self.store)
        with self.assertRaises(ValueError):
            register(self.src, "2019-12", URL, self.store)
        self.assertFalse(self.store.exists())

    def test_store_under_git_is_rejected(self):
        with self.assertRaises(ValueError):
            register(self.src, "2020-04", URL, ROOT / "data" / "staging" / "raw")

    def test_empty_vault_is_not_certified(self):
        self.assertFalse(audit(self.store)["aprovado"])

    def test_orphan_is_detected(self):
        receipt = register(self.src, "2020-04", URL, self.store)
        (self.store / "receipts" / "2020-04" / (receipt["sha256"] + ".json")).unlink()
        result = audit(self.store)
        self.assertFalse(result["aprovado"])
        self.assertEqual(len(result["objetos_orfaos"]), 1)

if __name__ == "__main__":
    unittest.main()

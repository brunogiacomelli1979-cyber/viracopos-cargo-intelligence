import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from conciliar_rima_rma import reconcile, load_rma, load_preliminary, _compare, _anac_tonnes
from decimal import Decimal

GROUPS = {
    "domestica/pouso": {"status": "completo", "carga_kg": "2518901"},
    "domestica/decolagem": {"status": "completo", "carga_kg": "3389598"},
    "internacional/pouso": {"status": "completo", "carga_kg": "9460925"},
    "internacional/decolagem": {"status": "completo", "carga_kg": "6554994"},
}
ANAC = {"resultado": "aprovado_tecnicamente",
        "erros": [], "comparacoes": {"2024-01": {"grupos": GROUPS}}}


class ReconcilerTests(unittest.TestCase):
    def test_no_overlap_does_not_invent_comparison(self):
        r = {"2025-01": {"mes": "2025-01", "fonte": "RMA_concessionaria_dashboard",
                         "status": "rma_painel_atual", "carga_domestica_t": "5000",
                         "carga_internacional_t": "10000", "courier_internacional_t": "500"}}
        obj = reconcile(ANAC, r)
        self.assertEqual(obj["situacao"], "sem_mes_coincidente")
        self.assertEqual(obj["meses_coincidentes"], 0)
        self.assertEqual(obj["comparacoes"], {})
        self.assertFalse(obj["liberado_dashboard"])

    def test_monthly_overlap_and_kilogram_conversion(self):
        self.assertEqual(_anac_tonnes(GROUPS, "domestica"), Decimal("5908.499"))
        self.assertEqual(_anac_tonnes(GROUPS, "internacional"), Decimal("16015.919"))
        self.assertEqual(_compare(Decimal("16015.919"), "13962")["diferenca_t"], "2053.919")

    def test_preliminary_is_not_certified_even_if_near_equal(self):
        ref = {"mes": "2024-01", "carga_domestica_t": "5908",
               "carga_internacional_t": "13962", "courier_internacional_t": "604",
               "status": "transcricao_preliminar_nao_certificada",
               "fonte": "RMA_pdf_transcricao_preliminar"}
        obj = reconcile(ANAC, {}, ref)
        self.assertEqual(obj["situacao"], "apenas_confronto_preliminar")
        self.assertFalse(obj["liberado_dashboard"])
        self.assertEqual(obj["comparacoes"]["2024-01"]["comparacao_domestica"]["diferenca_t"], "0.499")
        self.assertIn({"mes": "2024-01", "natureza": "internacional",
                       "tipo": "divergencia_fisica_conceitual_a_investigar"}, obj["alertas"])
        self.assertEqual(obj["comparacoes"]["2024-01"]["courier_rma_t_nao_comparado_ao_correio_anac"], "604")

    def test_incomplete_anac_is_not_treated_as_zero(self):
        groups = {**GROUPS, "internacional/pouso": {"status": "incompleto", "carga_kg": None}}
        self.assertIsNone(_anac_tonnes(groups, "internacional"))
        self.assertFalse(_compare(_anac_tonnes(groups, "internacional"), "13962")["comparavel"])

    def test_incomplete_group_does_not_break_reconciliation(self):
        groups = {**GROUPS, "internacional/pouso": {
            "status": "incompleto", "carga_kg": None
        }}
        anac = {"resultado": "aprovado_tecnicamente", "erros": [],
                "comparacoes": {"2024-01": {"grupos": groups}}}
        prelim = {"mes": "2024-01", "carga_domestica_t": "5908",
                  "carga_internacional_t": "13962",
                  "courier_internacional_t": "604",
                  "status": "transcricao_preliminar_nao_certificada",
                  "fonte": "RMA_pdf_transcricao_preliminar"}
        output = reconcile(anac, {}, prelim)
        self.assertFalse(output["comparacoes"]["2024-01"]["comparacao_internacional"]["comparavel"])
        self.assertFalse(output["liberado_dashboard"])

    def test_bad_rma_duplicate_month_rejected(self):
        text = ("mes,carga_internacional_t,carga_domestica_t,courier_internacional_t\n"
                "2025-01,12,14,1\n2025-01,12,14,1\n")
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "rma.csv"
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicata"):
                load_rma(path)

    def test_unverified_reference_must_be_official(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "ref.json"
            content = {"mes": "2024-01", "url_pdf": "https://evil.example/ref.pdf",
                       "carga_internacional_t": "1", "carga_domestica_t": "2",
                       "courier_internacional_t": "3",
                       "status": "transcricao_preliminar_nao_certificada",
                       "verificacao_pdf_completa": False, "sha256_pdf": None}
            path.write_text(json.dumps(content))
            with self.assertRaisesRegex(ValueError, "PDF oficial"):
                load_preliminary(path)


if __name__ == "__main__":
    unittest.main()

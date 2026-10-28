"""Protege contra reativação acidental de coletores ANAC legados."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows"
FROZEN = (
    "anac-sbkp-piloto.yml",
    "piloto-anac-rima-2019.yml",
    "testar-acesso-anac-rima.yml",
    "inspecionar-anac-2019.yml",
)


class WorkflowSafetyTests(unittest.TestCase):
    def test_old_workflows_are_non_executable(self):
        for name in FROZEN:
            with self.subTest(name=name):
                text = (WF / name).read_text(encoding="utf-8")
                self.assertIn("if: false", text)
                self.assertIn("  workflow_dispatch:", text)
                self.assertNotIn("  push:", text)
                self.assertNotIn("  schedule:", text)
                self.assertNotIn("contents: write", text)

    def test_audit_is_offline(self):
        text = (WF / "auditar-pendencias-anac.yml").read_text(encoding="utf-8")
        self.assertNotIn("urlopen", text)
        self.assertNotIn("2019/", text)
        self.assertIn("scripts/auditar_anac_rima.py", text)

    def test_active_collector_still_locked(self):
        text = (WF / "arquivar-anac-rima.yml").read_text(encoding="utf-8")
        self.assertIn("vars.ANAC_RIMA_COLETA_AUTORIZADA == 'true'", text)
        self.assertIn("vars.ANAC_RIMA_PILOTO_202003_AUTORIZADO == 'true'", text)
        self.assertIn("github.event_name == 'workflow_dispatch'", text)
        self.assertIn("github.ref_name == 'feature/anac-rima-staging-20261028'", text)
        self.assertIn("inputs.confirmar_competencia == '2020-03'", text)
        self.assertIn("--mode inicial --start 2020-03 --end 2020-03 --limit 1", text)
        self.assertNotIn("--limit \"$LIMIT\"", text)
        self.assertNotIn("  schedule:", text)
        self.assertNotIn("  push:", text)
        self.assertIn("scripts/publicar_anac_git.py", text)
        self.assertIn("needs: verificar-autorizacao", text)
        self.assertIn("steps.gate.outputs.autorizado", text)
        self.assertIn("needs.verificar-autorizacao.outputs.autorizado == 'true'", text)
        self.assertIn("echo \"autorizado=false\" >> \"$GITHUB_OUTPUT\"", text)
        self.assertIn("## Piloto ANAC 2020-03: NÃO EXECUTADO", text)
        self.assertIn("contents: read", text)
        self.assertIn("contents: write", text)


    def test_year_probe_respects_2020_start(self):
        text = (WF / "sondar-disponibilidade-anac-rima.yml").read_text(encoding="utf-8")
        self.assertIn("for year in range(2020,2025):", text)
        self.assertNotIn("for year in range(2019", text)


if __name__ == "__main__":
    unittest.main()

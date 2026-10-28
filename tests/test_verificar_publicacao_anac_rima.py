import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from arquivar_anac_rima import load_manifest, store_month, official_url
from publicar_anac_git import publish, HOMOLOG_BRANCH
from verificar_publicacao_anac_rima import verify

HEADER = "ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n"


def git(root, *args):
    outcome = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    if outcome.returncode:
        raise AssertionError(outcome.stderr)
    return outcome.stdout.strip()


def add_month(root, month):
    y, m = month.split("-")
    raw = (HEADER + f"{y};{m};SBKP;P;I;100;0\n"
           + f"{y};{m};SBKP;D;I;200;0\n"
           + f"{y};{m};SBKP;P;D;300;0\n"
           + f"{y};{m};SBKP;D;D;400;0\n").encode()
    folder = root / "data/anac/rima"
    store_month(folder, load_manifest(folder), month, raw, official_url(month),
                "2026-10-28T00:00:00+00:00")


class RemoteVerificationTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"GITHUB_REF_NAME": HOMOLOG_BRANCH})
        env.start()
        self.addCleanup(env.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        origin = self.root / "server.git"
        git(self.root, "init", "--bare", "--initial-branch=main", str(origin))
        seed = self.root / "seed"
        git(self.root, "clone", str(origin), str(seed))
        git(seed, "config", "user.name", "QA")
        git(seed, "config", "user.email", "qa@example.invalid")
        (seed / "README.md").write_text("fixture\n")
        add_month(seed, "2020-01")
        git(seed, "add", ".")
        git(seed, "commit", "-m", "fixture baseline")
        git(seed, "push", "origin", "main")
        self.main = git(seed, "rev-parse", "HEAD")
        git(seed, "switch", "-c", HOMOLOG_BRANCH)
        git(seed, "push", "origin", HOMOLOG_BRANCH)
        self.work = self.root / "worker"
        git(self.root, "clone", "-b", HOMOLOG_BRANCH, str(origin), str(self.work))
        self.before = git(self.work, "rev-parse", "HEAD")

    def test_publish_fetch_verify_and_repeat(self):
        add_month(self.work, "2020-03")
        record = publish(self.work)
        result = verify(self.work, self.before, self.main)
        self.assertEqual(result["status"], "novo_mes_confirmado")
        self.assertEqual(result["meses_novos"], ["2020-03"])
        self.assertEqual(result["registros_totais"], 8)
        self.assertEqual(result["integridade"], "aprovada")
        repeat = verify(self.work, record["commit"], self.main)
        self.assertEqual(repeat["status"], "repeticao_sem_mudancas")

    def test_unrelated_commit_is_blocked(self):
        add_month(self.work, "2020-03")
        publish(self.work)
        (self.work / "README.md").write_text("not part of ANAC\n")
        git(self.work, "add", "README.md")
        git(self.work, "commit", "-m", "unrelated change")
        git(self.work, "push", "origin", HOMOLOG_BRANCH)
        with self.assertRaisesRegex(ValueError, "fora do escopo"):
            verify(self.work, self.before, self.main)

    def test_main_sha_change_is_blocked(self):
        add_month(self.work, "2020-03")
        publish(self.work)
        other = self.root / "main_update"
        git(self.root, "clone", "-b", "main", str(self.root / "server.git"), str(other))
        git(other, "config", "user.name", "Other")
        git(other, "config", "user.email", "other@example.invalid")
        (other / "README.md").write_text("main updated\n")
        git(other, "commit", "-am", "unrelated main change")
        git(other, "push", "origin", "main")
        with self.assertRaisesRegex(ValueError, "Branch principal modificada"):
            verify(self.work, self.before, self.main)


if __name__ == "__main__":
    unittest.main()

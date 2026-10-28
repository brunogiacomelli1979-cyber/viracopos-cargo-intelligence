"""Integração Git totalmente local: nenhum acesso à ANAC nem a repositórios remotos reais."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from arquivar_anac_rima import load_manifest, store_month, official_url
from publicar_anac_git import publish, PublishError, HOMOLOG_BRANCH

HEADER = "ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n"


def command(cwd, *args):
    result = subprocess.run(["git", *args], cwd=cwd, text=True,
                            capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(f"Git falhou {args}: {result.stderr}")
    return result.stdout.strip()


def add_month(repo, month, amount):
    root = repo / "data/anac/rima"
    manifest = load_manifest(root)
    raw = (HEADER + f"{month[:4]};{month[5:]};SBKP;P;I;{amount};0\n").encode()
    store_month(root, manifest, month, raw, official_url(month),
                "2026-10-28T11:00:00+00:00")


class PublishIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.origin = self.root / "origin.git"
        command(self.root, "init", "--bare", "--initial-branch=main", str(self.origin))
        self.seed = self.root / "seed"
        command(self.root, "clone", str(self.origin), str(self.seed))
        command(self.seed, "config", "user.name", "Teste ANAC")
        command(self.seed, "config", "user.email", "test@example.invalid")
        (self.seed / "README.md").write_text("Base simulada para teste local\n")
        add_month(self.seed, "2020-01", 100)
        command(self.seed, "add", ".")
        command(self.seed, "commit", "-m", "fixtures de teste")
        command(self.seed, "push", "origin", "main")
        self.main_sha = command(self.seed, "rev-parse", "HEAD")
        command(self.seed, "switch", "-c", HOMOLOG_BRANCH)
        command(self.seed, "push", "-u", "origin", HOMOLOG_BRANCH)

    def clone(self, name, branch):
        path = self.root / name
        command(self.root, "clone", "-b", branch, str(self.origin), str(path))
        return path

    def test_publicacao_valida_sem_alterar_main(self):
        worker = self.clone("worker", HOMOLOG_BRANCH)
        add_month(worker, "2020-02", 200)
        result = publish(worker)
        self.assertEqual(result["status"], "publicado")
        self.assertEqual(command(worker, "rev-parse", "HEAD"), result["commit"])
        self.assertEqual(command(self.seed, "ls-remote", "origin", "refs/heads/main").split()[0],
                         self.main_sha)
        check = self.clone("check", HOMOLOG_BRANCH)
        manifest = load_manifest(check / "data/anac/rima")
        self.assertEqual(sorted(manifest["competencias"]), ["2020-01", "2020-02"])
        self.assertEqual(publish(worker)["status"], "sem_alteracoes")

    def test_race_preserva_commit_concorrente(self):
        worker = self.clone("worker", HOMOLOG_BRANCH)
        competitor = self.clone("competitor", HOMOLOG_BRANCH)
        command(competitor, "config", "user.name", "Outro job")
        command(competitor, "config", "user.email", "other@example.invalid")
        add_month(worker, "2020-02", 300)

        def competing_push():
            (competitor / "note.txt").write_text("Atualização concorrente\n")
            command(competitor, "add", "note.txt")
            command(competitor, "commit", "-m", "concorrente")
            command(competitor, "push", "origin", f"HEAD:refs/heads/{HOMOLOG_BRANCH}")

        with self.assertRaisesRegex(PublishError, "push falhou"):
            publish(worker, before_push=competing_push)
        check = self.clone("check", HOMOLOG_BRANCH)
        self.assertTrue((check / "note.txt").is_file())
        self.assertEqual(sorted(load_manifest(check / "data/anac/rima")["competencias"]),
                         ["2020-01"])
        self.assertEqual(command(self.seed, "ls-remote", "origin", "refs/heads/main").split()[0],
                         self.main_sha)

    def test_remote_already_advanced_rejected(self):
        worker = self.clone("worker", HOMOLOG_BRANCH)
        competitor = self.clone("competitor", HOMOLOG_BRANCH)
        command(competitor, "config", "user.name", "Outro job")
        command(competitor, "config", "user.email", "other@example.invalid")
        (competitor / "note.txt").write_text("Concorrente\n")
        command(competitor, "add", "note.txt")
        command(competitor, "commit", "-m", "alteração concorrente")
        command(competitor, "push", "origin", f"HEAD:refs/heads/{HOMOLOG_BRANCH}")
        add_month(worker, "2020-02", 300)
        with self.assertRaisesRegex(PublishError, "avançou"):
            publish(worker)

    def test_manifesto_corrompido_nao_publica(self):
        worker = self.clone("worker", HOMOLOG_BRANCH)
        manifest_path = worker / "data/anac/rima/manifesto.json"
        data = json.loads(manifest_path.read_text())
        data["competencias"]["2020-01"]["sha256_sbkp_gzip"] = "0" * 64
        manifest_path.write_text(json.dumps(data))
        with self.assertRaisesRegex(PublishError, "reprovado"):
            publish(worker)

    def test_snapshot_existente_nao_pode_ser_removido(self):
        worker = self.clone("worker", HOMOLOG_BRANCH)
        data = load_manifest(worker / "data/anac/rima")
        (worker / data["competencias"]["2020-01"]["caminho_sbkp"]).unlink()
        with self.assertRaisesRegex(PublishError, "reprovado"):
            publish(worker)

    def test_branch_principal_bloqueada(self):
        worker = self.clone("worker", HOMOLOG_BRANCH)
        with self.assertRaisesRegex(PublishError, "bloqueada"):
            publish(worker, branch="main")


if __name__ == "__main__":
    unittest.main()

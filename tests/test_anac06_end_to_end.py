"""Integração completa ANAC-06 com apenas Git local e CSV sintético.

Percurso: coletor -> staging -> auditor independente -> publicador real ->
clone remoto -> recibo e hashes -> repetição sem commit. NÃO usa ANAC real.
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from arquivar_anac_rima import (
    load_manifest, official_url, run, store_month, _verify_snapshot
)
from auditar_anac_rima import inspect
from publicar_anac_git import publish, HOMOLOG_BRANCH, PublishError
from validar_agrupamento_rima import validate

HEADER = "ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n"


def command(cwd, *args):
    result = subprocess.run(["git", *args], cwd=cwd, text=True,
                            capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(f"git {args} falhou: {result.stderr}")
    return result.stdout.strip()


def sample(month, *, invalid=False):
    year, mm = month.split("-")
    value = "-100" if invalid else "100"
    return (f"Atualizado em: 2026-10-01\n" + HEADER
            + f"{year};{mm};SBKP;P;I;{value};1\n"
            + f"{year};{mm};SBKP;D;I;200;0\n"
            + f"{year};{mm};SBKP;P;D;300;2\n"
            + f"{year};{mm};SBKP;D;D;400;0\n"
            + f"{year};{mm};SBGR;P;I;12345;6\n").encode("utf-8")


def fake_opener(*, invalid=False, missing=False):
    class Response:
        status = 200
        def __init__(self, url):
            self.url = url
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def geturl(self):
            return self.url
        def read(self, size):
            return sample("2020-03", invalid=invalid)[:size]
    def open_fake(request, timeout=None, context=None):
        url = request.full_url
        if missing:
            raise HTTPError(url, 404, "not found", {}, None)
        if url != official_url("2020-03"):
            raise AssertionError(f"URL não permitida: {url}")
        return Response(url)
    return open_fake


class CompletePipelineTests(unittest.TestCase):
    def setUp(self):
        ctx = patch.dict(os.environ, {"GITHUB_REF_NAME": HOMOLOG_BRANCH})
        ctx.start()
        self.addCleanup(ctx.stop)
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.parent = Path(t.name)
        self.remote = self.parent / "origin.git"
        command(self.parent, "init", "--bare", "--initial-branch=main", str(self.remote))
        seed = self.parent / "seed"
        command(self.parent, "clone", str(self.remote), str(seed))
        command(seed, "config", "user.name", "ANAC fixture")
        command(seed, "config", "user.email", "fixture@example.invalid")
        (seed / "README.md").write_text("fixture de QA, sem ANAC real\n")
        archive = seed / "data/anac/rima"
        receipt = load_manifest(archive)
        store_month(archive, receipt, "2020-01", sample("2020-01"),
                    official_url("2020-01"), "2026-10-28T00:00:00+00:00")
        command(seed, "add", ".")
        command(seed, "commit", "-m", "fixture original")
        command(seed, "push", "origin", "main")
        self.main_sha = command(seed, "rev-parse", "HEAD")
        command(seed, "switch", "-c", HOMOLOG_BRANCH)
        command(seed, "push", "origin", HOMOLOG_BRANCH)
        self.worker = self.clone("worker")
        self.current_sha = command(self.worker, "rev-parse", "HEAD")

    def clone(self, name):
        folder = self.parent / name
        command(self.parent, "clone", "-b", HOMOLOG_BRANCH,
                str(self.remote), str(folder))
        return folder

    def args(self):
        return SimpleNamespace(mode="inicial", start="2020-03", end="2020-03",
                               limit=1, refresh=0,
                               out_dir=self.worker / "data/anac/rima")

    def remote_shas(self):
        return {
            branch: command(self.worker, "ls-remote", "origin",
                            f"refs/heads/{branch}").split()[0]
            for branch in ("main", HOMOLOG_BRANCH)
        }

    def test_full_archiving_commit_clone_and_idempotence(self):
        original = self.remote_shas()
        before_manifest = load_manifest(self.worker / "data/anac/rima")
        old = copy.deepcopy(before_manifest["competencias"]["2020-01"])
        old_blob = (self.worker / old["caminho_sbkp"]).read_bytes()

        status = run(self.args(), opener=fake_opener(),
                     today=date(2026, 10, 28))
        self.assertEqual(status, 0)
        updated = load_manifest(self.worker / "data/anac/rima")
        self.assertEqual(sorted(updated["competencias"]), ["2020-01", "2020-03"])
        self.assertEqual(updated["competencias"]["2020-01"], old)
        self.assertEqual((self.worker / old["caminho_sbkp"]).read_bytes(), old_blob)
        self.assertTrue(_verify_snapshot(self.worker / "data/anac/rima",
                                         updated["competencias"]["2020-03"]))

        audit = inspect(self.worker)
        independent = validate(self.worker)
        self.assertEqual(audit["integridade_arquivos"], "aprovada")
        self.assertEqual(independent["resultado"], "aprovado_tecnicamente")
        self.assertEqual(independent["meses_validados"], 2)
        self.assertEqual(independent["total_registros"], 8)
        self.assertEqual(independent["comparacoes"]["2020-03"]["registros"], 4)

        published = publish(self.worker)
        self.assertEqual(published["status"], "publicado")
        self.assertNotEqual(published["commit"], original[HOMOLOG_BRANCH])
        self.assertEqual(self.remote_shas()["main"], self.main_sha)

        remote = self.clone("remote-check")
        remote_manifest = load_manifest(remote / "data/anac/rima")
        self.assertEqual(sorted(remote_manifest["competencias"]), ["2020-01", "2020-03"])
        self.assertEqual(remote_manifest["competencias"]["2020-01"], old)
        new_entry = remote_manifest["competencias"]["2020-03"]
        self.assertEqual(new_entry["sha256_original"], hashlib.sha256(sample("2020-03")).hexdigest())
        self.assertTrue(_verify_snapshot(remote / "data/anac/rima", new_entry))
        self.assertEqual(inspect(remote)["integridade_arquivos"], "aprovada")
        self.assertEqual(validate(remote)["resultado"], "aprovado_tecnicamente")
        self.assertFalse((remote / "data/comparativo_rima_rma.json").exists())
        self.assertFalse((remote / "index.html").exists())
        self.assertEqual(command(remote, "show", "--pretty=format:", "--name-only", "HEAD").splitlines(),
                         ["data/anac/rima/manifesto.json", new_entry["caminho_sbkp"]])

        self.assertEqual(run(self.args(), opener=fake_opener(),
                             today=date(2026, 10, 28)), 0)
        self.assertEqual(publish(self.worker), {"status": "sem_alteracoes", "commit": None})
        self.assertEqual(self.remote_shas()[HOMOLOG_BRANCH], published["commit"])

    def test_404_keeps_original_commit_and_archive(self):
        original = self.remote_shas()
        folder = self.worker / "data/anac/rima"
        before = (folder / "manifesto.json").read_bytes()
        blob_before = {p.relative_to(folder):p.read_bytes() for p in folder.rglob("*.csv.gz")}
        status = run(self.args(), opener=fake_opener(missing=True),
                     today=date(2026, 10, 28))
        self.assertEqual(status, 1)
        self.assertEqual((folder / "manifesto.json").read_bytes(), before)
        self.assertEqual({p.relative_to(folder):p.read_bytes() for p in folder.rglob("*.csv.gz")},
                         blob_before)
        self.assertEqual(self.remote_shas(), original)

    def test_invalid_weight_blocks_publication_after_staging(self):
        original = self.remote_shas()
        archive = self.worker / "data/anac/rima"
        original_manifest = (archive / "manifesto.json").read_bytes()
        original_gzip = {p.relative_to(archive):p.read_bytes()
                         for p in archive.rglob("*.csv.gz")}
        status = run(self.args(), opener=fake_opener(invalid=True),
                     today=date(2026, 10, 28))
        self.assertEqual(status, 1)
        self.assertEqual((archive / "manifesto.json").read_bytes(), original_manifest)
        self.assertEqual({p.relative_to(archive):p.read_bytes()
                          for p in archive.rglob("*.csv.gz")}, original_gzip)
        self.assertEqual(inspect(self.worker)["integridade_arquivos"], "aprovada")
        self.assertEqual(publish(self.worker), {"status": "sem_alteracoes", "commit": None})
        self.assertEqual(self.remote_shas(), original)


if __name__ == "__main__":
    unittest.main()

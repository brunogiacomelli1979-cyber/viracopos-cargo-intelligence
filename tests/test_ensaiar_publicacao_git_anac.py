"""Testes do ensaio real com Git bare LOCAL: nenhuma chamada externa."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from arquivar_anac_rima import load_manifest, store_month, official_url
from ensaiar_publicacao_git_anac import probe, RemoteProbeError, remote_sha, BRANCH


def git(cwd,*args):
    p=subprocess.run(["git",*args],cwd=cwd,text=True,capture_output=True)
    if p.returncode:
        raise AssertionError(p.stderr)
    return p.stdout.strip()


class RemoteWriteProbeTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.remote=root/"origin.git"
        git(root,"init","--bare","--initial-branch=main",str(self.remote))
        seed=root/"seed"
        git(root,"clone",str(self.remote),str(seed))
        git(seed,"config","user.name","Fixture")
        git(seed,"config","user.email","fixture@example.invalid")
        (seed/"README.md").write_text("fixture\n")
        data=seed/"data/anac/rima"
        manifest=load_manifest(data)
        raw=("ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n"
             "2020;01;SBKP;P;I;100;0\n").encode()
        store_month(data,manifest,"2020-01",raw,official_url("2020-01"),"2026-10-28T00:00:00+00:00")
        git(seed,"add",".")
        git(seed,"commit","-m","fixture")
        git(seed,"push","origin","main")
        git(seed,"switch","-c",BRANCH)
        git(seed,"push","origin",BRANCH)
        self.work=root/"work"
        git(root,"clone","-b",BRANCH,str(self.remote),str(self.work))

    def test_remote_create_read_delete_keeps_base_refs_unchanged(self):
        main=remote_sha(self.work,"main")
        branch=remote_sha(self.work,BRANCH)
        result=probe(self.work,run_id="123",attempt="1",strict=False)
        self.assertEqual(result["status"],"aprovado")
        self.assertTrue(result["ref_removida"])
        self.assertIsNone(remote_sha(self.work,"ci/anac06-probe-123-1"))
        self.assertEqual(remote_sha(self.work,"main"),main)
        self.assertEqual(remote_sha(self.work,BRANCH),branch)

    def test_dirty_checkout_cannot_push(self):
        (self.work/"README.md").write_text("modificado\n")
        with self.assertRaisesRegex(RemoteProbeError,"não está limpo"):
            probe(self.work,run_id="123",strict=False)
        self.assertIsNone(remote_sha(self.work,"ci/anac06-probe-123-1"))

    def test_ref_name_validation(self):
        with self.assertRaisesRegex(RemoteProbeError,"numéricos"):
            probe(self.work,run_id="123/../../main",strict=False)

    def test_outside_actions_is_forbidden_by_default(self):
        with patch.dict(os.environ,{"GITHUB_ACTIONS":"false","GITHUB_REPOSITORY":"other/repo"}):
            with self.assertRaisesRegex(RemoteProbeError,"permitido apenas"):
                probe(self.work,run_id="123")
        self.assertIsNone(remote_sha(self.work,"ci/anac06-probe-123-1"))


if __name__=="__main__":
    unittest.main()

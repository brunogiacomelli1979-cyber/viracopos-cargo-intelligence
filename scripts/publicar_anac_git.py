"""Publicação ANAC/RIMA restrita à branch de homologação.

Bloqueia alterações fora do acervo, remoções e sobrescrita de snapshots.
Audita antes do commit e exige fast-forward; nunca força push.
Não baixa dados da ANAC nem altera o dashboard.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

from auditar_anac_rima import inspect

HOMOLOG_BRANCH = "feature/anac-rima-staging-20261028"
MANIFEST = "data/anac/rima/manifesto.json"
ARCHIVE_PREFIX = "data/anac/rima/sbkp/"


class PublishError(RuntimeError):
    pass


def git(directory, *args, check=True):
    outcome = subprocess.run(
        ["git", *args], cwd=directory, text=True, capture_output=True, check=False
    )
    if check and outcome.returncode:
        raise PublishError(
            f"git {args[0]} falhou: {outcome.stderr.strip()[:700]}"
        )
    return outcome


def publish(directory, branch=HOMOLOG_BRANCH, *, before_push=None):
    root = Path(directory).resolve()
    if branch != HOMOLOG_BRANCH:
        raise PublishError("Publicação bloqueada fora da branch de homologação ANAC")
    current_branch = git(root, "branch", "--show-current").stdout.strip()
    if current_branch != HOMOLOG_BRANCH:
        raise PublishError(f"Checkout incorreto: {current_branch!r}")
    github_branch = os.environ.get("GITHUB_REF_NAME")
    if github_branch and github_branch != branch:
        raise PublishError("GITHUB_REF_NAME divergente da branch autorizada")
    if git(root, "status", "--porcelain", "--untracked-files=no", "--", "data/").returncode:
        raise PublishError("Git status falhou")
    # Proibir entradas pré-estagiadas fora do acervo. Não tocar arquivos pessoais.
    prior = git(root, "diff", "--cached", "--name-only", "-z").stdout
    if prior:
        raise PublishError("Há arquivos previamente preparados para commit; abortar")

    report = inspect(root)
    if report["erros_criticos"]:
        raise PublishError("Acervo ANAC reprovado na auditoria de integridade")
    if not report["competencias"]:
        raise PublishError("Acervo ANAC vazio")

    git(root, "add", "-A", "--", MANIFEST, "data/anac/rima/sbkp")
    changes = git(root, "diff", "--cached", "--name-status", "--", "data/anac/rima").stdout.splitlines()
    if not changes:
        return {"status": "sem_alteracoes", "commit": None}

    # Arquivos gzip adicionais só podem constar no commit se forem
    # citados pelo manifesto como versão corrente ou histórica.
    # O auditor inspeciona snapshots referenciados; sem este controle,
    # um .csv.gz órfão poderia entrar em um commit válido.
    receipt = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    permitted_snapshots = set()
    for entry in receipt["competencias"].values():
        permitted_snapshots.add(entry["caminho_sbkp"])
        for old in entry.get("revisoes", []):
            permitted_snapshots.add(old["caminho_sbkp"])

    manifest_changed = False
    for line in changes:
        pieces = line.split("\t")
        if len(pieces) != 2:
            raise PublishError(f"Alteração Git não reconhecida: {line[:150]!r}")
        status, file_path = pieces
        if file_path == MANIFEST and status in ("A", "M"):
            manifest_changed = True
        elif (file_path.startswith(ARCHIVE_PREFIX)
              and file_path.endswith(".csv.gz") and status == "A"):
            if file_path not in permitted_snapshots:
                raise PublishError(f"Snapshot sem referência no manifesto: {file_path}")
            continue
        else:
            raise PublishError(f"Alteração proibida em ANAC: {status} {file_path}")
    if not manifest_changed:
        raise PublishError("Arquivos novos exigem atualização do manifesto")

    local_head = git(root, "rev-parse", "HEAD").stdout.strip()
    remote_output = git(root, "ls-remote", "origin", f"refs/heads/{branch}").stdout.strip()
    if not remote_output:
        raise PublishError("Branch remota ausente")
    remote_head = remote_output.split()[0]
    if local_head != remote_head:
        raise PublishError("A branch remota avançou: atualizar checkout e repetir auditoria")

    git(root, "config", "user.name", "github-actions[bot]")
    git(root, "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git(root, "commit", "-m", "data: arquivar ANAC RIMA SBKP com recibo auditado")
    new_commit = git(root, "rev-parse", "HEAD").stdout.strip()
    if before_push is not None:
        # Somente para teste de corrida; produção não fornece callback.
        before_push()
    # Sem force; uma atualização concorrente rejeita a publicação e preserva a origem.
    git(root, "push", "origin", f"HEAD:refs/heads/{branch}")
    return {"status": "publicado", "commit": new_commit}


def main():
    parser = argparse.ArgumentParser(description="Publicar apenas dados ANAC/RIMA auditados em homologação")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = publish(args.root)
    print(result)


if __name__ == "__main__":
    main()

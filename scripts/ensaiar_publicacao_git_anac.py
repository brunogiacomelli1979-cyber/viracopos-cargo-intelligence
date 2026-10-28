"""ANAC-06: ensaio de escrita Git remota com ref temporária, sem coleta.

Cria referência isolada ci/anac06-probe-<run>-<attempt> apontando para o
HEAD atual, verifica pelo servidor e REMOVE a referência no mesmo job.
Nunca altera conteúdo, main, homologação, snapshots ou manifesto.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from auditar_anac_rima import inspect

BRANCH = "feature/anac-rima-staging-20261028"
PROJECT = "brunogiacomelli1979-cyber/viracopos-cargo-intelligence"
PREFIX = "ci/anac06-probe-"


class RemoteProbeError(RuntimeError):
    pass


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, text=True,
                            capture_output=True, check=False)
    if result.returncode:
        raise RemoteProbeError(f"git {args[0]} falhou: {result.stderr.strip()[:550]}")
    return result.stdout.strip()


def remote_sha(root, name):
    result = git(root, "ls-remote", "--heads", "origin", f"refs/heads/{name}")
    if not result:
        return None
    lines = result.splitlines()
    if len(lines) != 1 or not lines[0].endswith(f"refs/heads/{name}"):
        raise RemoteProbeError(f"Resposta inesperada de ls-remote para {name}")
    sha = lines[0].split()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RemoteProbeError("SHA remoto inválido")
    return sha


def probe(root, *, run_id, attempt="1", strict=True):
    root = Path(root).resolve()
    if not re.fullmatch(r"[0-9]{1,20}", str(run_id)) or not re.fullmatch(r"[0-9]{1,5}", str(attempt)):
        raise RemoteProbeError("Identificadores numéricos inválidos")
    if strict and (os.environ.get("GITHUB_ACTIONS") != "true"
                   or os.environ.get("GITHUB_REPOSITORY") != PROJECT
                   or os.environ.get("GITHUB_REF_NAME") != BRANCH):
        raise RemoteProbeError("Ensaio remoto permitido apenas no GitHub Actions e branch de homologação")
    name = f"{PREFIX}{run_id}-{attempt}"
    if git(root, "status", "--porcelain"):
        raise RemoteProbeError("Working tree não está limpo; nenhum push de ensaio autorizado")
    if git(root, "diff", "--cached", "--name-only"):
        raise RemoteProbeError("Índice Git não está limpo")
    audit = inspect(root)
    if audit["erros_criticos"] or not audit["competencias"]:
        raise RemoteProbeError("Auditoria de integridade ANAC reprovada")
    head = git(root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise RemoteProbeError("Commit local inválido")
    if remote_sha(root, BRANCH) != head:
        raise RemoteProbeError("HEAD da homologação não corresponde ao remoto")
    main_before = remote_sha(root, "main")
    if not main_before:
        raise RemoteProbeError("Branch principal não encontrada")
    if remote_sha(root, name):
        raise RemoteProbeError("Referência temporária já existe; recusar reutilização")

    created = False
    error = None
    try:
        # A escrita verdadeira ocorre SOMENTE em ref temporária não usada pelo projeto.
        git(root, "push", "origin", f"HEAD:refs/heads/{name}")
        created = True
        if remote_sha(root, name) != head:
            raise RemoteProbeError("SHA do ensaio não confere no servidor")
    except Exception as exc:
        error = exc
    finally:
        # Se push retornou erro mas criou ref, também tentar limpar com verificação.
        existing = remote_sha(root, name)
        if existing is not None:
            if existing != head:
                raise RemoteProbeError("Referência temporária aponta para SHA não esperado; limpeza manual necessária")
            try:
                git(root, "push", "origin", f":refs/heads/{name}")
            except Exception as exc:
                raise RemoteProbeError(f"Falha ao remover ref temporária {name}: {exc}") from exc
        if remote_sha(root, name) is not None:
            raise RemoteProbeError(f"Referência temporária persistiu: {name}")
    if error is not None:
        raise RemoteProbeError(f"Criação remota do ensaio falhou: {error}") from error
    if not created:
        raise RemoteProbeError("Nenhuma ref foi criada")
    if remote_sha(root, BRANCH) != head or remote_sha(root, "main") != main_before:
        raise RemoteProbeError("Branch principal/homologação mudou durante ensaio; investigar")
    return {
        "status": "aprovado", "teste": "criacao_e_exclusao_de_ref_temporaria",
        "ref_temporaria": name, "ref_removida": True,
        "homologacao_inalterada": True, "main_inalterada": True,
        "sha_homologacao": head, "sha_main": main_before,
        "competencias_arquivadas": len(audit["competencias"]),
        "novos_dados_anac": False, "publicacao_dashboard": False,
        "limite": "Nao comprova coleta ANAC nem commit versionado na branch de homologacao"
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    status = 0
    try:
        report = probe(args.root, run_id=os.environ.get("GITHUB_RUN_ID", ""),
                       attempt=os.environ.get("GITHUB_RUN_ATTEMPT", ""))
    except Exception as exc:
        report = {"status": "reprovado", "erro": str(exc),
                  "acao": "Consultar job e confirmar se existe ref ci/anac06-probe-*"}
        status = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(status)


if __name__ == "__main__":
    main()

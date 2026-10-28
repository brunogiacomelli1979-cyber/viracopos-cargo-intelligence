"""ANAC-06: verifica commit remoto e conteúdo recém-publicado, sem coletar dados."""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path
from auditar_anac_rima import inspect
from validar_agrupamento_rima import validate
from publicar_anac_git import HOMOLOG_BRANCH, MANIFEST


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(f"git {args[0]}: {result.stderr.strip()[:500]}")
    return result.stdout.strip()


def remote(root, name):
    result = git(root, "ls-remote", "--heads", "origin", f"refs/heads/{name}")
    if not result or len(result.splitlines()) != 1:
        raise ValueError(f"Branch remota ausente ou ambígua: {name}")
    return result.split()[0]


def verify(root, base, main_before, month="2020-03"):
    root = Path(root).resolve()
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (base, main_before)):
        raise ValueError("SHA Git inválido")
    if month != "2020-03":
        raise ValueError("Piloto restrito à competência 2020-03")
    if remote(root, "main") != main_before:
        raise ValueError("Branch principal modificada durante a publicação")

    after = remote(root, HOMOLOG_BRANCH)
    git(root, "fetch", "--no-tags", "origin",
        f"refs/heads/{HOMOLOG_BRANCH}:refs/remotes/origin/{HOMOLOG_BRANCH}")
    if git(root, "rev-parse", f"refs/remotes/origin/{HOMOLOG_BRANCH}") != after:
        raise ValueError("SHA remoto não confirmado após fetch")
    if base != after:
        git(root, "merge-base", "--is-ancestor", base, after)

    changes = {}
    if base != after:
        for line in git(root, "diff", "--name-status", "--no-renames", base, after).splitlines():
            parts = line.split("\t")
            if len(parts) != 2 or parts[0] not in ("A", "M") or parts[1] in changes:
                raise ValueError("Mudança Git inesperada no push")
            changes[parts[1]] = parts[0]

    original = json.loads(git(root, "show", f"{base}:{MANIFEST}"))
    with tempfile.TemporaryDirectory(prefix="anac06-remote-") as temp:
        checkout = Path(temp) / "checkout"
        git(root, "worktree", "add", "--detach", str(checkout), after)
        try:
            latest = json.loads((checkout / MANIFEST).read_text(encoding="utf-8"))
            old_months = original["competencias"]
            months = latest["competencias"]
            if any(months.get(key) != value for key, value in old_months.items()):
                raise ValueError("Dados anteriores foram alterados")
            new_months = sorted(set(months) - set(old_months))
            if new_months not in ([], [month]):
                raise ValueError(f"Meses inesperados: {new_months}")

            audit = inspect(checkout)
            sums = validate(checkout)
            if audit["erros_criticos"] or sums["erros"] or sums["resultado"] != "aprovado_tecnicamente":
                raise ValueError("Acervo remoto reprovou auditoria")
            if month not in months:
                raise ValueError("Competência solicitada não encontrada")
            if base != after:
                path = months[month]["caminho_sbkp"]
                if (new_months != [month] or
                        changes != {MANIFEST: "M", path: "A"} or
                        f"/versoes/{month}/" not in path or
                        not path.endswith(".csv.gz")):
                    raise ValueError(f"Arquivos publicados fora do escopo: {changes}")
                state = "novo_mes_confirmado"
            else:
                if changes or new_months:
                    raise ValueError("Ausência de commit sem idempotência")
                state = "repeticao_sem_mudancas"
            return {"status": state, "mes": month, "antes": base, "remoto": after,
                    "main_preservada": True, "meses_novos": new_months,
                    "arquivos_alterados": changes, "registros_totais": sums["total_registros"],
                    "integridade": audit["integridade_arquivos"],
                    "nenhuma_alteracao_dashboard": True}
        finally:
            git(root, "worktree", "remove", "--force", str(checkout))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--main-sha", required=True)
    parser.add_argument("--month", default="2020-03")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(Path(__file__).resolve().parents[1], args.base, args.main_sha, args.month)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

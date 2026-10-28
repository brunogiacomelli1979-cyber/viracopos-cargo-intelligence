"""Simula inclusao de UMA competencia ANAC em copia descartavel do acervo.

Nao altera o manifesto historico, nao executa Git, rede ou deploy.
Exige bruto com SHA confirmado e executa auditores completos em copia local.
"""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from acervo_bruto_anac import digest_file
from auditar_anac_rima import inspect
from reprocessar_bruto_anac import prepare, locate_original
from validar_agrupamento_rima import validate

ROOT = Path(__file__).resolve().parents[1]


def _qa(repo):
    a = inspect(repo)
    b = validate(repo)
    if (a["erros_criticos"] or a["integridade_arquivos"] != "aprovada"
            or b["erros"] or b["resultado"] != "aprovado_tecnicamente"):
        raise ValueError(f"Auditoria reprovada: {a['erros_criticos'][:2]}, {b['erros'][:2]}")
    return a, b


def simulate(vault, month, sha, stage_dir, base_repo=ROOT):
    base_repo = Path(base_repo).resolve()
    manifest_path = base_repo / "data/anac/rima/manifesto.json"
    if not manifest_path.is_file():
        raise ValueError("Manifesto base inexistente; simulacao exige base auditada")
    original_manifest_sha, _ = digest_file(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "anac_rima_sbkp_v1" or manifest.get("aeroporto") != "SBKP":
        raise ValueError("Contrato de manifesto ANAC desconhecido")
    if month in manifest.get("competencias", {}):
        raise ValueError("Competencia ja arquivada; revisar versao exige processo distinto")
    # Nao depender de data atual nem estimar versao: recusa sem recibo exato.
    original, receipt = locate_original(vault, month, sha)
    staged = prepare(vault, month, sha, stage_dir)
    pack = Path(staged["pasta"])
    info = staged["resumo"]
    if (info.get("schema") != "anac-rima-sbkp-offline-v1"
            or info.get("estado") != "staging_validado_local_nao_publicado"
            or info.get("sha256_original") != sha
            or info.get("competencia") != month
            or info.get("bytes_original") != receipt["bytes"]):
        raise ValueError("Pacote staging nao corresponde ao bruto verificado")
    with tempfile.TemporaryDirectory(prefix="anac-candidate-") as temp:
        trial = Path(temp)
        dest = trial / "data/anac/rima"
        shutil.copytree(base_repo / "data/anac/rima", dest)
        before, cross_before = _qa(trial)
        trial_manifest = json.loads((dest / "manifesto.json").read_text(encoding="utf-8"))
        if month in trial_manifest["competencias"]:
            raise ValueError("Competencia apareceu na copia base; cancelar")
        filename = info["sha256_gzip"] + ".csv.gz"
        rel = Path("data/anac/rima/sbkp") / month[:4] / "versoes" / month / filename
        target = trial / rel
        if target.exists():
            raise ValueError("Snapshot da competencia ja existe")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pack / "sbkp.csv.gz", target)
        if digest_file(target) != (info["sha256_gzip"], info["bytes_gzip"]):
            raise ValueError("Copia do recorte diverge")
        trial_manifest["competencias"][month] = {
            "url_original": receipt["url"],
            "coletado_em_utc": receipt["capturado_em_utc"],
            "sha256_original": sha,
            "bytes_original": receipt["bytes"],
            "caminho_sbkp": rel.as_posix(),
            "sha256_sbkp_gzip": info["sha256_gzip"],
            "bytes_sbkp_gzip": info["bytes_gzip"],
            "revisoes": [],
            "linhas_origem": info["linhas_origem"],
            "linhas_sbkp": info["linhas_sbkp"],
            "colunas": info["colunas"],
            "codificacao_origem": "utf-8" if info["codificacao_original"] == "utf-8-sig" else info["codificacao_original"],
            "conteudo_sbkp_sha256": info["sha256_csv_sbkp"],
        }
        (dest / "manifesto.json").write_text(
            json.dumps(trial_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        after, cross_after = _qa(trial)
        old_keys = set(before["competencias"])
        new_keys = set(after["competencias"])
        if (new_keys != old_keys | {month}
                or after["total_registros"] != before["total_registros"] + info["linhas_sbkp"]):
            raise ValueError("Cobertura/contagem apos simulacao nao confere")
        for prior in old_keys:
            if before["competencias"][prior] != after["competencias"][prior]:
                raise ValueError(f"Competencia preexistente modificada: {prior}")
        if cross_before["total_registros"] + info["linhas_sbkp"] != cross_after["total_registros"]:
            raise ValueError("Auditorias independentes divergem na contagem")
        if (digest_file(manifest_path)[0] != original_manifest_sha
                or not original.is_file()
                or digest_file(original) != (sha, receipt["bytes"])):
            raise ValueError("Origem/manifesto mudou durante a simulacao")
        return {
            "estado": "simulacao_aprovada_nao_publicada",
            "competencia": month, "sha256_original": sha,
            "meses_base": len(old_keys), "meses_simulados": len(new_keys),
            "novos_registros_sbkp": info["linhas_sbkp"],
            "registros_simulados": after["total_registros"],
            "checks": ["auditoria_base", "auditoria_candidato", "agregacao_independente",
                       "integridade_hash", "preservacao_de_meses_anteriores"],
            "observacao": "Candidato descartado apos validacao; nenhuma alteracao ao Git, main ou manifesto original"
        }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--acervo", type=Path, required=True)
    p.add_argument("--competencia", required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--staging", type=Path, required=True)
    p.add_argument("--repo-base", type=Path, default=ROOT)
    args = p.parse_args()
    result = simulate(args.acervo, args.competencia, args.sha256, args.staging, args.repo_base)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

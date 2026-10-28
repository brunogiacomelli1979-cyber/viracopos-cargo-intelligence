"""Ensaio G2: prova tecnica de backup, recuperacao e replay offline.

Nunca coleta dados, altera manifesto, executa Git ou aprova G2 operacional.
Exige acervo original existente e dois caminhos existentes para os volumes.
"""
import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from acervo_bruto_anac import audit, digest_file
from backup_acervo_anac import (
    _inventory, _not_nested, _outside_git, backup, restore, verify,
)
from reprocessar_bruto_anac import prepare, locate_original

SCHEMA = "anac-g2-drill-v1"


def _existing_dir(path, name):
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{name} deve ser diretorio existente sem symlink")
    if not os.access(path, os.R_OK | os.X_OK):
        raise ValueError(f"{name} sem permissao de leitura/travessia")
    resolved = path.resolve()
    _outside_git(resolved)
    return resolved


def _check_layout(source, backup_root, restore_root):
    source = _existing_dir(source, "Cofre primario")
    backup_root = _existing_dir(backup_root, "Diretorio de backups")
    restore_root = _existing_dir(restore_root, "Diretorio-base de recuperacao")
    for x, y in ((source, backup_root), (source, restore_root), (backup_root, restore_root)):
        _not_nested(x, y)
    if not os.access(backup_root, os.W_OK):
        raise ValueError("Volume de backups nao gravavel")
    if not os.access(restore_root, os.W_OK):
        raise ValueError("Volume de restauracao nao gravavel")
    return source, backup_root, restore_root


def _assert_quiescent(source):
    """Um cofre com escrita pendente nao pode produzir snapshot certificado."""
    allowed = {"objects", "receipts", "incoming"}
    for entry in source.iterdir():
        if entry.name not in allowed or entry.is_symlink() or not entry.is_dir():
            raise ValueError("Cofre possui entrada inesperada ou symlink; verificar antes do backup")
    pending = source / "incoming"
    if pending.is_dir() and any(pending.iterdir()):
        raise ValueError("Cofre possui aquisicao parcial em incoming; aguardar tratamento")
    if pending.is_symlink():
        raise ValueError("Incoming e um symlink; falha fechada")


def _check_devices(primary, backup_root):
    # Diferentes st_dev indicam volumes distintos para o SO, mas nao
    # comprovam discos fisicamente independentes nem retencao externa.
    a, b = primary.stat().st_dev, backup_root.stat().st_dev
    return {"volumes_so_distintos": a != b,
            "ressalva": "st_dev distinto nao comprova independencia fisica, offsite ou imutabilidade"}


def _data_bytes(inventory):
    return sum(row["bytes"] for row in inventory)


def drill(source, backup_root, recovery_parent, month, sha256, *, mode="simulado"):
    """Roda backup, verifica, restaura em pasta nova e reprocessa competencia.

    O resultado NUNCA aprova G2 operacional: falta comprovacao externa de
    protecao, retencao, periodicidade, propriedade e segunda localizacao.
    """
    if mode not in ("simulado", "pre_homologacao"):
        raise ValueError("Modo invalido")
    source, backup_root, recovery_parent = _check_layout(
        source, backup_root, recovery_parent)
    devices = _check_devices(source, backup_root)
    if mode == "pre_homologacao" and not devices["volumes_so_distintos"]:
        raise ValueError("Pre-homologacao exige volumes distintos no SO; ainda nao prova midia independente")
    _assert_quiescent(source)
    before = audit(source)
    if not before["aprovado"]:
        raise ValueError(f"Cofre fonte reprovado: {before['erros'][:2]}")
    source_inventory = _inventory(source)
    original, receipt = locate_original(source, month, sha256)
    if digest_file(original) != (sha256, receipt["bytes"]):
        raise ValueError("Bruto de teste nao confere antes do ensaio")

    started = time.monotonic()
    backed_up = backup(source, backup_root)
    snap = backed_up["snapshot_id"]
    verified = verify(backup_root, snap)
    if verified["snapshot_id"] != snap:
        raise ValueError("Snapshot verificado incorretamente")
    backup_seconds = round(time.monotonic() - started, 3)

    # Diretorio final reservado dentro de uma pasta criada pela propria rotina:
    # um UUID interno de TemporaryDirectory evita reaproveitamento acidental.
    # Mantemos a pasta restaurada apenas durante o ensaio: o backup sobrevive.
    with tempfile.TemporaryDirectory(prefix="g2-drill-", dir=recovery_parent) as temp:
        temp_root = Path(temp)
        recovered = temp_root / "recovered"
        t_restore = time.monotonic()
        restored = restore(backup_root, snap, recovered)
        restore_seconds = round(time.monotonic() - t_restore, 3)
        if restored["estado"] != "restaurado_em_novo_diretorio":
            raise ValueError("Restauracao nao comprovada")
        if _inventory(recovered) != source_inventory:
            raise ValueError("Inventario recuperado nao corresponde ao cofre inicial")
        if not audit(recovered)["aprovado"]:
            raise ValueError("Cofre restaurado reprovado")
        t_replay = time.monotonic()
        staged = prepare(recovered, month, sha256, temp_root / "staging")
        replay_seconds = round(time.monotonic() - t_replay, 3)
        meta = staged["resumo"]
        if (meta.get("sha256_original") != sha256
                or meta.get("competencia") != month
                or meta.get("estado") != "staging_validado_local_nao_publicado"):
            raise ValueError("Reprocessamento nao corresponde ao bruto escolhido")
        if not (temp_root / "staging" / month / sha256 / "sbkp.csv.gz").is_file():
            raise ValueError("Staging recuperado ausente")
        if _inventory(recovered) != source_inventory:
            raise ValueError("Recuperado mudou durante reprocessamento")
    _assert_quiescent(source)
    if _inventory(source) != source_inventory:
        raise ValueError("Acervo primario mudou durante o ensaio")
    if verify(backup_root, snap)["snapshot_id"] != snap:
        raise ValueError("Snapshot mudou durante o ensaio")

    return {
        "schema": SCHEMA,
        "estado": "ensaio_tecnico_aprovado_sem_homologacao_operacional",
        "modo": mode,
        "snapshot_id": snap,
        "competencia_reprocessada": month,
        "sha256_original": sha256,
        "arquivos_verificados": len(source_inventory),
        "recibos_verificados": verified["recibos"],
        "bytes_verificados": _data_bytes(source_inventory),
        "linhas_sbkp_reprocessadas": meta["linhas_sbkp"],
        "medicoes_segundos": {
            "backup": backup_seconds, "restauracao": restore_seconds,
            "reprocessamento": replay_seconds},
        "preflight_dispositivos": devices,
        "copia_restaurada_temporaria_removida_apos_auditoria": True,
        "snapshot_salvo_no_destino_informado": True,
        "durabilidade_fisica_comprovada": False,
        "g2_operacional_aprovado": False,
        "pendencias_externas": [
            "comprovar dispositivos fisicamente independentes ou backup offsite",
            "registrar propriedade e politica de retencao/versionamento/imutabilidade",
            "comprovar controle de acesso e teste de recuperacao no ambiente real",
            "selecionar destino persistente e aprovar procedimento pelo proprietario",
        ],
        "observacao": (
            "Sem rede, dados ANAC adicionais ou alteracao do manifesto. "
            "A aprovacao G2 exige evidencias externas e revisao humana."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cofre", required=True, type=Path)
    parser.add_argument("--backups", required=True, type=Path)
    parser.add_argument("--recuperacao-parent", required=True, type=Path)
    parser.add_argument("--competencia", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--modo", choices=("simulado", "pre_homologacao"), default="simulado")
    parser.add_argument("--evidencia", type=Path)
    args = parser.parse_args()
    location = None
    if args.evidencia:
        location = args.evidencia.resolve()
        _outside_git(location)
        if location.exists():
            raise ValueError("Relatorio ja existente: nao sobrescrever evidencia de recuperacao")
        if not location.parent.is_dir():
            raise ValueError("Diretorio pai da evidencia nao existe")
    result = drill(args.cofre, args.backups, args.recuperacao_parent,
                   args.competencia, args.sha256, mode=args.modo)
    data = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if location is not None:
        with location.open("x", encoding="utf-8") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    print(data, end="")


if __name__ == "__main__":
    main()

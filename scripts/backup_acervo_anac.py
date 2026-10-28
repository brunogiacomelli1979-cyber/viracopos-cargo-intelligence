"""Snapshots verificados do cofre ANAC em outro diretorio, sem rede/Git.

O backup guarda BRUTOS e RECIBOS, nunca altera manifesto SBKP ou dashboard.
Restauracao somente para diretorio NOVO: nao sobrescreve o cofre original.
Use um segundo volume/dispositivo para protecao real contra perda fisica.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath

from acervo_bruto_anac import ROOT, CHUNK, audit, digest_file

SCHEMA = "anac-vault-backup-v1"
HASH = re.compile(r"[0-9a-f]{64}")
MONTH = re.compile(r"20\d{2}-(0[1-9]|1[0-2])")


def _outside_git(path):
    if Path(path).resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Cofre ou backup sob repositorio Git nao permitido")


def _not_nested(a, b):
    left, right = Path(a).resolve(), Path(b).resolve()
    if left == right or left.is_relative_to(right) or right.is_relative_to(left):
        raise ValueError("Origem e destino devem ser diretorios separados e nao aninhados")


def _valid_rel(name):
    if not isinstance(name, str) or "\\" in name or name.startswith("/"):
        raise ValueError("Caminho relativo invalido")
    parts = PurePosixPath(name).parts
    if len(parts) != 3 or "." in parts or ".." in parts:
        raise ValueError("Caminho de arquivo fora do contrato")
    group, middle, filename = parts
    if group == "objects":
        if (not re.fullmatch(r"[0-9a-f]{2}", middle)
                or not filename.endswith(".csv") or not HASH.fullmatch(filename[:-4])
                or filename[:2] != middle):
            raise ValueError("Objeto com caminho invalido")
    elif group == "receipts":
        if not MONTH.fullmatch(middle) or middle < "2020-01" or not filename.endswith(".json") or not HASH.fullmatch(filename[:-5]):
            raise ValueError("Recibo com caminho invalido")
    else:
        raise ValueError("Somente objects/ e receipts/ podem ser preservados")
    return name


def _inventory(root):
    root = Path(root)
    entries = []
    for group in ("objects", "receipts"):
        parent = root / group
        if parent.is_symlink():
            raise ValueError("Link simbolico de pasta nao permitido")
        for path in sorted(parent.rglob("*")):
            if path.is_symlink():
                raise ValueError("Link simbolico nao permitido")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError("Entrada especial nao permitida")
            name = path.relative_to(root).as_posix()
            _valid_rel(name)
            sha, size = digest_file(path)
            entries.append({"path": name, "sha256": sha, "bytes": size})
    return sorted(entries, key=lambda e: e["path"])


def _canonical(entries):
    return json.dumps(entries, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _snapshot_id(entries):
    return hashlib.sha256(_canonical(entries)).hexdigest()


def _validate_entries(entries):
    if not isinstance(entries, list) or not entries:
        raise ValueError("Inventario do backup vazio ou invalido")
    found = set()
    for e in entries:
        if not isinstance(e, dict) or set(e) != {"path", "sha256", "bytes"}:
            raise ValueError("Entrada do backup invalida")
        name = _valid_rel(e["path"])
        if name in found:
            raise ValueError("Caminho repetido no backup")
        found.add(name)
        if (not isinstance(e["sha256"], str) or not HASH.fullmatch(e["sha256"])
                or type(e["bytes"]) is not int or e["bytes"] < 1):
            raise ValueError("Hash/tamanho invalido no manifesto")
    return found


def _copy_verified(src, dst, sha, size):
    dst.parent.mkdir(parents=True, exist_ok=True)
    h, count = hashlib.sha256(), 0
    with src.open("rb") as stream, dst.open("xb") as output:
        while block := stream.read(CHUNK):
            count += len(block)
            h.update(block)
            output.write(block)
        output.flush()
        os.fsync(output.fileno())
    if h.hexdigest() != sha or count != size:
        raise ValueError("Origem mudou durante a copia ou conteudo corrompido")
    if digest_file(dst) != (sha, size):
        raise ValueError("Copia nao confere byte a byte pelo SHA-256")


def _audit_or_fail(path):
    result = audit(path)
    if not result["aprovado"]:
        raise ValueError(f"Auditoria do cofre reprovada: {result['erros'][:2]}; orfaos={result['objetos_orfaos'][:2]}")
    return result


def verify(backup_root, snapshot_id):
    backup_root = Path(backup_root).resolve()
    _outside_git(backup_root)
    if not HASH.fullmatch(snapshot_id):
        raise ValueError("ID de snapshot invalido")
    snapshot = backup_root / "snapshots" / snapshot_id
    if snapshot.is_symlink() or (backup_root / "snapshots").is_symlink():
        raise ValueError("Diretorio de backup nao pode ser link simbolico")
    manifest_path = snapshot / "manifesto_backup.json"
    if manifest_path.is_symlink():
        raise ValueError("Manifesto de backup nao pode ser link")
    info = json.loads(manifest_path.read_text(encoding="utf-8"))
    if info.get("schema") != SCHEMA or info.get("snapshot_id") != snapshot_id:
        raise ValueError("Manifesto do backup nao corresponde ao snapshot")
    entries = info.get("arquivos")
    expected = _validate_entries(entries)
    if _snapshot_id(entries) != snapshot_id:
        raise ValueError("Inventario nao corresponde ao identificador de conteudo")
    files = snapshot / "files"
    if files.is_symlink():
        raise ValueError("Link simbolico no backup")
    actual = _inventory(files)
    if {e["path"] for e in actual} != expected or actual != entries:
        raise ValueError("Backup incompleto, alterado ou com arquivos inesperados")
    _audit_or_fail(files)
    return {"estado": "backup_verificado", "snapshot_id": snapshot_id,
            "arquivos": len(entries), "recibos": len([e for e in entries if e["path"].startswith("receipts/")])}


def backup(source, backup_root):
    source, backup_root = Path(source).resolve(), Path(backup_root).resolve()
    _outside_git(source)
    _outside_git(backup_root)
    _not_nested(source, backup_root)
    if not source.is_dir():
        raise ValueError("Cofre bruto nao existe")
    _audit_or_fail(source)
    entries = _inventory(source)
    _validate_entries(entries)
    snapshot_id = _snapshot_id(entries)
    target = backup_root / "snapshots" / snapshot_id
    if target.exists():
        return {**verify(backup_root, snapshot_id), "estado": "backup_ja_existente"}
    (backup_root / "snapshots").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="backup-incompleto-", dir=backup_root) as temporary:
        tmp = Path(temporary)
        for item in entries:
            _copy_verified(source / item["path"], tmp / "files" / item["path"],
                           item["sha256"], item["bytes"])
        meta = {"schema": SCHEMA, "snapshot_id": snapshot_id, "arquivos": entries}
        (tmp / "manifesto_backup.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8")
        # Conferir o snapshot temporario antes de torna-lo visivel.
        if _inventory(tmp / "files") != entries:
            raise ValueError("Backup temporario difere da origem")
        _audit_or_fail(tmp / "files")
        if target.exists():
            return {**verify(backup_root, snapshot_id), "estado": "backup_ja_existente"}
        os.rename(tmp, target)
    return verify(backup_root, snapshot_id)


def restore(backup_root, snapshot_id, destination):
    backup_root, destination = Path(backup_root).resolve(), Path(destination).resolve()
    _outside_git(backup_root)
    _outside_git(destination)
    _not_nested(backup_root, destination)
    checked = verify(backup_root, snapshot_id)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Restauracao so pode criar diretorio NOVO; nao sobrescrever")
    source = backup_root / "snapshots" / snapshot_id / "files"
    entries = json.loads((source.parent / "manifesto_backup.json").read_text(encoding="utf-8"))["arquivos"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="restauracao-incompleta-", dir=destination.parent) as temporary:
        tmp = Path(temporary)
        for item in entries:
            _copy_verified(source / item["path"], tmp / item["path"],
                           item["sha256"], item["bytes"])
        if _inventory(tmp) != entries:
            raise ValueError("Restauracao com arquivos diferentes do backup")
        _audit_or_fail(tmp)
        if destination.exists():
            raise ValueError("Destino criado por outra operacao; nao sobrescrever")
        os.rename(tmp, destination)
    _audit_or_fail(destination)
    if _inventory(destination) != entries:
        raise ValueError("Falha na verificacao apos restauracao")
    return {**checked, "estado": "restaurado_em_novo_diretorio", "destino": str(destination)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="comando", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--origem", type=Path, required=True)
    b.add_argument("--destino", type=Path, required=True)
    v = sub.add_parser("verificar")
    v.add_argument("--backup", type=Path, required=True)
    v.add_argument("--snapshot", required=True)
    r = sub.add_parser("restaurar")
    r.add_argument("--backup", type=Path, required=True)
    r.add_argument("--snapshot", required=True)
    r.add_argument("--novo-cofre", type=Path, required=True)
    args = p.parse_args()
    result = (backup(args.origem, args.destino) if args.comando == "backup"
              else verify(args.backup, args.snapshot) if args.comando == "verificar"
              else restore(args.backup, args.snapshot, args.novo_cofre))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

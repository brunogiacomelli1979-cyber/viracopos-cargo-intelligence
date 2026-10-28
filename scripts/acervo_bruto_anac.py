"""Acervo local e imutavel de CSVs ANAC originais (offline, sem download).

A copia e feita em blocos; a raiz do acervo deve ser persistente e FORA do Git.
Nao modifica o manifesto SBKP nem publica dados no dashboard.
"""
import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 250_000_000
CHUNK = 1024 * 1024
MONTH = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])$")


def validate_input(month, url, store):
    if not MONTH.fullmatch(month) or month < "2020-01":
        raise ValueError("Competencia invalida ou anterior a 2020-01")
    parsed = urlparse(url)
    yyyy, mm = month.split("-")
    if (parsed.scheme != "https" or parsed.netloc != "sistemas.anac.gov.br"
            or parsed.query or parsed.fragment
            or not parsed.path.endswith(f"/{yyyy}/Movimentacoes_Aeroportuarias_{yyyy}{mm}.csv")
            or "/dadosabertos/" not in parsed.path):
        raise ValueError("URL nao corresponde ao CSV oficial da competencia")
    if store.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Acervo bruto deve ficar fora do repositorio Git")


def digest_file(path):
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as handle:
        while True:
            piece = handle.read(CHUNK)
            if not piece:
                break
            digest.update(piece)
            count += len(piece)
    return digest.hexdigest(), count


def _put_immutable(tmp, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(tmp, destination)
    except FileExistsError:
        if digest_file(tmp) != digest_file(destination):
            raise ValueError("Objeto imutavel existente diverge")
    finally:
        tmp.unlink(missing_ok=True)


def register(source, month, url, store, captured_at=None, limit=MAX_BYTES):
    source, store = Path(source), Path(store)
    validate_input(month, url, store)
    if not source.is_file():
        raise ValueError("Arquivo de origem local nao existe")
    store.mkdir(parents=True, exist_ok=True)
    staging = store / "incoming"
    staging.mkdir(parents=True, exist_ok=True)
    pending = None
    try:
        with tempfile.NamedTemporaryFile(dir=staging, prefix="raw-", suffix=".partial", delete=False) as target:
            pending = Path(target.name)
            size = 0
            h = hashlib.sha256()
            prefix = bytearray()
            with source.open("rb") as handle:
                while chunk := handle.read(CHUNK):
                    size += len(chunk)
                    if size > limit:
                        raise ValueError("CSV nacional excede limite configurado")
                    if len(prefix) < 8192:
                        prefix.extend(chunk[:8192 - len(prefix)])
                    h.update(chunk)
                    target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        if not size or b"<html" in bytes(prefix).lower() or b"NR_AEROPORTO_REFERENCIA" not in prefix:
            raise ValueError("Arquivo vazio, HTML ou cabecalho CSV nao reconhecido")
        hexdigest = h.hexdigest()
        destination = store / "objects" / hexdigest[:2] / f"{hexdigest}.csv"
        _put_immutable(pending, destination)
        pending = None
        if digest_file(destination) != (hexdigest, size):
            raise ValueError("Copia do bruto nao confere com origem")
        receipt = store / "receipts" / month / f"{hexdigest}.json"
        if receipt.exists():
            existing = json.loads(receipt.read_text(encoding="utf-8"))
            if (existing.get("sha256") != hexdigest or existing.get("bytes") != size
                    or existing.get("competencia") != month or existing.get("url") != url):
                raise ValueError("Recibo imutavel existente em conflito")
            return existing
        info = {"schema": "anac-original-raw-v1", "competencia": month,
                "url": url, "sha256": hexdigest, "bytes": size,
                "objeto": destination.relative_to(store).as_posix(),
                "capturado_em_utc": captured_at or datetime.now(timezone.utc).isoformat(),
                "status": "bruto_preservado_nao_validado"}
        receipt.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=receipt.parent, prefix="receipt-", suffix=".partial", delete=False) as fh:
            temp_receipt = Path(fh.name)
            fh.write((json.dumps(info, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            fh.flush()
            os.fsync(fh.fileno())
        _put_immutable(temp_receipt, receipt)
        existing = json.loads(receipt.read_text(encoding="utf-8"))
        if {k: existing.get(k) for k in ("schema", "competencia", "url", "sha256", "bytes", "objeto", "status")} != {k: info[k] for k in ("schema", "competencia", "url", "sha256", "bytes", "objeto", "status")}:
            raise ValueError("Colisao concorrente de recibo")
        return existing
    finally:
        if pending:
            pending.unlink(missing_ok=True)


def audit(store):
    store = Path(store)
    failures, checked, referenced = [], 0, set()
    for receipt in sorted((store / "receipts").glob("????-??/*.json")):
        try:
            info = json.loads(receipt.read_text(encoding="utf-8"))
            if info.get("schema") != "anac-original-raw-v1":
                raise ValueError("Contrato de recibo invalido")
            month, sha = info["competencia"], info["sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise ValueError("Digest invalido")
            validate_input(month, info["url"], store)
            if receipt != store / "receipts" / month / f"{sha}.json":
                raise ValueError("Recibo fora do caminho da competencia")
            object_path = store / "objects" / sha[:2] / f"{sha}.csv"
            if info.get("objeto") != object_path.relative_to(store).as_posix():
                raise ValueError("Caminho de objeto inconsistente")
            if digest_file(object_path) != (sha, info["bytes"]):
                raise ValueError("Hash ou tamanho divergente")
            referenced.add(object_path.resolve())
            checked += 1
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            failures.append({"recibo": str(receipt), "erro": str(exc)})
    orphan = [p.relative_to(store).as_posix() for p in (store / "objects").glob("*/*.csv") if p.resolve() not in referenced]
    return {"recibos_validos": checked, "objetos_orfaos": orphan,
            "erros": failures, "aprovado": not failures and not orphan}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="comando", required=True)
    incoming = commands.add_parser("registrar", help="Preservar CSV local; sem baixar")
    incoming.add_argument("--arquivo", type=Path, required=True)
    incoming.add_argument("--competencia", required=True)
    incoming.add_argument("--url", required=True)
    incoming.add_argument("--acervo", type=Path, required=True)
    inspection = commands.add_parser("auditar", help="Conferir hashes e objetos sem rede")
    inspection.add_argument("--acervo", type=Path, required=True)
    args = parser.parse_args()
    result = (register(args.arquivo, args.competencia, args.url, args.acervo)
              if args.comando == "registrar" else audit(args.acervo))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.comando == "auditar" and not result["aprovado"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

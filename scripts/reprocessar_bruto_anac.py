"""Reprocessa UM CSV nacional ANAC ja preservado, inteiramente offline.

Leitura do original em fluxo (sem carregar o CSV nacional em RAM).
Escreve somente staging isolado. NUNCA altera data/anac/rima,
manifesto oficial, Git ou dashboard. Nenhuma chamada de rede.
"""
import argparse
import codecs
import csv
import gzip
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from acervo_bruto_anac import CHUNK, digest_file, validate_input
from processar_anac_rima import process_file

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"ANO", "MES", "NR_AEROPORTO_REFERENCIA", "NR_MOVIMENTO_TIPO",
            "NR_NATUREZA", "QT_CARGA", "QT_CORREIO"}
SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_CSV = 100_000_000
MAX_GZIP = 10_000_000


def locate_original(vault, month, sha256):
    vault = Path(vault).resolve()
    if not SHA.fullmatch(sha256):
        raise ValueError("SHA-256 do recibo deve ter 64 digitos hexadecimais")
    receipt_path = vault / "receipts" / month / f"{sha256}.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "anac-original-raw-v1" or receipt.get("status") != "bruto_preservado_nao_validado":
        raise ValueError("Contrato ou status do recibo bruto incompativel")
    if receipt.get("competencia") != month or receipt.get("sha256") != sha256:
        raise ValueError("Recibo nao pertence a competencia/versao solicitada")
    validate_input(month, receipt["url"], vault)
    raw = vault / "objects" / sha256[:2] / f"{sha256}.csv"
    if receipt.get("objeto") != raw.relative_to(vault).as_posix():
        raise ValueError("Caminho bruto indicado pelo recibo nao confere")
    if raw.is_symlink() or not raw.is_file():
        raise ValueError("Objeto bruto inexistente ou link simbolico nao permitido")
    if type(receipt.get("bytes")) is not int or receipt["bytes"] < 1:
        raise ValueError("Tamanho do original invalido")
    if digest_file(raw) != (sha256, receipt["bytes"]):
        raise ValueError("Objeto original corrompido: tamanho/hash divergente")
    return raw, receipt


def detect_encoding(raw):
    decoder = codecs.getincrementaldecoder("utf-8-sig")("strict")
    try:
        with raw.open("rb") as stream:
            while chunk := stream.read(CHUNK):
                if b"\x00" in chunk:
                    raise ValueError("Original contem bytes nulos")
                decoder.decode(chunk)
        decoder.decode(b"", final=True)
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "cp1252"


def filter_stream(raw, month, output):
    encoding = detect_encoding(raw)
    all_rows = selected = 0
    with raw.open("r", encoding=encoding, errors="strict", newline="") as src, \
            output.open("w", encoding="utf-8", newline="") as dst:
        head = None
        for _ in range(20):
            line = src.readline()
            if not line:
                break
            if "\x00" in line:
                raise ValueError("Original contem bytes nulos")
            candidate = [c.strip().lstrip("\ufeff")
                         for c in next(csv.reader([line], delimiter=";", strict=True), [])]
            if len(candidate) == len(set(candidate)) and REQUIRED.issubset(candidate):
                head = candidate
                break
            if line.strip() and not line.strip().lstrip("\ufeff").lower().startswith("atualizado em:"):
                raise ValueError("Preambulo desconhecido; parser bloqueado")
        if head is None:
            raise ValueError("Cabecalho oficial ANAC nao encontrado")
        reader = csv.DictReader(src, fieldnames=head, delimiter=";", strict=True)
        writer = csv.DictWriter(dst, fieldnames=head, delimiter=";", lineterminator="\n",
                                extrasaction="raise")
        writer.writeheader()
        for row in reader:
            all_rows += 1
            if None in row or any(value is None or "\x00" in value for value in row.values()):
                raise ValueError(f"Linha {reader.line_num}: colunas/bytes invalidos")
            if row["NR_AEROPORTO_REFERENCIA"].strip().upper() != "SBKP":
                continue
            yyyy, mm = row["ANO"].strip(), row["MES"].strip()
            if (not yyyy.isdigit() or not mm.isdigit()
                    or f"{int(yyyy):04d}-{int(mm):02d}" != month):
                raise ValueError("Movimento SBKP com competencia divergente")
            if (row["NR_NATUREZA"].strip() not in ("D", "I")
                    or row["NR_MOVIMENTO_TIPO"].strip() not in ("P", "D")):
                raise ValueError("Codigo ANAC nao reconhecido em movimento SBKP")
            writer.writerow(row)
            selected += 1
    if not all_rows or not selected:
        raise ValueError("CSV nacional vazio ou sem movimentos SBKP; nao inferir zero")
    return {"codificacao_original": encoding, "linhas_origem": all_rows,
            "linhas_sbkp": selected, "colunas": head}


def _gzip_csv(csv_path, gz_path):
    with csv_path.open("rb") as original, gz_path.open("wb") as out:
        with gzip.GzipFile(fileobj=out, filename="", mode="wb", mtime=0) as compressed:
            while chunk := original.read(CHUNK):
                compressed.write(chunk)


def _inspect_existing(final, sha, month):
    info_path = final / "proveniencia.json"
    gzip_path = final / "sbkp.csv.gz"
    if not info_path.is_file() or not gzip_path.is_file():
        raise ValueError("Staging ja existe, mas esta incompleto; nao sobrescrever")
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if (info.get("sha256_original") != sha or info.get("competencia") != month
            or digest_file(gzip_path) != (info.get("sha256_gzip"), info.get("bytes_gzip"))):
        raise ValueError("Staging previamente existente diverge; nao sobrescrever")
    return info


def prepare(vault, month, sha256, out_dir):
    """Executa QA e publica apenas pacote local versionado, nunca dados de producao."""
    output = Path(out_dir).resolve()
    if (output == ROOT / "data" or output.is_relative_to(ROOT / "_site")
            or output.is_relative_to(ROOT / "data/anac/rima")):
        raise ValueError("Nao utilizar caminho publico ou acervo versionado como staging")
    raw, receipt = locate_original(vault, month, sha256)
    final = output / month / sha256
    if final.exists():
        info = _inspect_existing(final, sha256, month)
        return {"estado": "staging_reutilizado", "pasta": str(final), "resumo": info}
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sbkp-stage-", dir=output) as temp:
        work = Path(temp)
        csv_path = work / "sbkp.csv"
        details = filter_stream(raw, month, csv_path)
        content_hash, csv_bytes = digest_file(csv_path)
        if csv_bytes > MAX_CSV:
            raise ValueError("Recorte SBKP excedeu limite de 100 MB")
        summary = process_file(csv_path, month)
        if summary["provenance"]["linhas_sbkp"] != details["linhas_sbkp"]:
            raise ValueError("Soma de registros SBKP divergente entre leitores")
        if summary["provenance"]["sha256_original"] != content_hash:
            raise ValueError("Parser releu bytes diferentes do recorte")
        _gzip_csv(csv_path, work / "sbkp.csv.gz")
        gzip_hash, gzip_bytes = digest_file(work / "sbkp.csv.gz")
        if gzip_bytes > MAX_GZIP:
            raise ValueError("Gzip SBKP excedeu limite de auditoria")
        info = {
            "schema": "anac-rima-sbkp-offline-v1",
            "estado": "staging_validado_local_nao_publicado",
            "competencia": month,
            "url_original": receipt["url"],
            "sha256_original": sha256,
            "bytes_original": receipt["bytes"],
            "sha256_csv_sbkp": content_hash,
            "bytes_csv_sbkp": csv_bytes,
            "sha256_gzip": gzip_hash,
            "bytes_gzip": gzip_bytes,
            **details,
            "grupos": summary["rows"],
            "nota": "Reprocessamento local do bruto original; nao comprova comparabilidade com RMA"
        }
        (work / "proveniencia.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        csv_path.unlink()  # jamais publicar original nacional ou CSV temporario
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.exists():
            return {"estado": "staging_reutilizado", "pasta": str(final),
                    "resumo": _inspect_existing(final, sha256, month)}
        os.rename(work, final)
        return {"estado": "staging_validado_local", "pasta": str(final), "resumo": info}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acervo", type=Path, required=True, help="Cofre externo persistente")
    parser.add_argument("--competencia", required=True)
    parser.add_argument("--sha256", required=True, help="Versao explicita do original")
    parser.add_argument("--saida", type=Path, required=True, help="Staging isolado, nao dashboard")
    args = parser.parse_args()
    result = prepare(args.acervo, args.competencia, args.sha256, args.saida)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

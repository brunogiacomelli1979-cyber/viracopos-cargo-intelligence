"""Arquiva a parcela SBKP de arquivos oficiais ANAC/RIMA por competência.

Os CSVs nacionais são baixados apenas em memória, com HTTPS validado.
No Git são guardadas apenas linhas SBKP (campos originais preservados)
em CSV UTF-8 gzip e recibos com hash SHA-256 do arquivo fonte.
Não atualiza o dashboard.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import shutil
import tempfile
import ssl
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = (
    "https://sistemas.anac.gov.br/dadosabertos/"
    "Operador%20Aeroportu%C3%A1rio/"
    "Dados%20de%20Movimenta%C3%A7%C3%A3o%20Aeroportu%C3%A1rias/"
)
REQUIRED = {"ANO", "MES", "NR_AEROPORTO_REFERENCIA", "NR_MOVIMENTO_TIPO",
            "NR_NATUREZA", "QT_CARGA", "QT_CORREIO"}
MAX_SOURCE_BYTES = 250_000_000
FIRST_MONTH = "2020-01"  # Recorte histórico oficial do projeto; não altera arquivos antigos.
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/anac/rima"


def month_string(value):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise ValueError("Competência precisa ser AAAA-MM")
    return value


def month_sequence(start, end):
    start, end = month_string(start), month_string(end)
    if start < FIRST_MONTH:
        raise ValueError(f"Competência anterior ao recorte aprovado ({FIRST_MONTH}): {start}")
    if start > end:
        raise ValueError("Início após fim")
    year, month = map(int, start.split("-"))
    while f"{year:04d}-{month:02d}" <= end:
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month > 12:
            month = 1
            year += 1


def lagged_month(today, months=6):
    index = today.year * 12 + today.month - 1 - months
    return f"{(index // 12):04d}-{(index % 12) + 1:02d}"


def official_url(month):
    year, mm = month_string(month).split("-")
    return f"{BASE_URL}{year}/Movimentacoes_Aeroportuarias_{year}{mm}.csv"


def fetch_original(url, opener=urlopen, retry_delay=time.sleep):
    """HTTPS sem bypass TLS; rejeita HTML e leituras maiores que 250 MB."""
    request = Request(url, headers={
        "User-Agent": "VCP-Insights-ANAC-RIMA-archive/1.0",
        "Accept": "text/csv,text/plain,application/octet-stream",
    })
    last_error = None
    for attempt in range(2):
        try:
            response = opener(request, timeout=55, context=ssl.create_default_context())
            with response:
                final_url = response.geturl()
                if not final_url.startswith(BASE_URL):
                    raise ValueError(f"Redirecionamento inesperado: {final_url}")
                if response.status != 200:
                    # Arquivamento exige o CSV integral, nunca uma resposta parcial 206.
                    raise ValueError(f"HTTP {response.status}")
                raw = response.read(MAX_SOURCE_BYTES + 1)
                if not raw or len(raw) > MAX_SOURCE_BYTES:
                    raise ValueError("Arquivo vazio ou maior que limite")
                if b"<html" in raw[:4000].lower():
                    raise ValueError("Resposta HTML em vez de CSV")
                return raw, final_url
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            last_error = exc
            if attempt == 0:
                retry_delay(2)
    raise RuntimeError(f"Falha na origem: {last_error}") from last_error


def filter_sbkp(raw, month):
    """Recorte fiel das colunas originais; não soma nem interpreta QT_CARGA."""
    try:
        text = raw.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
        encoding = "cp1252"
    if "\x00" in text:
        raise ValueError("CSV contém bytes nulos")
    lines = text.splitlines(keepends=True)
    header_at = None
    for pos, line in enumerate(lines[:20]):
        candidate = next(csv.reader([line], delimiter=";", strict=True), [])
        candidate = [field.strip().lstrip("\ufeff") for field in candidate]
        if len(candidate) == len(set(candidate)) and REQUIRED.issubset(set(candidate)):
            header_at = pos
            break
    if header_at is None:
        preview = [line.strip()[:200] for line in lines[:8]]
        raise ValueError(f"Cabeçalho ANAC não localizado nas primeiras 20 linhas; prévia: {preview!r}")
    preamble = [line.strip().lstrip("\ufeff") for line in lines[:header_at] if line.strip()]
    if not all(line.lower().startswith("atualizado em:") for line in preamble):
        raise ValueError(f"Preâmbulo ANAC não reconhecido: {preamble[:5]!r}")
    reader = csv.DictReader(io.StringIO("".join(lines[header_at:]), newline=""),
                            delimiter=";", strict=True)
    headers = [x.strip().lstrip("\ufeff") for x in reader.fieldnames or []]
    if len(headers) != len(set(headers)) or not REQUIRED.issubset(set(headers)):
        raise ValueError(f"Cabeçalho ANAC inesperado: {headers[:30]}")
    reader.fieldnames = headers
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=";", lineterminator="\n")
    writer.writeheader()
    total, selected = 0, 0
    for row in reader:
        total += 1
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"Linha {reader.line_num}: colunas inconsistentes")
        if (row["NR_AEROPORTO_REFERENCIA"] or "").strip().upper() != "SBKP":
            continue
        year, mo = row["ANO"].strip(), row["MES"].strip()
        if not (year.isdigit() and mo.isdigit()
                and f"{int(year):04d}-{int(mo):02d}" == month):
            raise ValueError(f"Linha {reader.line_num}: competência divergente")
        if row["NR_MOVIMENTO_TIPO"].strip() not in ("P", "D"):
            raise ValueError(f"Linha {reader.line_num}: código de movimento ANAC desconhecido")
        if row["NR_NATUREZA"].strip() not in ("D", "I"):
            raise ValueError(f"Linha {reader.line_num}: código de natureza ANAC desconhecido")
        writer.writerow(row)
        selected += 1
    if total == 0 or selected == 0:
        raise ValueError("Arquivo vazio ou sem SBKP; não criar observação falsa")
    data = output.getvalue().encode("utf-8")
    compressed = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as gz:
        gz.write(data)
    return compressed.getvalue(), {
        "linhas_origem": total,
        "linhas_sbkp": selected,
        "colunas": headers,
        "codificacao_origem": encoding,
        "conteudo_sbkp_sha256": hashlib.sha256(data).hexdigest(),
    }


def load_manifest(root):
    file = root / "manifesto.json"
    if not file.exists():
        return {"schema": "anac_rima_sbkp_v1", "aeroporto": "SBKP", "competencias": {}}
    data = json.loads(file.read_text(encoding="utf-8"))
    if data.get("schema") != "anac_rima_sbkp_v1" or data.get("aeroporto") != "SBKP":
        raise ValueError("Manifesto existente usa contrato desconhecido")
    return data


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".partial")
    try:
        temp.write_bytes(content)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _verify_snapshot(root, entry):
    """Confere bytes antes de reutilizar arquivo atual ou histórico."""
    base = root.parent.parent.parent.resolve()
    path = (base / entry["caminho_sbkp"]).resolve()
    if not path.is_relative_to((base / "data/anac/rima").resolve()):
        raise ValueError("Caminho da versão fora do acervo RIMA")
    if not path.is_file():
        raise ValueError("Versão arquivada não existe")
    data = path.read_bytes()
    if (hashlib.sha256(data).hexdigest() != entry["sha256_sbkp_gzip"]
            or len(data) != entry["bytes_sbkp_gzip"]):
        raise ValueError("Versão arquivada não corresponde ao manifesto")
    return path


def store_month(root, manifest, month, raw, url, collected_utc):
    """Salva novo snapshot imutável; preserva o arquivo anterior e seu recibo."""
    month = month_string(month)
    if month < FIRST_MONTH:
        raise ValueError(f"Competência fora do recorte aprovado: {month}")
    archive, summary = filter_sbkp(raw, month)
    origin_hash = hashlib.sha256(raw).hexdigest()
    archive_hash = hashlib.sha256(archive).hexdigest()
    previous = manifest["competencias"].get(month)
    if previous:
        _verify_snapshot(root, previous)
        for prior in previous.get("revisoes", []):
            _verify_snapshot(root, prior)
        if previous["sha256_original"] == origin_hash:
            return "sem_mudanca"

    # Não reutilizar o caminho legado para versões novas.
    # Nome endereçado pelo conteúdo: snapshots antigos continuam íntegros.
    path = root / "sbkp" / month[:4] / "versoes" / month / f"{archive_hash}.csv.gz"
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != archive_hash:
            raise ValueError(f"{month}: colisão / versão existente modificada")
    else:
        atomic_write(path, archive)
    revisions = list(previous.get("revisoes", [])) if previous else []
    if previous:
        old = {key: value for key, value in previous.items() if key != "revisoes"}
        old["substituido_em_utc"] = collected_utc
        revisions.append(old)

    new_entry = {
        "url_original": url,
        "coletado_em_utc": collected_utc,
        "sha256_original": origin_hash,
        "bytes_original": len(raw),
        "caminho_sbkp": str(path.relative_to(root.parent.parent.parent)).replace("\\", "/"),
        "sha256_sbkp_gzip": archive_hash,
        "bytes_sbkp_gzip": len(archive),
        "revisoes": revisions,
        **summary,
    }
    # Publicar o recibo apenas após a verificação física do snapshot.
    _verify_snapshot(root, new_entry)
    manifest["competencias"][month] = new_entry
    manifest["atualizado_em_utc"] = collected_utc
    atomic_write(root / "manifesto.json",
                 (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return "revisado" if previous else "novo"


def _promote_complete_batch(source_root, staged_root, original_manifest_digest):
    """Publica lote inteiro somente após todas as coletas/validações aprovadas.

    Nunca sobrescreve um gzip antigo. A troca do manifesto ocorre por último.
    Arquivos ainda não referenciados podem ficar no disco após falha física,
    mas não são incorporados ao índice nem commitados se a execução falhar.
    """
    current_path = source_root / "manifesto.json"
    current_digest = (hashlib.sha256(current_path.read_bytes()).hexdigest()
                      if current_path.exists() else None)
    if current_digest != original_manifest_digest:
        raise RuntimeError("Manifesto mudou durante a execução; abortar por conflito")

    proposed = load_manifest(staged_root)
    for entry in proposed["competencias"].values():
        _verify_snapshot(staged_root, entry)
        for prior in entry.get("revisoes", []):
            _verify_snapshot(staged_root, prior)

    source_root.mkdir(parents=True, exist_ok=True)
    for staged_file in (staged_root / "sbkp").rglob("*.csv.gz"):
        relative = staged_file.relative_to(staged_root)
        destination = source_root / relative
        if destination.exists():
            if hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(staged_file.read_bytes()).digest():
                raise RuntimeError(f"Snapshot imutável diverge: {relative}")
            continue
        atomic_write(destination, staged_file.read_bytes())

    # A escrita é atômica e a única alteração de índice; falha antes disso
    # não expõe um lote parcialmente aceito.
    atomic_write(current_path, (staged_root / "manifesto.json").read_bytes())


def choose_months(manifest, mode, start, end, refresh, limit):
    months = list(month_sequence(start, end))
    if mode == "mensal":
        existing = set(manifest["competencias"])
        pending = [m for m in months if m not in existing]
        last = months[-refresh:] if refresh else []
        months = list(dict.fromkeys(pending + last))
    if limit:
        months = months[:limit]
    return months


def run(args, opener=urlopen, today=None):
    """Prepara lote em cópia temporária; falha não altera a base versionada."""
    cutoff = lagged_month(today or date.today())
    start = month_string(args.start)
    end = min(month_string(args.end or cutoff), cutoff)
    if start < FIRST_MONTH or start > end:
        raise ValueError(f"Intervalo fora do recorte aprovado/competências elegíveis: {start}..{end}")
    root = Path(args.out_dir).resolve()
    if root == ROOT / "data" or str(root).startswith(str(ROOT / "_site")):
        raise ValueError("Saída não pode ser data/ nem _site/")

    original_path = root / "manifesto.json"
    original_digest = (hashlib.sha256(original_path.read_bytes()).hexdigest()
                       if original_path.exists() else None)
    manifest = load_manifest(root)
    months = choose_months(manifest, args.mode, start, end, args.refresh, args.limit)
    result = {"planejados": len(months), "novos": 0, "revisados": 0,
              "sem_mudanca": 0, "falhas": [], "publicado": False}
    if not months:
        result["publicado"] = True
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    with tempfile.TemporaryDirectory(prefix="rima-batch-") as staging:
        staged_root = Path(staging) / "data/anac/rima"
        if root.exists():
            shutil.copytree(root, staged_root, dirs_exist_ok=True)
        staged_manifest = load_manifest(staged_root)
        for month in months:
            url = official_url(month)
            try:
                raw, final_url = fetch_original(url, opener=opener)
                changed = store_month(staged_root, staged_manifest, month, raw,
                                      final_url, datetime.now(timezone.utc).isoformat())
                if changed == "novo":
                    result["novos"] += 1
                elif changed == "revisado":
                    result["revisados"] += 1
                else:
                    result["sem_mudanca"] += 1
                print(f"{month}: {changed}", flush=True)
            except (OSError, ValueError, RuntimeError, csv.Error, UnicodeError) as exc:
                result["falhas"].append({"mes": month, "erro": str(exc)})
                print(f"{month}: ERRO: {exc}", file=sys.stderr, flush=True)
        if not result["falhas"]:
            # Validar semântica de quantidades/CSV e somas independentes
            # ANTES de promover snapshots e manifesto para a área de trabalho.
            # O GitHub Actions repetirá essas checagens após a promoção.
            try:
                from auditar_anac_rima import inspect
                from validar_agrupamento_rima import validate
                staged_repo = staged_root.parent.parent.parent
                audit = inspect(staged_repo)
                if audit["erros_criticos"]:
                    raise ValueError(f"Auditoria integral do lote reprovada: {audit['erros_criticos'][:3]}")
                crosscheck = validate(staged_repo)
                if crosscheck["resultado"] != "aprovado_tecnicamente" or crosscheck["erros"]:
                    raise ValueError(f"Agregação independente reprovada: {crosscheck['erros'][:3]}")
                _promote_complete_batch(root, staged_root, original_digest)
                result["publicado"] = True
            except (OSError, ValueError, RuntimeError, KeyError, csv.Error, UnicodeError) as exc:
                result["falhas"].append({"mes": "lote", "erro": str(exc)})
                print(f"Lote: ERRO: {exc}", file=sys.stderr, flush=True)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["falhas"] else 0


def main():
    parser = argparse.ArgumentParser(description="Download histórico e arquivamento ANAC/RIMA para SBKP")
    parser.add_argument("--mode", choices=["inicial", "mensal"], required=True)
    parser.add_argument("--start", default=FIRST_MONTH, help="A partir de 2020-01; períodos anteriores estão fora do escopo")
    parser.add_argument("--end", default=None)
    parser.add_argument("--refresh", type=int, default=12, help="Meses a reconsultar na rotina mensal")
    parser.add_argument("--limit", type=int, default=0, help="Limitar arquivos por execução; 0=todos")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    if args.refresh < 0 or args.limit < 0:
        parser.error("refresh/limit precisam ser não negativos")
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()

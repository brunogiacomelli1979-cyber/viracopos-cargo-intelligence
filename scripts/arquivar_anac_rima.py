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
REQUIRED = {"ANO", "MES", "NR_AEROPORTO", "NR_MOVIMENTO_TIPO",
            "NR_NATUREZA", "QT_CARGA", "QT_CORREIO"}
MAX_SOURCE_BYTES = 250_000_000
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/anac/rima"


def month_string(value):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise ValueError("Competência precisa ser AAAA-MM")
    return value


def month_sequence(start, end):
    start, end = month_string(start), month_string(end)
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
                if not (200 <= response.status < 300):
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
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=";", strict=True)
    headers = [x.strip().lstrip("\ufeff") for x in reader.fieldnames or []]
    if len(headers) != len(set(headers)) or not REQUIRED.issubset(set(headers)):
        raise ValueError(f"Cabeçalho inesperado: {headers[:30]}")
    reader.fieldnames = headers
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=";", lineterminator="\n")
    writer.writeheader()
    total, selected = 0, 0
    for row in reader:
        total += 1
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"Linha {reader.line_num}: colunas inconsistentes")
        if (row["NR_AEROPORTO"] or "").strip().upper() != "SBKP":
            continue
        year, mo = row["ANO"].strip(), row["MES"].strip()
        if not (year.isdigit() and mo.isdigit()
                and f"{int(year):04d}-{int(mo):02d}" == month):
            raise ValueError(f"Linha {reader.line_num}: competência divergente")
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


def store_month(root, manifest, month, raw, url, collected_utc):
    archive, summary = filter_sbkp(raw, month)
    path = root / "sbkp" / month[:4] / f"{month}.csv.gz"
    origin_hash = hashlib.sha256(raw).hexdigest()
    archive_hash = hashlib.sha256(archive).hexdigest()
    previous = manifest["competencias"].get(month)
    if previous and previous["sha256_original"] == origin_hash:
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != previous["sha256_sbkp_gzip"]:
            raise ValueError(f"{month}: cópia histórica diverge do manifesto")
        return "sem_mudanca"
    revisions = list(previous.get("revisoes", [])) if previous else []
    if previous:
        revisions.append({
            "sha256_original_anterior": previous["sha256_original"],
            "sha256_sbkp_anterior": previous["sha256_sbkp_gzip"],
            "substituido_em_utc": collected_utc,
        })
    atomic_write(path, archive)
    manifest["competencias"][month] = {
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
    manifest["atualizado_em_utc"] = collected_utc
    atomic_write(root / "manifesto.json", (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return "revisado" if previous else "novo"


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


def run(args, opener=urlopen):
    cutoff = lagged_month(date.today())
    start = month_string(args.start)
    end = min(month_string(args.end or cutoff), cutoff)
    if start > end:
        raise ValueError(f"Nenhum mês elegível (limite indicativo: {cutoff})")
    root = Path(args.out_dir).resolve()
    # Sem edição de séries atuais ou pasta de publicação.
    if root == ROOT / "data" or str(root).startswith(str(ROOT / "_site")):
        raise ValueError("Saída não pode ser data/ nem _site/")
    manifest = load_manifest(root)
    months = choose_months(manifest, args.mode, start, end, args.refresh, args.limit)
    result = {"planejados": len(months), "novos": 0, "revisados": 0, "sem_mudanca": 0, "falhas": []}
    for month in months:
        url = official_url(month)
        try:
            raw, final_url = fetch_original(url, opener=opener)
            changed = store_month(root, manifest, month, raw, final_url, datetime.now(timezone.utc).isoformat())
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
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["falhas"] else 0


def main():
    parser = argparse.ArgumentParser(description="Download histórico e arquivamento ANAC/RIMA para SBKP")
    parser.add_argument("--mode", choices=["inicial", "mensal"], required=True)
    parser.add_argument("--start", default="2019-01")
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

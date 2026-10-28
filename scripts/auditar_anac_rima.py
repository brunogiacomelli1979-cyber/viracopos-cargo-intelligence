"""Audita arquivos ANAC/RIMA SBKP sem publicar agregados no dashboard."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"ANO", "MES", "NR_AEROPORTO_REFERENCIA", "NR_MOVIMENTO_TIPO",
            "NR_NATUREZA", "QT_CARGA", "QT_CORREIO"}
DECIMAL = re.compile(r"^\d+(?:[.,]\d+)?$")


def inspect(root=ROOT):
    manifest_path = root / "data/anac/rima/manifesto.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "anac_rima_sbkp_v1" or manifest.get("aeroporto") != "SBKP":
        raise ValueError("Manifesto ANAC incompatível")
    months = manifest.get("competencias", {})
    if not months:
        raise ValueError("Acervo ANAC sem nenhuma competência")
    summary = {"competencias": {}, "total_registros": 0,
               "erros_criticos": [], "alertas": [], "limites": {
                   "duplicata_exata": "indicador de investigação, não exclusão automática",
                   "peso_nulo": "ausência não equivale a zero",
                   "rima_rma": "não diretamente comparáveis"}}
    for month, entry in sorted(months.items()):
        errors = []
        # Revisões devem continuar fisicamente recuperáveis, não apenas com hashes no JSON.
        for version in entry.get("revisoes", []):
            try:
                old_path = (root / version["caminho_sbkp"]).resolve()
                if not old_path.is_relative_to((root / "data/anac/rima").resolve()):
                    raise ValueError("caminho histórico fora do acervo")
                if not old_path.is_file():
                    raise ValueError("arquivo histórico ausente")
                old_bytes = old_path.read_bytes()
                if (len(old_bytes) != version["bytes_sbkp_gzip"]
                        or hashlib.sha256(old_bytes).hexdigest() != version["sha256_sbkp_gzip"]):
                    raise ValueError("tamanho/hash da versão histórica divergente")
                if len(old_bytes) > 10_000_000:
                    raise ValueError("versão histórica excede limite")
                with gzip.open(old_path, "rb") as old_stream:
                    raw_old = old_stream.read(100_000_001)
                if (len(raw_old) > 100_000_000
                        or hashlib.sha256(raw_old).hexdigest() != version["conteudo_sbkp_sha256"]):
                    raise ValueError("hash de conteúdo histórico divergente")
            except (OSError, ValueError, KeyError, EOFError) as exc:
                errors.append(f"revisão histórica indisponível: {exc}")
        path = root / entry["caminho_sbkp"]
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            errors.append("competência inválida")
            summary["erros_criticos"].append({month: errors})
            continue
        if not path.is_file():
            summary["erros_criticos"].append({month: ["arquivo ausente"]})
            continue
        encoded = path.read_bytes()
        if (hashlib.sha256(encoded).hexdigest() != entry["sha256_sbkp_gzip"]
                or len(encoded) != entry["bytes_sbkp_gzip"]):
            errors.append("gzip difere do manifesto em tamanho/hash")
        if len(encoded) > 10_000_000:
            errors.append("gzip excede limite de segurança")
            summary["erros_criticos"].append({month: errors})
            continue
        try:
            # Evita uso de gzip com leitura ilimitada.
            with gzip.open(path, "rb") as gz:
                data = gz.read(100_000_001)
            if len(data) > 100_000_000:
                raise ValueError("conteúdo descompactado maior que 100 MB")
            if hashlib.sha256(data).hexdigest() != entry["conteudo_sbkp_sha256"]:
                errors.append("CSV descompactado difere do hash")
            reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""),
                                    delimiter=";", strict=True)
            header = reader.fieldnames or []
            if (len(header) != len(set(header))
                    or not REQUIRED.issubset(header)
                    or header != entry["colunas"]):
                errors.append("esquema incompatível com manifesto")
                summary["erros_criticos"].append({month: errors})
                continue
            counts = Counter()
            empty = Counter()
            zero = Counter()
            invalid = Counter()
            seen = set()
            duplicates = 0
            total = 0
            for row in reader:
                total += 1
                if None in row or any(v is None for v in row.values()):
                    errors.append(f"linha {reader.line_num}: número de colunas inválido")
                    break
                if (row["NR_AEROPORTO_REFERENCIA"] != "SBKP"
                        or not row["ANO"].strip().isdigit()
                        or not row["MES"].strip().isdigit()
                        or f"{int(row['ANO']):04d}-{int(row['MES']):02d}" != month):
                    errors.append(f"linha {reader.line_num}: aeroporto/competência incorreto")
                    break
                mv = row["NR_MOVIMENTO_TIPO"].strip()
                nv = row["NR_NATUREZA"].strip()
                if mv not in ("P", "D") or nv not in ("D", "I"):
                    errors.append(f"linha {reader.line_num}: código de movimento/natureza inválido")
                    break
                counts[mv + "/" + nv] += 1
                # Duplicidade exata de registros: alerta, pode refletir ausência de ID único.
                row_hash = hashlib.sha256("\x1f".join(row[h] for h in header).encode()).digest()
                if row_hash in seen:
                    duplicates += 1
                else:
                    seen.add(row_hash)
                for field in ("QT_CARGA", "QT_CORREIO"):
                    value = row[field].strip()
                    if not value:
                        empty[field] += 1
                    elif not DECIMAL.fullmatch(value):
                        invalid[field] += 1
                    else:
                        try:
                            v = Decimal(value.replace(",", "."))
                            if not v.is_finite() or v < 0:
                                invalid[field] += 1
                            elif v == 0:
                                zero[field] += 1
                        except InvalidOperation:
                            invalid[field] += 1
            if total != entry["linhas_sbkp"]:
                errors.append(f"registros divergentes: manifesto={entry['linhas_sbkp']}, observado={total}")
            if any(invalid.values()):
                errors.append(f"peso inválido sem política definida: {dict(invalid)}")
            if not counts:
                errors.append("nenhum movimento aceito")
            summary["competencias"][month] = {
                "registros": total, "movimentos_por_natureza": dict(sorted(counts.items())),
                "pesos_nulos": dict(empty), "pesos_zero": dict(zero),
                "pesos_invalidos": dict(invalid),
                "duplicatas_linha_inteira": duplicates,
                "sha256_gzip": hashlib.sha256(encoded).hexdigest(),
                "versoes_anteriores": len(entry.get("revisoes", []))
            }
            summary["total_registros"] += total
            if duplicates:
                summary["alertas"].append({month: f"{duplicates} linhas completamente idênticas: investigar granularidade antes de qualquer deduplicação"})
        except (OSError, UnicodeError, ValueError, csv.Error) as exc:
            errors.append(f"falha de leitura CSV/gzip: {exc}")
        if errors:
            summary["erros_criticos"].append({month: errors})
    summary["integridade_arquivos"] = "aprovada" if not summary["erros_criticos"] else "reprovada"
    summary["serie_apta_modelagem"] = False  # dependências metodológicas e temporais ainda não resolvidas
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    result = inspect(args.root)
    txt = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(txt, encoding="utf-8")
    print(txt)
    raise SystemExit(1 if result["erros_criticos"] else 0)


if __name__ == "__main__":
    main()

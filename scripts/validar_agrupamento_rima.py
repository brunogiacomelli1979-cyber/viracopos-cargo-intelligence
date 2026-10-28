"""Validação cruzada do agregador ANAC/RIMA usando meses SBKP arquivados.

Roda offline, não coleta dados, não altera o dashboard e não publica tonelagem.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import tempfile
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from processar_anac_rima import process_file

ROOT = Path(__file__).resolve().parents[1]
CODES = {("D", "P"): ("domestica", "pouso"),
         ("D", "D"): ("domestica", "decolagem"),
         ("I", "P"): ("internacional", "pouso"),
         ("I", "D"): ("internacional", "decolagem")}
MAX_GZIP_BYTES = 10_000_000
MAX_CSV_BYTES = 100_000_000


def independent_totals(data, month):
    """Segundo cálculo, independente das regras de somatória do processador."""
    reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""), delimiter=";", strict=True)
    if not reader.fieldnames:
        raise ValueError("CSV sem cabeçalho")
    aggregates = defaultdict(lambda: {"registros": 0, "carga_kg": Decimal(0),
                                       "correio_kg": Decimal(0), "carga_ausente": 0,
                                       "correio_ausente": 0})
    n = 0
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("CSV com colunas inválidas")
        if row["NR_AEROPORTO_REFERENCIA"].strip() != "SBKP":
            raise ValueError("Acervo contém aeroportos diferentes de SBKP")
        if f"{int(row['ANO']):04d}-{int(row['MES']):02d}" != month:
            raise ValueError("Competência do arquivo incorreta")
        key = CODES.get((row["NR_NATUREZA"].strip(), row["NR_MOVIMENTO_TIPO"].strip()))
        if key is None:
            raise ValueError("Categoria RIMA não reconhecida")
        group = aggregates[key]
        group["registros"] += 1
        n += 1
        for col, name in (("QT_CARGA", "carga_kg"), ("QT_CORREIO", "correio_kg")):
            value = row[col].strip()
            if not value:
                group["carga_ausente" if col == "QT_CARGA" else "correio_ausente"] += 1
                continue
            try:
                amount = Decimal(value.replace(",", "."))
            except InvalidOperation as exc:
                raise ValueError(f"{col}: valor não numérico") from exc
            if not amount.is_finite() or amount < 0:
                raise ValueError(f"{col}: valor negativo/não finito")
            group[name] += amount
    return aggregates, n


def validate(root=ROOT):
    manifest_path = root / "data/anac/rima/manifesto.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "anac_rima_sbkp_v1" or manifest.get("aeroporto") != "SBKP":
        raise ValueError("Manifesto RIMA incompatível")
    months = manifest.get("competencias", {})
    if not months:
        raise ValueError("Sem meses arquivados")
    report = {"comparacoes": {}, "meses_validados": 0, "total_registros": 0,
              "apto_publicacao": False, "erros": [],
              "restricao": "Validação técnica de agregações; pendências RIMA/RMA e de série contínua permanecem"}
    for month, entry in sorted(months.items()):
        try:
            if month < "2020-01":
                raise ValueError("Mês anterior ao início aprovado 2020-01")
            path = root / entry["caminho_sbkp"]
            if not path.is_file() or not path.resolve().is_relative_to((root / "data/anac/rima").resolve()):
                raise ValueError("Arquivo arquivado fora do diretório autorizado")
            raw_gzip = path.read_bytes()
            if len(raw_gzip) > MAX_GZIP_BYTES or hashlib.sha256(raw_gzip).hexdigest() != entry["sha256_sbkp_gzip"]:
                raise ValueError("Gzip excedeu limite ou não corresponde ao SHA-256")
            with gzip.open(path, "rb") as stream:
                csv_bytes = stream.read(MAX_CSV_BYTES + 1)
            if len(csv_bytes) > MAX_CSV_BYTES:
                raise ValueError("CSV excedeu limite")
            if hashlib.sha256(csv_bytes).hexdigest() != entry["conteudo_sbkp_sha256"]:
                raise ValueError("CSV difere do hash de proveniência")
            with tempfile.TemporaryDirectory() as tmp:
                csv_path = Path(tmp) / f"sbkp_{month}.csv"
                csv_path.write_bytes(csv_bytes)
                parsed = process_file(csv_path, month)
            independent, count = independent_totals(csv_bytes, month)
            if parsed["provenance"]["linhas_sbkp"] != count or count != entry["linhas_sbkp"]:
                raise ValueError("Divergência no total de registros")
            verified_groups = {}
            for group in parsed["rows"]:
                key = (group["natureza"], group["movimento"])
                src = independent[key]
                if group["registros"] != src["registros"]:
                    raise ValueError(f"Divergência de contagem: {key}")
                if group["carga_ausente"] != src["carga_ausente"] or group["correio_ausente"] != src["correio_ausente"]:
                    raise ValueError(f"Divergência de quantidades ausentes: {key}")
                for col in ("carga_kg", "correio_kg"):
                    expected = "" if src["registros"] == 0 or src["carga_ausente" if col == "carga_kg" else "correio_ausente"] else src[col]
                    if expected == "":
                        if group[col] != "":
                            raise ValueError(f"Valor inventado para grupo incompleto: {key}/{col}")
                    elif not group[col] or Decimal(group[col]) != expected:
                        raise ValueError(f"Soma não confere: {key}/{col}")
                expected_status = ("sem_movimentos" if src["registros"] == 0
                                   else "incompleto" if src["carga_ausente"] or src["correio_ausente"]
                                   else "completo")
                if group["status"] != expected_status:
                    raise ValueError(f"Status inesperado: {key}")
                verified_groups["/".join(key)] = {
                    "registros": src["registros"],
                    "carga_kg": str(src["carga_kg"]) if not src["carga_ausente"] and src["registros"] else None,
                    "correio_kg": str(src["correio_kg"]) if not src["correio_ausente"] and src["registros"] else None,
                    "status": expected_status,
                }
            report["comparacoes"][month] = {"registros": count, "grupos": verified_groups,
                                            "resultado": "agregacao_confere"}
            report["meses_validados"] += 1
            report["total_registros"] += count
        except (OSError, ValueError, KeyError, csv.Error, UnicodeError, InvalidOperation) as exc:
            report["erros"].append({"mes": month, "motivo": str(exc)})
    report["resultado"] = "aprovado_tecnicamente" if not report["erros"] else "reprovado"
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    report = validate(args.root)
    result = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print(result)
    raise SystemExit(1 if report["erros"] else 0)


if __name__ == "__main__":
    main()

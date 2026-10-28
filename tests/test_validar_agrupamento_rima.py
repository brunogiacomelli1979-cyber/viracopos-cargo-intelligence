"""Teste de agregação cruzada sem acessar ANAC e sem dados operacionais reais."""
import csv
import gzip
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validar_agrupamento_rima import validate

HEADER = "ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n"

def fixture(root, rows):
    root = Path(root)
    directory = root / "data/anac/rima"
    path = directory / "sbkp/2020/2020-01.csv.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (HEADER+rows).encode("utf-8")
    with gzip.open(path, "wb") as out:
        out.write(data)
    manifest={"schema":"anac_rima_sbkp_v1","aeroporto":"SBKP",
              "competencias":{"2020-01":{
               "caminho_sbkp":"data/anac/rima/sbkp/2020/2020-01.csv.gz",
               "sha256_sbkp_gzip":hashlib.sha256(path.read_bytes()).hexdigest(),
               "conteudo_sbkp_sha256":hashlib.sha256(data).hexdigest(),
               "linhas_sbkp":len(rows.strip().splitlines())}}}
    (directory/"manifesto.json").write_text(json.dumps(manifest), encoding="utf-8")
    return path

class CrossValidationTests(unittest.TestCase):
    def test_sums_and_counts_match(self):
        with tempfile.TemporaryDirectory() as t:
            fixture(t, "2020;01;SBKP;P;I;15,5;2\n2020;01;SBKP;P;I;5;0\n"
                       "2020;01;SBKP;D;D;1;3\n")
            data=validate(Path(t))
            self.assertEqual(data["resultado"],"aprovado_tecnicamente")
            self.assertEqual(data["total_registros"],3)
            self.assertEqual(data["comparacoes"]["2020-01"]["grupos"]["internacional/pouso"]["carga_kg"],"20.5")
            self.assertFalse(data["apto_publicacao"])

    def test_no_imputation_when_missing(self):
        with tempfile.TemporaryDirectory() as t:
            fixture(t, "2020;01;SBKP;P;I;10;1\n2020;01;SBKP;P;I;;2\n")
            data=validate(Path(t))
            self.assertEqual(data["resultado"],"aprovado_tecnicamente")
            self.assertEqual(data["comparacoes"]["2020-01"]["grupos"]["internacional/pouso"]["carga_kg"],None)

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as t:
            path=fixture(t,"2020;01;SBKP;P;I;5;2\n")
            path.write_bytes(b"tampered")
            self.assertEqual(validate(Path(t))["resultado"],"reprovado")

if __name__=="__main__":
    unittest.main()

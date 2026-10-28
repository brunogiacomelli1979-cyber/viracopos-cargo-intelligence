import csv, gzip, hashlib, io, json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from auditar_anac_rima import inspect

class AuditTests(unittest.TestCase):
    def setup_month(self, root, original="2020;01;SBKP;P;I;0;"):
        store=root/"data/anac/rima"
        file=store/"sbkp/2020/2020-01.csv.gz"
        file.parent.mkdir(parents=True,exist_ok=True)
        plain=("ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n"+
               original+"\n").encode()
        # Use deterministic gzip only to simplify test hashes.
        with gzip.open(file,"wb") as g:g.write(plain)
        binary=file.read_bytes()
        manifest={"schema":"anac_rima_sbkp_v1","aeroporto":"SBKP",
                  "competencias":{"2020-01":{
                  "caminho_sbkp":"data/anac/rima/sbkp/2020/2020-01.csv.gz",
                  "sha256_sbkp_gzip":hashlib.sha256(binary).hexdigest(),
                  "bytes_sbkp_gzip":len(binary),
                  "conteudo_sbkp_sha256":hashlib.sha256(plain).hexdigest(),
                  "linhas_sbkp":1,"colunas":list(csv.DictReader(io.StringIO(plain.decode()),delimiter=";").fieldnames)}}}
        (store/"manifesto.json").write_text(json.dumps(manifest))
        return file

    def test_integrity_and_missing_not_zero(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            self.setup_month(root)
            r=inspect(root)
            self.assertEqual(r["integridade_arquivos"],"aprovada")
            self.assertEqual(r["competencias"]["2020-01"]["pesos_nulos"]["QT_CORREIO"],1)
            self.assertEqual(r["competencias"]["2020-01"]["pesos_zero"]["QT_CARGA"],1)
            self.assertFalse(r["serie_apta_modelagem"])

    def test_corruption_is_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            file=self.setup_month(root)
            file.write_bytes(b"not gzip")
            self.assertEqual(inspect(root)["integridade_arquivos"],"reprovada")

    def test_invalid_weight_blocks(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            self.setup_month(root,"2020;01;SBKP;P;I;-5;0")
            r=inspect(root)
            self.assertEqual(r["integridade_arquivos"],"reprovada")
            self.assertEqual(r["competencias"]["2020-01"]["pesos_invalidos"]["QT_CARGA"],1)

if __name__=="__main__":
    unittest.main()

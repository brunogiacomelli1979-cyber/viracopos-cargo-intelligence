"""Testes sintéticos da coleta ANAC; não representam dados reais do aeroporto."""
import io
import sys
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from coletar_anac_sbkp import aggregate_csv, collect_month, url_for, months_between

HEADER = "nr_ano_referencia;nr_mes_referencia;sg_icao_origem;sg_icao_destino;ds_natureza_etapa;kg_carga_paga;kg_carga_gratis;kg_correio\n"
def sample():
    return (HEADER+
       "2024;1;SBKP;SBGR;DOMESTICA;1000;500;20\n"+
       "2024;1;KMIA;SBKP;INTERNACIONAL;2100;400;30\n"+
       "2024;1;SBGR;SBRJ;DOMESTICA;9999;999;99\n").encode("latin-1")
class AnacTest(unittest.TestCase):
    def test_url_and_calendar(self):
        self.assertTrue(url_for("2024-01").endswith("/2024/basica2024-01.zip"))
        self.assertEqual(months_between("2023-12","2024-02"),["2023-12","2024-01","2024-02"])
    def test_direction_scope_units_and_mail(self):
        rows, quality = aggregate_csv(sample(), "2024-01")
        self.assertEqual(quality["etapas_sbkp"],2)
        by_dir={r["sentido"]:r for r in rows}
        self.assertAlmostEqual(by_dir["embarque"]["carga_sem_correio_t"],1.5)
        self.assertAlmostEqual(by_dir["desembarque"]["carga_sem_correio_t"],2.5)
        self.assertAlmostEqual(by_dir["embarque"]["correio_t"],0.02)
        self.assertAlmostEqual(by_dir["desembarque"]["correio_t"],0.03)
    def test_missing_cargo_is_not_zero(self):
        raw=(HEADER+"2024;1;SBKP;SBGR;DOMESTICA;;100;0\n").encode()
        with self.assertRaisesRegex(ValueError,"não informados"):
            aggregate_csv(raw,"2024-01")
    def test_wrong_period_rejected(self):
        with self.assertRaisesRegex(ValueError,"competência"):
            aggregate_csv(sample(),"2023-12")
    def test_missing_column_rejected(self):
        with self.assertRaisesRegex(ValueError,"Esquema ANAC"):
            aggregate_csv(b"sg_icao_origem;sg_icao_destino\nSBKP;SBGR\n","2024-01")
    def test_zip_and_source_hashes(self):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,"w") as archive:
            archive.writestr("basica2024-01.csv",sample())
        data, receipt=collect_month("2024-01",fetcher=lambda url, timeout: buffer.getvalue())
        self.assertEqual(receipt["competencia"],"2024-01")
        self.assertEqual(len(data),2)
        self.assertEqual(len(receipt["sha256"]),64)
if __name__=="__main__":unittest.main()

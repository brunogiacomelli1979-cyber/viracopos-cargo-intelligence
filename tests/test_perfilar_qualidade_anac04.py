import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from perfilar_qualidade_anac04 import profile_archive, profile_csv

HEADER = ("ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;"
          "QT_CARGA;QT_CORREIO;NR_SERVICE_TYPE;NR_AERONAVE_MARCAS;"
          "DT_CALCO;HH_CALCO;DT_TOQUE;HH_TOQUE\n")
ROW1 = "2020;04;SBKP;P;I;100;0;F;PTABC;2020-04-10;12:00;2020-04-10;11:55\n"
ROW2 = "2020;04;SBKP;P;I;0;;F;PTABC;2020-04-10;12:00;2020-04-10;11:55\n"
ROW3 = "2020;04;SBKP;D;D;;5;J;PTXYZ;2020-05-01;00:02;2020-04-30;23:58\n"


class DataQualityProfileTests(unittest.TestCase):
    def test_semantics_null_zero_positive_and_movement(self):
        item = profile_csv((HEADER + ROW1 + ROW2 + ROW3).encode(), "2020-04")
        self.assertEqual(item["registros_movimentacao"], 3)
        self.assertEqual(item["carga"]["movimentos_com_carga_positiva"], 1)
        self.assertEqual(item["carga"]["movimentos_com_carga_zero"], 1)
        self.assertEqual(item["carga"]["movimentos_com_carga_ausente"], 1)
        self.assertEqual(item["correio"], {"positivo": 1, "zero": 1, "ausente": 1})
        self.assertEqual(item["movimentos_por_natureza"], {"D/D": 1, "P/I": 2})
        self.assertFalse(item["apto_publicacao"])

    def test_candidate_key_collisions_are_not_deduplicated(self):
        item = profile_csv((HEADER + ROW1 + ROW2).encode(), "2020-04")
        self.assertEqual(item["duplicatas_exatas_adicionais"], 0)
        self.assertEqual(item["chaves_operacionais_candidatas"]["calco"]["colisoes_adicionais"], 1)
        self.assertEqual(item["chaves_operacionais_candidatas"]["toque"]["colisoes_adicionais"], 1)
        self.assertEqual(item["registros_movimentacao"], 2)

    def test_full_duplicate_only_alerts_and_preserves_counts(self):
        item = profile_csv((HEADER + ROW1 + ROW1).encode(), "2020-04")
        self.assertEqual(item["duplicatas_exatas_adicionais"], 1)
        self.assertEqual(item["registros_movimentacao"], 2)
        self.assertIn("linhas_idênticas_exigem_analise_de_granularidade",
                      item["alertas_investigacao"])

    def test_out_of_month_date_is_flagged_not_deleted(self):
        item = profile_csv((HEADER + ROW1 + ROW3).encode(), "2020-04")
        self.assertEqual(item["datas_operacionais"]["DT_CALCO"]["fora_da_competencia"], 1)
        self.assertEqual(item["registros_movimentacao"], 2)
        self.assertIn("datas_operacionais_foras_da_competencia_ou_nao_reconhecidas",
                      item["alertas_investigacao"])

    def test_missing_optional_candidate_key_does_not_fake_uniqueness(self):
        h = ("ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;"
             "NR_NATUREZA;QT_CARGA;QT_CORREIO\n")
        r = profile_csv((h + "2020;04;SBKP;P;I;0;\n").encode(), "2020-04")
        self.assertFalse(r["chaves_operacionais_candidatas"])
        self.assertEqual(r["service_type"], {"(nao_informado)": 1})

    def test_invalid_number_or_wrong_airport_rejected(self):
        with self.assertRaisesRegex(ValueError, "numero invalido"):
            profile_csv((HEADER + ROW1.replace(";100;0;", ";-5;0;")).encode(), "2020-04")
        with self.assertRaisesRegex(ValueError, "aeroporto"):
            profile_csv((HEADER + ROW1.replace("SBKP", "SBGR")).encode(), "2020-04")

    def test_empty_and_pre2020_rejected(self):
        with self.assertRaisesRegex(ValueError, "sem movimentos"):
            profile_csv(HEADER.encode(), "2020-04")
        with self.assertRaisesRegex(ValueError, "recorte"):
            profile_csv((HEADER + ROW1).encode(), "2019-12")

    def test_real_archived_months_remain_unpublished(self):
        result = profile_archive(ROOT)
        self.assertEqual(result["competencias_analisadas"],
                         ["2020-01", "2020-02", "2020-03", "2024-01"])
        self.assertEqual(result["total_movimentacoes"], 34968)
        self.assertFalse(result["liberado_dashboard"])
        self.assertFalse(result["liberado_nova_coleta"])
        self.assertEqual(result["quantidade_competencias"], 4)
        # Evidência operacional compacta no log; não publica dados no dashboard.
        print("ANAC04_RESUMO_REAL=" + json.dumps({
            "meses": result["competencias_analisadas"],
            "total": result["total_movimentacoes"],
            "meses_perfil": {
                month: {
                    "registros": item["registros_movimentacao"],
                    "movimentos_carga_positiva": item["carga"]["movimentos_com_carga_positiva"],
                    "zero": item["carga"]["movimentos_com_carga_zero"],
                    "ausente": item["carga"]["movimentos_com_carga_ausente"],
                    "colisoes_calco": item["chaves_operacionais_candidatas"].get("calco", {}).get("colisoes_adicionais"),
                    "colisoes_toque": item["chaves_operacionais_candidatas"].get("toque", {}).get("colisoes_adicionais"),
                    "datas_calco_fora": item["datas_operacionais"].get("DT_CALCO", {}).get("fora_da_competencia", 0),
                } for month, item in result["perfis"].items()
            }
        }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    unittest.main()

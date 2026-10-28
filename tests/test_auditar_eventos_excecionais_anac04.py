import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from auditar_eventos_excecionais_anac04 import (
    SERVICE_GROUPS, _delta, inspect_csv, inspect_archive, parse_date,
)

HEADER = ("ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;"
          "NR_NATUREZA;QT_CARGA;QT_CORREIO;NR_SERVICE_TYPE;"
          "NR_AERONAVE_MARCAS;NR_AERONAVE_TIPO;NR_AERONAVE_OPERADOR;"
          "NR_VOO_NUMERO;NR_VOO_OUTRO_AEROPORTO;"
          "DT_CALCO;HH_CALCO;DT_TOQUE;HH_TOQUE\n")

def row(move="P", nature="I", cargo="100", service="J",
        calco="2020-04-01", hcalco="00:15", toque="2020-03-31",
        htoque="23:59", flight="123"):
    return (f"2020;04;SBKP;{move};{nature};{cargo};0;{service};"
            f"PTABC;B738;AAB;{flight};SBGR;"
            f"{calco};{hcalco};{toque};{htoque}\n")


class AnacNormaTests(unittest.TestCase):
    def test_competencia_de_calco_permite_toque_no_mes_anterior(self):
        result = inspect_csv((HEADER + row()).encode(), "2020-04")
        self.assertEqual(result["calco_norma"], {"na_competencia": 1})
        self.assertEqual(result["toque_status"], {"fora_da_competencia": 1})
        self.assertEqual(result["toque_fora_mes_duracao_operacional"], {"diferenca_ate_120_minutos": 1})
        self.assertTrue(result["norma_competencia_calco_respeitada"])

    def test_decolagem_descalco_no_mes_e_toque_no_proximo(self):
        r = row(move="D", calco="2020-04-30", hcalco="23:57",
                toque="2020-05-01", htoque="00:03", service="F")
        result = inspect_csv((HEADER + r).encode(), "2020-04")
        self.assertEqual(result["toque_fora_mes_por_tipo_movimento"], {"D":1})
        self.assertEqual(result["toque_fora_mes_duracao_operacional"], {"diferenca_ate_120_minutos":1})
        self.assertTrue(result["norma_competencia_calco_respeitada"])

    def test_calco_outside_is_different_error(self):
        r = row(calco="2020-05-01", toque="2020-04-30")
        result = inspect_csv((HEADER + r).encode(), "2020-04")
        self.assertFalse(result["norma_competencia_calco_respeitada"])
        self.assertEqual(result["calco_norma"], {"fora_da_competencia": 1})

    def test_known_service_type_Y_and_Z_from_portaria(self):
        self.assertEqual(SERVICE_GROUPS["Y"], "voo_alternado_portaria")
        self.assertEqual(SERVICE_GROUPS["Z"], "voo_retorno_portaria")
        result = inspect_csv((HEADER + row(service="Y") +
                              row(service="Z",flight="124")).encode(), "2020-04")
        self.assertEqual(result["service_type_nao_mapeados"], {})
        self.assertEqual(result["service_type_grupos_descritivos"]["voo_alternado_portaria"],1)
        self.assertEqual(result["service_type_grupos_descritivos"]["voo_retorno_portaria"],1)

    def test_null_text_treated_as_uninformed_and_not_collision(self):
        a = row(toque="null", htoque="null")
        b = row(toque="null", htoque="null", cargo="200", flight="321")
        result = inspect_csv((HEADER + a + b).encode(), "2020-04")
        self.assertEqual(result["toque_status"]["nao_informado"], 2)
        self.assertEqual(result["colisoes_toque_com_data_reconhecida"], 0)

    def test_colliding_key_with_real_date_does_not_publish_identity(self):
        a = row(toque="2020-04-01", htoque="00:01", hcalco="00:04")
        b = row(toque="2020-04-01", htoque="00:01", hcalco="00:10",
                cargo="400", flight="451")
        result = inspect_csv((HEADER+a+b).encode(), "2020-04")
        self.assertEqual(result["colisoes_toque_com_data_reconhecida"],1)
        one = result["colisoes_perfil_anonimizado"][0]
        self.assertTrue(one["calco_difere"])
        self.assertTrue(one["valores_de_carga_diferem"])
        blob = json.dumps(result)
        self.assertNotIn("PTABC", blob)
        self.assertNotIn("451", blob)
        self.assertNotIn("2020-04-01", blob)
        self.assertTrue(result["nenhum_registro_excluido"])

    def test_invalid_date_is_not_silently_parsed(self):
        with self.assertRaisesRegex(ValueError, "nao reconhecida"):
            parse_date("SEM_DATA")
        with self.assertRaises(ValueError):
            inspect_csv((HEADER + row(toque="XX")).encode(), "2020-04")

    def test_bad_airport_rejected(self):
        bad = row().replace(";SBKP;", ";SBGR;")
        with self.assertRaises(ValueError):
            inspect_csv((HEADER + bad).encode(), "2020-04")

    def test_real_archived_anomalies_and_normative_date(self):
        r = inspect_archive(ROOT)
        self.assertEqual(r["total_registros"],34968)
        self.assertEqual(r["total_toque_fora_mes"],15)
        self.assertEqual(r["total_toque_nao_informado"],264)
        self.assertEqual(r["total_colisoes_toque_data_reconhecida"],1)
        self.assertEqual(r["total_calco_fora_mes"],0)
        self.assertTrue(r["todos_calcos_no_mes"])
        self.assertTrue(r["nao_liberado_para_publicacao"])
        self.assertTrue(r["nao_liberado_para_nova_coleta"])
        print("ANAC04_EXCECOES_AGREGADAS="+json.dumps({
            "total_toque_fora_mes":r["total_toque_fora_mes"],
            "total_toque_nao_informado":r["total_toque_nao_informado"],
            "total_colisoes_toque_data_reconhecida":r["total_colisoes_toque_data_reconhecida"],
            "todos_calcos_no_mes":r["todos_calcos_no_mes"],
            "meses":{
                m:{
                    "toques_fora":z["toque_status"].get("fora_da_competencia",0),
                    "tipos":z["toque_fora_mes_por_tipo_movimento"],
                    "duracoes":z["toque_fora_mes_duracao_operacional"],
                    "diferenca_dias":z["toque_fora_mes_diferenca_dias_toque_menos_calco"],
                    "colisoes_perfil":z["colisoes_perfil_anonimizado"],
                    "codigos_sem_mapeamento":z["service_type_nao_mapeados"],
                    "contagem_codigos_yz":{c:z["service_type_codes"].get(c,0) for c in ("Y","Z")}
                } for m,z in r["competencias"].items()
            }
        },ensure_ascii=False,sort_keys=True))


if __name__ == "__main__":
    unittest.main()

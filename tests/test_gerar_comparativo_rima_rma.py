import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from gerar_comparativo_rima_rma import measure,pax_status,profile_csv,_month_sources,generate

HEADER=("ANO;MES;NR_AEROPORTO_REFERENCIA;NR_NATUREZA;NR_MOVIMENTO_TIPO;"
        "NR_SERVICE_TYPE;QT_CARGA;QT_PAX_LOCAL;QT_PAX_CONEXAO_DOMESTICO;"
        "QT_PAX_CONEXAO_INTERNACIONAL\n")

class FlightCargoTests(unittest.TestCase):
    def test_passenger_flight_may_carry_cargo(self):
        data=(HEADER+"2024;01;SBKP;I;P;F;1500;35;0;0\n"
               +"2024;01;SBKP;I;D;J;0;42;0;0\n"
               +"2024;01;SBKP;D;D;H;2500;0;0;0\n"
               +"2024;01;SBKP;D;P;G;0;0;0;0\n").encode()
        profile=profile_csv(data,"2024-01")
        self.assertEqual(profile["movimentos"],4)
        self.assertEqual(profile["por_natureza"]["internacional"]["com_carga__com_passageiros"],1)
        self.assertEqual(profile["por_natureza"]["internacional"]["sem_carga__com_passageiros"],1)
        self.assertEqual(profile["por_natureza"]["domestica"]["com_carga__sem_passageiros_registrados"],1)
        self.assertTrue(profile["nao_e_fluxo_aduaneiro"])

    def test_nulls_not_zero(self):
        self.assertEqual(measure({"QT_CARGA":""}),"carga_indeterminada")
        self.assertEqual(pax_status({"QT_PAX_LOCAL":"","QT_PAX_CONEXAO_DOMESTICO":"0",
                                    "QT_PAX_CONEXAO_INTERNACIONAL":"0"}),"passageiros_indeterminados")

    def test_incomplete_passenger_data_positive_still_known(self):
        self.assertEqual(pax_status({"QT_PAX_LOCAL":"1","QT_PAX_CONEXAO_DOMESTICO":"",
                                    "QT_PAX_CONEXAO_INTERNACIONAL":""}),"com_passageiros")

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):measure({"QT_CARGA":"-1"})
        with self.assertRaises(ValueError):pax_status({"QT_PAX_LOCAL":"-1",
            "QT_PAX_CONEXAO_DOMESTICO":"0","QT_PAX_CONEXAO_INTERNACIONAL":"0"})

    def test_mixed_month_rejected(self):
        with self.assertRaisesRegex(ValueError,"competência"):
            profile_csv((HEADER+"2024;02;SBKP;I;D;J;10;5;0;0\n").encode(),"2024-01")


class MonthlyExpansionTests(unittest.TestCase):
    def test_sparse_months_are_not_zero_and_preliminary_overlap_is_preserved(self):
        report={"resultado":"aprovado_tecnicamente","erros":[],
          "comparacoes":{
           "2020-01":{"grupos":{
             "domestica/pouso":{"registros":1,"carga_kg":"2000","status":"completo"},
             "domestica/decolagem":{"registros":1,"carga_kg":"3000","status":"completo"},
             "internacional/pouso":{"registros":1,"carga_kg":"4000","status":"completo"},
             "internacional/decolagem":{"registros":1,"carga_kg":"5000","status":"completo"}}},
           "2024-01":{"grupos":{
             "domestica/pouso":{"registros":1,"carga_kg":"2000","status":"completo"},
             "domestica/decolagem":{"registros":1,"carga_kg":"3000","status":"completo"},
             "internacional/pouso":{"registros":1,"carga_kg":"4000","status":"completo"},
             "internacional/decolagem":{"registros":1,"carga_kg":"5000","status":"completo"}}}
           }}
        rma={"2025-01":{"mes":"2025-01","status":"rma_painel_atual",
                        "fonte":"RMA_concessionaria_dashboard",
                        "carga_domestica_t":"6","carga_internacional_t":"7",
                        "courier_internacional_t":"1"}}
        preliminary={"mes":"2024-01","status":"transcricao_preliminar_nao_certificada",
                     "url_pdf":"https://www.viracopos.com/rma.pdf",
                     "carga_domestica_t":"5","carga_internacional_t":"10",
                     "courier_internacional_t":"1",
                     "movimentos_domesticos":2,"movimentos_internacionais":2}
        manifest={"competencias":{
         "2020-01":{"sha256_sbkp_gzip":"a"*64},
         "2024-01":{"sha256_sbkp_gzip":"b"*64}}}
        series,overlap,comparison=_month_sources(report,rma,preliminary,manifest)
        self.assertEqual(len(series),6)  # 3 distinct months x 2 natures
        self.assertEqual(len(overlap),2)
        self.assertEqual({r["mes"] for r in overlap},{"2024-01"})
        first=next(x for x in series if x["mes"]=="2020-01" and x["natureza"]=="internacional")
        self.assertEqual(first["rima_carga_t"],9)
        self.assertIsNone(first["rma_carga_t"])
        later=next(x for x in series if x["mes"]=="2025-01" and x["natureza"]=="internacional")
        self.assertIsNone(later["rima_carga_t"])
        self.assertIsNone(later["rma_movimentos"])
        self.assertEqual(later["qualidade_rma"],"serie_rma_dashboard")
        pair=next(x for x in overlap if x["natureza"]=="internacional")
        self.assertEqual(pair["qualidade_rma"],"transcricao_preliminar_pdf_nao_certificado")
        self.assertFalse(comparison["liberado_dashboard"])

    def test_repository_profiles_cover_all_archived_months(self):
        from validar_dados import ROOT
        result=generate(ROOT)
        self.assertEqual(result["versao"],2)
        import json
        months = sorted(json.loads((ROOT/"data/anac/rima/manifesto.json").read_text(encoding="utf-8"))["competencias"])
        self.assertEqual([p["mes"] for p in result["perfil_voos"]], months)
        self.assertEqual(len(result["recortes"]),2)
        self.assertEqual(result["meses_anac"],len(months))
        self.assertEqual(result["meses_com_duas_fontes"],1)
        self.assertFalse(result["liberado_para_indicadores"])
        self.assertEqual(result["perfil_voos"][-1]["movimentos"],9348)

if __name__=="__main__":
    unittest.main()

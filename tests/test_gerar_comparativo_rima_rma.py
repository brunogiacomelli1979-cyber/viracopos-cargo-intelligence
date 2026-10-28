import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from gerar_comparativo_rima_rma import measure,pax_status,profile_csv

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

if __name__=="__main__":
    unittest.main()

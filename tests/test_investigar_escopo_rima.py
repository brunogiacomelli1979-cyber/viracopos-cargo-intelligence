import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from investigar_escopo_rima import profile_csv

HEADER = "ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;NR_SERVICE_TYPE;QT_CARGA\n"

class ServiceProfileTests(unittest.TestCase):
    def test_sums_by_service_and_movement(self):
        data=(HEADER + "2024;01;SBKP;P;I;F;1000\n"
              + "2024;01;SBKP;D;I;F;2000\n"
              + "2024;01;SBKP;P;D;J;500\n").encode()
        r=profile_csv(data, "2024-01")
        self.assertEqual(r["total_internacional_kg"], "3000")
        self.assertEqual(r["total_domestica_kg"], "500")
        self.assertEqual(r["registros"],3)
        self.assertFalse(r["publicavel"])

    def test_missing_cargo_is_rejected(self):
        data=(HEADER+"2024;01;SBKP;P;I;F;\n").encode()
        with self.assertRaisesRegex(ValueError,"ausente"):
            profile_csv(data,"2024-01")

    def test_wrong_month_rejected(self):
        data=(HEADER+"2023;01;SBKP;P;I;F;1000\n").encode()
        with self.assertRaisesRegex(ValueError,"competência"):
            profile_csv(data,"2024-01")

if __name__=="__main__":
    unittest.main()

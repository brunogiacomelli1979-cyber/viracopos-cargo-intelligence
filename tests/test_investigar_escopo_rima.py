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

    def test_date_audit_with_out_of_month_calco(self):
        header = HEADER.strip() + ";DT_CALCO\n"
        data = (header +
                "2024;01;SBKP;P;I;F;1000;2024-01-03\n" +
                "2024;01;SBKP;D;I;F;2000;2024-02-01\n" +
                "2024;01;SBKP;P;D;J;500;31/01/2024\n").encode()
        r = profile_csv(data, "2024-01")
        self.assertEqual(r["auditoria_calco"]["ocorrencias"]["na_competencia"], 2)
        self.assertEqual(r["auditoria_calco"]["ocorrencias"]["fora_da_competencia"], 1)
        self.assertEqual(r["total_internacional_kg"], "3000")
        self.assertFalse(r["publicavel"])

    def test_unknown_date_not_silently_assumed_valid(self):
        header = HEADER.strip() + ";DT_CALCO\n"
        data = (header + "2024;01;SBKP;P;I;F;1000;SEM_DATA\n").encode()
        r = profile_csv(data, "2024-01")
        self.assertEqual(r["auditoria_calco"]["ocorrencias"]["formato_desconhecido"], 1)

    def test_composite_movement_collision_is_flagged_not_deleted(self):
        header = HEADER.strip() + ";NR_AERONAVE_MARCAS;DT_CALCO;HH_CALCO;DT_TOQUE;HH_TOQUE\n"
        data = (header +
                "2024;01;SBKP;P;I;F;1000;PTABC;2024-01-03;12:00;2024-01-03;11:50\n" +
                "2024;01;SBKP;P;I;F;2000;PTABC;2024-01-03;12:00;2024-01-03;11:50\n" +
                "2024;01;SBKP;D;D;J;500;PTABC;2024-01-04;12:00;2024-01-04;12:30\n").encode()
        report = profile_csv(data, "2024-01")
        audit = report["auditoria_chaves_movimento"]
        self.assertEqual(audit["cobertura"]["calco"], 3)
        self.assertEqual(audit["colisoes_potenciais"]["calco"], 1)
        self.assertEqual(audit["colisoes_potenciais"]["toque"], 1)
        self.assertEqual(report["registros"], 3)
        self.assertEqual(report["total_internacional_kg"], "3000")

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

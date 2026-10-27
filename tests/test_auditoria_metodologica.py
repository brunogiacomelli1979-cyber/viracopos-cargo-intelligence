"""Testes do protocolo estatístico, inclusive limites de publicação."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from auditar_metodologia import monthly_profile,same_month_yoy,matched_ytd,rolling_benchmark
class MethodTests(unittest.TestCase):
    def test_sample_sd(self):
        p=monthly_profile([{"mes":"2025-01","v":10},{"mes":"2025-02","v":20},{"mes":"2025-03","v":30}],"v")
        self.assertEqual((p["media"],p["desvio_padrao_amostral"],p["cv_pct"]),(20,10,50))
    def test_gap(self):
        p=monthly_profile([{"mes":"2025-01","v":1},{"mes":"2025-03","v":3}],"v")
        self.assertEqual(p["lacunas"],["2025-02"])
    def test_yoy_denominator_and_matching(self):
        r=[{"mes":"2025-01","v":0},{"mes":"2025-08","v":100},{"mes":"2026-01","v":9},{"mes":"2026-08","v":115}]
        self.assertEqual([x["variacao_pct"] for x in same_month_yoy(r,"v")],[15])
    def test_ytd_requires_january(self):
        self.assertIsNone(matched_ytd([{"mes":"2025-02","v":100},{"mes":"2026-02","v":110}],"v",2026))
    def test_ytd_matched_months(self):
        r=[{"mes":"2025-01","v":100},{"mes":"2025-02","v":200},{"mes":"2026-01","v":110},{"mes":"2026-02","v":220}]
        self.assertEqual(matched_ytd(r,"v",2026)["variacao_pct"],10)
    def test_history_insufficient(self):
        r=[{"mes":f"{2025+i//12}-{i%12+1:02d}","v":100+i} for i in range(20)]
        for mode in ("naive","seasonal_naive"):
            self.assertEqual(rolling_benchmark(r,"v",mode=mode)["status"],"bloqueado")
    def test_expanding_origin_one_step(self):
        r=[{"mes":f"{2020+i//12}-{i%12+1:02d}","v":float(i)} for i in range(40)]
        p=rolling_benchmark(r,"v",min_train=24,min_test=12)
        self.assertEqual((p["status"],p["dobras"],p["mae"],p["rmse"]),("avaliacao_retroativa",16,1,1))
if __name__=="__main__":unittest.main()

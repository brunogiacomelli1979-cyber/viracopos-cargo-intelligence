import hashlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from coletar_comex import aggregate_lines, merge_month_flows, datasets_to_rows


class ComexTests(unittest.TestCase):
    def test_stream_filters_urf_and_air_and_preserves_units(self):
        raw=(b'"CO_ANO";"CO_MES";"CO_NCM";"CO_VIA";"CO_URF";"KG_LIQUIDO";"VL_FOB"\n'
             b'2026;1;30041010;4;817700;100;1000000\n'
             b'2026;1;30049010;04;0817700;250;2000000\n'
             b'2026;1;30049010;1;817700;900;3000000\n'
             b'2026;1;30049010;4;817600;800;4000000\n')
        result=aggregate_lines(io.BytesIO(raw),2026,'IMP')
        self.assertEqual(result['sectors'],[{'mes':'2026-01','sh2':'30','valor_fob_usd':3000000,'kg_liquido':350}])
        self.assertEqual(result['brasil']['2026-01'],10000000)
        self.assertEqual(result['receipt']['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['receipt']['linhas_recorte'],2)
        rows,_=datasets_to_rows([result],{'30':'Produtos farmacêuticos'})
        self.assertEqual(rows[0]['fluxo'],'importacao')
        self.assertEqual(rows[0]['setor'],'SH30 · Produtos farmacêuticos')

    def test_revision_replaces_month_flow_including_removed_sector(self):
        existing=[{'mes':'2025-12','fluxo':'importacao','setor':'SH30','valor_fob_usd':1,'kg_liquido':1},
                  {'mes':'2026-01','fluxo':'importacao','setor':'SH30','valor_fob_usd':2,'kg_liquido':2},
                  {'mes':'2026-01','fluxo':'importacao','setor':'SH84','valor_fob_usd':3,'kg_liquido':3},
                  {'mes':'2026-01','fluxo':'exportacao','setor':'SH84','valor_fob_usd':4,'kg_liquido':4}]
        fresh=[{'mes':'2026-01','fluxo':'importacao','setor':'SH30','valor_fob_usd':9,'kg_liquido':8}]
        result=merge_month_flows(existing,fresh)
        self.assertEqual(len(result),3)
        self.assertNotIn(existing[2],result)
        self.assertIn(existing[0],result)
        self.assertIn(existing[3],result)
        self.assertIn(fresh[0],result)

    def test_month_with_no_selected_sector_removes_old_group(self):
        old=[{'mes':'2026-01','fluxo':'importacao','setor':'SH30','valor_fob_usd':2,'kg_liquido':2}]
        self.assertEqual(merge_month_flows(old,[],{('2026-01','importacao')}),[])


if __name__ == '__main__':unittest.main()

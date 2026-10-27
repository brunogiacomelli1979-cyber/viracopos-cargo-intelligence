import hashlib
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atualizar import aggregate, collect, build
from validar_dados import ROOT, validate_rows, validate_project


class PipelineTests(unittest.TestCase):
    def test_html_links_assets_and_unique_ids(self):
        from html.parser import HTMLParser
        class PageParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids, self.anchors, self.assets = [], [], []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if 'id' in attrs:
                    self.ids.append(attrs['id'])
                for key in ('href', 'src'):
                    value = attrs.get(key, '')
                    if value.startswith('#'):
                        self.anchors.append(value[1:])
                    elif value.startswith('assets/'):
                        self.assets.append(value)
        parser = PageParser()
        parser.feed((ROOT / 'index.html').read_text(encoding='utf-8'))
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertTrue(all(anchor in parser.ids for anchor in parser.anchors))
        self.assertTrue(all((ROOT / path).is_file() for path in parser.assets))

    def test_project_consistency(self):
        validate_project()

    def test_archive_unchanged(self):
        for item in json.loads((ROOT / 'docs/archive/manifest.json').read_text(encoding='utf-8-sig')):
            content = (ROOT / 'docs/archive/initial' / item['path']).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), item['sha256'])

    def test_duplicate_month_rejected(self):
        row = {'mes': '2020-01', 'exportacoes_usd_bi': 1, 'importacoes_usd_bi': 2}
        with self.assertRaisesRegex(ValueError, 'duplicada'):
            validate_rows('brasil', [row, row])

    def test_invalid_values_rejected(self):
        for value in [float('nan'), float('inf'), -1, None, True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_rows('brasil', [{'mes': '2020-01', 'exportacoes_usd_bi': value, 'importacoes_usd_bi': 2}])

    def test_current_month_rejected(self):
        with self.assertRaises(ValueError):
            validate_rows('brasil', [{'mes': '2026-10', 'exportacoes_usd_bi': 1, 'importacoes_usd_bi': 2}], today=date(2026,10,27))

    def test_monthly_aggregation(self):
        data = [{'data': '31/01/2020', 'valor': '4.0'}, {'data': '02/01/2020', 'valor': '2.0'}]
        self.assertEqual(aggregate('dolar_venda_medio_brl', data, date(2020,1,1), date(2020,1,31)), {'2020-01': 3})
        self.assertEqual(aggregate('selic_meta_pct_aa', data, date(2020,1,1), date(2020,1,31)), {'2020-01': 4})

    def test_deflation_is_valid(self):
        validate_rows('macro', [{'mes':'2020-01', 'selic_meta_pct_aa':None, 'dolar_venda_medio_brl':None, 'ipca_pct_mes':-0.2}])

    def test_fallback_preserves_history(self):
        rows = [{'mes':'2020-01', 'selic_meta_pct_aa':4.5, 'dolar_venda_medio_brl':4.1, 'ipca_pct_mes':0.2}]
        meta = {'macro': {}}
        with patch('atualizar.fetch_series', side_effect=OSError('indisponível')):
            result, status = collect(rows, meta, datetime(2026,10,27,tzinfo=timezone.utc))
        self.assertEqual(result, rows)
        self.assertEqual(len(status), 3)

    def test_partial_failure_and_revision(self):
        rows = [{'mes':'2020-01', 'selic_meta_pct_aa':4.5, 'dolar_venda_medio_brl':4.1, 'ipca_pct_mes':0.2}]
        def fetch(code, start, end):
            if code != 432:
                raise OSError('indisponível')
            return [{'data':'31/01/2020','valor':'4.25'}], {'url':'https://api.bcb.gov.br', 'sha256':'teste', 'registros':1}
        with patch('atualizar.fetch_series', side_effect=fetch):
            result, _ = collect(rows, {'macro':{}}, datetime(2020,2,20,tzinfo=timezone.utc))
        self.assertEqual(result[0]['selic_meta_pct_aa'], 4.25)
        self.assertEqual(result[0]['dolar_venda_medio_brl'], 4.1)

    def test_offline_deterministic_data_and_safe_embedding(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'data', root / 'data')
            shutil.copy(ROOT / 'index.template.html', root / 'index.template.html')
            before = (root/'data/macro.csv').read_bytes()
            first = build(True, root)
            second = build(True, root)
            self.assertEqual(first['macro'], second['macro'])
            self.assertEqual(first['coleta_bcb'], second['coleta_bcb'])
            self.assertEqual(before, (root/'data/macro.csv').read_bytes())
            validate_project(root)


if __name__ == '__main__':
    unittest.main()

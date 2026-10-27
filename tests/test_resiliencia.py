"""Testes de regressão para respostas transitórias SGS e falhas parciais RMA."""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atualizar import fetch_series
from coletar_carga_vcp import INDEX_URL, collect_rma

class ResilienciaTest(unittest.TestCase):
    def test_sgs_retries_invalid_json_without_disabling_tls(self):
        payload = json.dumps([{"data": "01/09/2026", "valor": "5.10"}]).encode()
        with patch("atualizar.get_bytes", side_effect=[b"<html>temporarily unavailable</html>", payload]) as fetch, patch("atualizar.time.sleep") as sleep:
            data, receipt = fetch_series(1, datetime(2026,9,1).date(), datetime(2026,9,30).date())
        self.assertEqual(fetch.call_count, 2)
        sleep.assert_called_once_with(1)
        self.assertEqual(data[0]["valor"], "5.10")
        self.assertEqual(receipt["registros"], 1)

    def test_sgs_retries_empty_or_wrong_shape(self):
        good = b'[{"data":"01/09/2026","valor":"5.0"}]'
        with patch("atualizar.get_bytes", side_effect=[b"{}", b"[]", good]) as fetch, patch("atualizar.time.sleep"):
            data, _ = fetch_series(1, datetime(2026,9,1).date(), datetime(2026,9,30).date())
        self.assertEqual(len(data), 1)
        self.assertEqual(fetch.call_count, 3)

    def test_rma_skips_invalid_pdf_when_another_is_valid(self):
        bad = "https://www.viracopos.com/data/files/RMA%202026%20JAN.pdf"
        good = "https://www.viracopos.com/data/files/RMA%202026%20FEV.pdf"
        index = f'<a href="{bad}">Jan</a><a href="{good}">Fev</a>'.encode()
        def fetch(url):
            if url == INDEX_URL: return index
            if url == bad: raise OSError("certificado inválido")
            return b"valid-pdf"
        rows = [{"mes":"2026-01","carga_internacional_t":20,"carga_domestica_t":10,"courier_internacional_t":3}]
        control = {"ano":2026,"pagina":1,"meses":1,"controle_publicado_t":{}}
        with patch("coletar_carga_vcp.extract_rma", return_value=(rows,control)):
            found, metadata = collect_rma(fetcher=fetch,now=datetime(2026,3,1,tzinfo=timezone.utc))
        self.assertEqual(found,rows)
        self.assertEqual(len(metadata["documentos"]),1)
        self.assertEqual(metadata["avisos_coleta"][0]["url"],bad)

    def test_rma_never_marks_all_failed_documents_as_success(self):
        url = "https://www.viracopos.com/data/files/RMA%202026%20FEV.pdf"
        def fetch(target):
            if target == INDEX_URL: return f'<a href="{url}">RMA</a>'.encode()
            raise OSError("TLS indisponível")
        with self.assertRaisesRegex(ValueError,"nenhum boletim acessível"):
            collect_rma(fetcher=fetch,now=datetime(2026,3,1,tzinfo=timezone.utc))

if __name__ == "__main__":
    unittest.main()

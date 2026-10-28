import io
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from baixar_original_anac import fetch_and_register, CaptureError
from acervo_bruto_anac import audit
from test_ingestao_controlada_anac import URL, DATA


class Response:
    def __init__(self, url, data, status=200, headers=None, fail=False):
        self.url, self.reader, self.status = url, io.BytesIO(data), status
        self.headers = headers or {"Content-Length": str(len(data))}
        self.fail = fail
        self.reads = 0
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def geturl(self): return self.url
    def read(self, size):
        self.reads += 1
        if self.fail and self.reads == 2:
            raise URLError("quebra no meio")
        return self.reader.read(size if not self.fail else 10)


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name) / "vault"

    def assert_clean(self):
        self.assertEqual(list((self.store / "incoming").glob("*.partial")), [])
        self.assertEqual(list((self.store / "objects").glob("*/*.csv")), [])

    def test_transfer_completa_arquivo_e_recibo(self):
        count = []
        def opener(*_, **kwargs):
            self.assertIsNotNone(kwargs.get("context"))
            count.append(1)
            return Response(URL, DATA)
        receipt = fetch_and_register("2020-04", URL, self.store, opener=opener)
        self.assertEqual(len(count), 1)
        self.assertEqual(receipt["bytes"], len(DATA))
        self.assertTrue(audit(self.store)["aprovado"])

    def test_404_not_retried(self):
        count = []
        def opener(request, **_):
            count.append(1)
            raise HTTPError(URL, 404, "not found", {}, None)
        with self.assertRaises(CaptureError) as err:
            fetch_and_register("2020-04", URL, self.store, opener=opener)
        self.assertEqual(err.exception.category, "origem_nao_encontrada")
        self.assertEqual(len(count), 1)
        self.assert_clean()

    def test_timeout_retry_then_success(self):
        count = []
        def opener(request, **_):
            count.append(1)
            if len(count) == 1:
                raise URLError("timeout")
            return Response(URL, DATA)
        waits = []
        result = fetch_and_register("2020-04", URL, self.store, opener=opener, wait=waits.append)
        self.assertEqual(result["bytes"], len(DATA))
        self.assertEqual(len(waits), 1)
        self.assertEqual(len(count), 2)

    def test_midstream_failure_never_commits_partial(self):
        def opener(request, **_): return Response(URL, DATA, fail=True)
        with self.assertRaises(CaptureError) as err:
            fetch_and_register("2020-04", URL, self.store, opener=opener, wait=lambda _:None)
        self.assertEqual(err.exception.category, "falha_transitoria")
        self.assert_clean()

    def test_206_never_accepted(self):
        with self.assertRaises(CaptureError) as err:
            fetch_and_register("2020-04", URL, self.store, opener=lambda *_ , **__: Response(URL, DATA[:10], status=206))
        self.assertEqual(err.exception.category, "resposta_invalida")
        self.assert_clean()

    def test_length_mismatch_never_accepted(self):
        with self.assertRaises(CaptureError):
            fetch_and_register("2020-04", URL, self.store, opener=lambda *_ , **__: Response(URL, DATA, headers={"Content-Length":str(len(DATA)+1)}))
        self.assert_clean()

    def test_redirection_never_accepted(self):
        with self.assertRaises(CaptureError):
            fetch_and_register("2020-04", URL, self.store, opener=lambda *_ , **__: Response("https://other.example/data.csv", DATA))
        self.assert_clean()

    def test_429_retry_after_is_bounded(self):
        calls, sleeps = [], []
        def opener(request, **_):
            calls.append(1)
            if len(calls) == 1:
                raise HTTPError(URL, 429, "rate limit", {"Retry-After":"240"}, None)
            return Response(URL, DATA)
        result = fetch_and_register("2020-04", URL, self.store, opener=opener, wait=sleeps.append)
        self.assertEqual(result["bytes"], len(DATA))
        self.assertEqual(sleeps, [60])

    def test_header_invalid_file_does_not_create_receipt(self):
        with self.assertRaises(ValueError):
            fetch_and_register("2020-04", URL, self.store, opener=lambda *_ , **__: Response(URL, b"<html>error</html>"))
        self.assert_clean()

if __name__ == "__main__":
    unittest.main()

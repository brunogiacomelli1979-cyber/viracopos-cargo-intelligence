"""Modulo opt-in para captura HTTPS ANAC em streaming; NAO acionado por workflows.

NENHUMA execucao de rede ocorre ao importar este modulo. O chamador deve
aprovar manualmente cada competencia; nenhuma rotina de backfill/cron o utiliza.
"""
import ssl
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from acervo_bruto_anac import CHUNK, MAX_BYTES, register, validate_input


class CaptureError(RuntimeError):
    def __init__(self, category, explanation):
        self.category = category
        super().__init__(f"{category}: {explanation}")


def fetch_and_register(month, url, store, *, opener=urlopen, wait=time.sleep,
                       attempts=2, max_bytes=MAX_BYTES):
    """Transfere CSV integral para arquivo temporario; registra bruto por hash.

    Faz retry apenas para timeout/erro de rede/HTTP 429 ou 5xx. 404 e resposta
    parcial sao terminais. Respostas invalidas nao alteram manifesto ou recibos.
    """
    store = Path(store)
    validate_input(month, url, store)
    if not 1 <= attempts <= 3:
        raise ValueError("Numero de tentativas deve estar entre 1 e 3")
    store.mkdir(parents=True, exist_ok=True)
    incoming = store / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "VCP-Insights-RIMA-raw/1.0",
                                    "Accept": "text/csv,text/plain,application/octet-stream"})
    for attempt in range(attempts):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=incoming, prefix="download-", suffix=".partial", delete=False) as tmp:
                temp_path = Path(tmp.name)
                with opener(request, timeout=55, context=ssl.create_default_context()) as response:
                    if response.geturl() != url:
                        raise CaptureError("resposta_invalida", "Redirecionamento nao autorizado")
                    if response.status != 200:
                        raise CaptureError("resposta_invalida", f"HTTP {response.status} nao e arquivo integral")
                    expected = response.headers.get("Content-Length") if response.headers else None
                    if expected is not None:
                        try:
                            expected = int(expected)
                        except (TypeError, ValueError) as exc:
                            raise CaptureError("resposta_invalida", "Content-Length invalido") from exc
                        if expected < 1 or expected > max_bytes:
                            raise CaptureError("resposta_invalida", "Content-Length fora do limite")
                    total = 0
                    while chunk := response.read(CHUNK):
                        total += len(chunk)
                        if total > max_bytes:
                            raise CaptureError("resposta_invalida", "Arquivo excede limite de tamanho")
                        tmp.write(chunk)
                    if total == 0 or (expected is not None and total != expected):
                        raise CaptureError("resposta_invalida", "Transferencia vazia ou truncada")
            return register(temp_path, month, url, store, limit=max_bytes)
        except HTTPError as exc:
            if exc.code == 404:
                raise CaptureError("origem_nao_encontrada", "HTTP 404; verificar inventario") from exc
            if exc.code != 429 and not 500 <= exc.code <= 599:
                raise CaptureError("resposta_invalida", f"HTTP {exc.code}") from exc
            if attempt + 1 == attempts:
                raise CaptureError("falha_transitoria", f"HTTP {exc.code} apos {attempts} tentativas") from exc
            retry_header = exc.headers.get("Retry-After") if exc.headers else None
            seconds = min(60, max(0, int(retry_header))) if retry_header and retry_header.isdigit() else min(8, 2**attempt)
            wait(seconds)
        except (URLError, TimeoutError, ConnectionError) as exc:
            if attempt + 1 == attempts:
                raise CaptureError("falha_transitoria", f"Falha de rede apos {attempts} tentativas") from exc
            wait(min(8, 2**attempt))
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)
    raise AssertionError("Tentativas esgotadas sem decisao")

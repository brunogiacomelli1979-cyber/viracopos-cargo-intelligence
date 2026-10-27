"""Leitura pública HTTPS com verificação TLS e fallback ao cliente nativo."""
import shutil
import subprocess
from urllib.request import Request, urlopen


def get_bytes(url, timeout=40):
    request = Request(url, headers={"User-Agent": "VCP-Insights/2.0 (public research)"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except Exception as original:
        # Windows Schannel can build a current trust chain when OpenSSL cannot.
        # curl keeps all default certificate/hostname checks; never use --insecure.
        curl = shutil.which("curl.exe") or shutil.which("curl")
        if not curl:
            raise
        result = subprocess.run([curl, "--fail", "--silent", "--show-error", "--location", "--max-time", str(timeout), url], capture_output=True, timeout=timeout + 5)
        if result.returncode:
            raise OSError(f"HTTPS indisponível: {original}; curl: {result.stderr.decode(errors='replace').strip()}") from original
        return result.stdout

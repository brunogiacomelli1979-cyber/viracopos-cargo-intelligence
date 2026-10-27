"""Verificação independente de acervo oficial: arquivos, SHA-256 e formatos."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs/referencias/anac/manifesto.json"


def validate_archive(root=ROOT):
    manifest = json.loads((root / "docs/referencias/anac/manifesto.json").read_text(encoding="utf-8"))
    errors = []
    verified = []
    pending = []
    for item in manifest["documentos"]:
        if item["status"] != "baixado":
            pending.append(item["id"])
            if item["essential"]:
                errors.append(f"{item['id']}: documento essencial pendente")
            continue
        p = root / item["file"]
        if not p.is_file():
            errors.append(f"{item['id']}: arquivo não encontrado")
            continue
        data = p.read_bytes()
        if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            errors.append(f"{item['id']}: integridade SHA-256/tamanho divergente")
            continue
        if item["type"] == "pdf":
            if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-4096:]:
                errors.append(f"{item['id']}: assinatura PDF inválida")
                continue
        elif item["type"] == "html":
            if b"<html" not in data[:5000].lower():
                errors.append(f"{item['id']}: HTML inválido")
                continue
        else:
            errors.append(f"{item['id']}: formato desconhecido")
            continue
        verified.append(item["id"])
    if errors:
        raise ValueError("; ".join(errors))
    return {"verificados": verified, "pendentes_opcionais": pending, "quantidade": len(verified)}


if __name__ == "__main__":
    print(json.dumps(validate_archive(), indent=2, ensure_ascii=False))

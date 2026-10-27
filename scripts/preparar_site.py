"""Copia somente arquivos públicos para _site; não inclui fontes e arquivos antigos."""
import shutil
from pathlib import Path

from validar_dados import ROOT, validate_project


def prepare(root=ROOT):
    validate_project(root)
    target = root / "_site"
    target.mkdir(exist_ok=True)
    for name in ("index.html", "index_blue.html"):
        shutil.copy2(root / name, target / name)
    shutil.copytree(root / "assets", target / "assets", dirs_exist_ok=True)
    (target / "data").mkdir(exist_ok=True)
    for name in ("dashboard.json", "fontes.json", "viracopos.csv", "comex_viracopos.csv", "brasil.csv", "macro.csv"):
        shutil.copy2(root / "data" / name, target / "data" / name)
    (target / ".nojekyll").touch()
    print(f"Site validado em {target}")


if __name__ == "__main__":
    prepare()

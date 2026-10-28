import gzip
import copy
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from arquivar_anac_rima import month_sequence, filter_sbkp, store_month, load_manifest, official_url, choose_months, run, _verify_snapshot

HEADER = "ANO;MES;NR_AEROPORTO_REFERENCIA;NR_MOVIMENTO_TIPO;NR_NATUREZA;QT_CARGA;QT_CORREIO\n"
ROWS = (HEADER + "2024;01;SBKP;P;I;100;1\n" +
        "2024;01;SBGR;P;I;800;9\n" +
        "2024;01;SBKP;D;D;;0\n").encode("utf-8")

class ArchiveTests(unittest.TestCase):
    def test_months(self):
        self.assertEqual(list(month_sequence("2023-12","2024-02")), ["2023-12","2024-01","2024-02"])
        self.assertIn("2024/Movimentacoes_Aeroportuarias_202401.csv", official_url("2024-01"))

    def test_reject_dates_before_2020(self):
        with self.assertRaisesRegex(ValueError, "recorte aprovado"):
            list(month_sequence("2019-12", "2020-01"))
        self.assertEqual(list(month_sequence("2020-01", "2020-02")),
                         ["2020-01", "2020-02"])

    def test_filter_keeps_sbkp_and_missing(self):
        compressed, meta = filter_sbkp(ROWS, "2024-01")
        text = gzip.decompress(compressed).decode("utf-8")
        self.assertEqual(meta["linhas_sbkp"], 2)
        self.assertNotIn("SBGR",text)
        self.assertIn(";;0",text)

    def test_official_update_preamble(self):
        sample = b"Atualizado em: 2025-01-01\n" + ROWS
        compressed, meta = filter_sbkp(sample, "2024-01")
        self.assertEqual(meta["linhas_sbkp"], 2)
        self.assertIn("SBKP", gzip.decompress(compressed).decode("utf-8"))

    def test_reject_unexpected_preamble(self):
        with self.assertRaises(ValueError):
            filter_sbkp(b"Erro inesperado\n" + ROWS, "2024-01")

    def test_reject_empty_and_bad_month(self):
        with self.assertRaises(ValueError):
            filter_sbkp(HEADER.encode(), "2024-01")
        with self.assertRaises(ValueError):
            filter_sbkp(ROWS, "2024-02")

    def test_manifest_and_no_overwrite_when_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/"data"/"anac"/"rima"
            manifest=load_manifest(root)
            status=store_month(root,manifest,"2024-01",ROWS,official_url("2024-01"),"2026-10-28T00:00:00+00:00")
            self.assertEqual(status,"novo")
            self.assertEqual(store_month(root,manifest,"2024-01",ROWS,official_url("2024-01"),"2026-10-28T00:00:00+00:00"),"sem_mudanca")
            saved=json.loads((root/"manifesto.json").read_text())
            self.assertEqual(saved["competencias"]["2024-01"]["sha256_original"],hashlib.sha256(ROWS).hexdigest())
            self.assertTrue((Path(temp)/saved["competencias"]["2024-01"]["caminho_sbkp"]).exists())

    def test_revision_preserves_legacy_file_and_complete_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data/anac/rima"
            manifest = load_manifest(root)
            stamp = "2026-10-28T00:00:00+00:00"
            self.assertEqual(store_month(root, manifest, "2024-01", ROWS, official_url("2024-01"), stamp), "novo")
            first = copy.deepcopy(manifest["competencias"]["2024-01"])
            first_path = Path(temp) / first["caminho_sbkp"]
            first_bytes = first_path.read_bytes()
            changed = ROWS.replace(b"100;1", b"200;1")
            self.assertEqual(store_month(root, manifest, "2024-01", changed, official_url("2024-01"), stamp), "revisado")
            second = copy.deepcopy(manifest["competencias"]["2024-01"])
            self.assertEqual(first_path.read_bytes(), first_bytes)
            self.assertEqual(second["revisoes"][0]["caminho_sbkp"], first["caminho_sbkp"])
            self.assertEqual(second["revisoes"][0]["sha256_sbkp_gzip"], first["sha256_sbkp_gzip"])
            self.assertNotEqual(second["caminho_sbkp"], first["caminho_sbkp"])
            second_path = Path(temp) / second["caminho_sbkp"]
            self.assertTrue(second_path.is_file())
            self.assertEqual(store_month(root, manifest, "2024-01", changed, official_url("2024-01"), stamp), "sem_mudanca")
            third = changed.replace(b"200;1", b"300;1")
            self.assertEqual(store_month(root, manifest, "2024-01", third, official_url("2024-01"), stamp), "revisado")
            self.assertEqual(len(manifest["competencias"]["2024-01"]["revisoes"]), 2)
            self.assertTrue(second_path.read_bytes())
            self.assertTrue(_verify_snapshot(root, second))
            self.assertTrue(_verify_snapshot(root, first))

    def test_revision_of_real_legacy_path_preserves_old_month(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data/anac/rima"
            manifest = load_manifest(root)
            stamp = "2026-10-28T00:00:00+00:00"
            raw = ROWS.replace(b"2024;01", b"2020;01")
            store_month(root, manifest, "2020-01", raw, official_url("2020-01"), stamp)
            entry = manifest["competencias"]["2020-01"]
            versioned = Path(temp) / entry["caminho_sbkp"]
            legacy = root / "sbkp/2020/2020-01.csv.gz"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_bytes(versioned.read_bytes())
            versioned.unlink()
            entry["caminho_sbkp"] = "data/anac/rima/sbkp/2020/2020-01.csv.gz"
            (root / "manifesto.json").write_text(json.dumps(manifest))
            old_bytes = legacy.read_bytes()
            revised = raw.replace(b"100;1", b"500;1")
            self.assertEqual(store_month(root, manifest, "2020-01", revised,
                                         official_url("2020-01"), stamp), "revisado")
            self.assertEqual(legacy.read_bytes(), old_bytes)
            latest = manifest["competencias"]["2020-01"]
            self.assertEqual(latest["revisoes"][0]["caminho_sbkp"],
                             "data/anac/rima/sbkp/2020/2020-01.csv.gz")
            self.assertTrue(_verify_snapshot(root, latest))
            self.assertTrue(_verify_snapshot(root, latest["revisoes"][0]))

    @staticmethod
    def make_opener(fail_month=None, failure="404"):
        class Response:
            status = 200
            def __init__(self, url, raw):
                self.url = url
                self.raw = raw
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def geturl(self):
                return self.url
            def read(self, size):
                return self.raw[:size]
        def opener(request, timeout=None, context=None):
            url = request.full_url
            month = url.split("_")[-1][:6]
            if month == fail_month:
                if failure == "404":
                    raise HTTPError(url, 404, "Not Found", {}, None)
                raise URLError("timeout simulated")
            year, mm = month[:4], month[4:]
            raw = (HEADER +
                   f"{year};{mm};SBKP;P;I;101;0\n").encode()
            return Response(url, raw)
        return opener

    def test_404_after_success_keeps_entire_repository_unchanged(self):
        for kind in ("404", "timeout"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "data/anac/rima"
                existing = load_manifest(root)
                first_raw = ROWS.replace(b"2024;01", b"2020;01")
                store_month(root, existing, "2020-01", first_raw, official_url("2020-01"), "2026-10-28T00:00:00+00:00")
                before = (root / "manifesto.json").read_bytes()
                paths_before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*.csv.gz")}
                args = SimpleNamespace(mode="inicial", start="2020-02", end="2020-03",
                                       limit=0, refresh=12, out_dir=root)
                status = run(args, opener=self.make_opener("202003", kind),
                             today=__import__("datetime").date(2026, 10, 28))
                self.assertEqual(status, 1)
                self.assertEqual((root / "manifesto.json").read_bytes(), before)
                self.assertEqual(
                    {p.relative_to(root): p.read_bytes() for p in root.rglob("*.csv.gz")},
                    paths_before)

    def test_successful_batch_commits_only_complete_months(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data/anac/rima"
            args = SimpleNamespace(mode="inicial", start="2020-01", end="2020-02",
                                   limit=0, refresh=12, out_dir=root)
            code = run(args, opener=self.make_opener(), today=__import__("datetime").date(2026,10,28))
            self.assertEqual(code, 0)
            manifest = load_manifest(root)
            self.assertEqual(sorted(manifest["competencias"]), ["2020-01", "2020-02"])
            for entry in manifest["competencias"].values():
                self.assertTrue(_verify_snapshot(root, entry))
                self.assertIn("/versoes/", entry["caminho_sbkp"])

    def test_invalid_weight_rejected_before_promoting_any_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data/anac/rima"
            receipt = load_manifest(root)
            original = ROWS.replace(b"2024;01", b"2020;01").replace(b";;0", b";50;0")
            store_month(root, receipt, "2020-01", original,
                        official_url("2020-01"), "2026-10-28T00:00:00+00:00")
            before = (root / "manifesto.json").read_bytes()
            prior_files = {p.relative_to(root):p.read_bytes() for p in root.rglob("*.csv.gz")}

            class Response:
                status = 200
                def __init__(self, url):
                    self.url = url
                def __enter__(self):
                    return self
                def __exit__(self, *exc):
                    return False
                def geturl(self):
                    return self.url
                def read(self, count):
                    csvdata = (HEADER + "2020;03;SBKP;P;I;-100;0\n").encode()
                    return csvdata[:count]
            def opener(request, timeout=None, context=None):
                return Response(request.full_url)

            args = SimpleNamespace(mode="inicial", start="2020-03", end="2020-03",
                                   refresh=0, limit=1, out_dir=root)
            result = run(args, opener=opener,
                         today=__import__("datetime").date(2026, 10, 28))
            self.assertEqual(result, 1)
            self.assertEqual((root / "manifesto.json").read_bytes(), before)
            self.assertEqual({p.relative_to(root):p.read_bytes() for p in root.rglob("*.csv.gz")},
                             prior_files)
            self.assertNotIn("2020-03", load_manifest(root)["competencias"])

    def test_monthly_selects_missing_and_refresh(self):
        manifest={"competencias":{"2024-01":{}}}
        months=choose_months(manifest,"mensal","2024-01","2024-03",1,0)
        self.assertEqual(months,["2024-02","2024-03"])
if __name__ == "__main__":
    unittest.main()

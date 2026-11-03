"""Testes das ferramentas da Fase 0 com arquivos sintéticos (nenhum dado do jogo)."""
from __future__ import annotations

import io
import json
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import check_content  # noqa: E402
import inspect_dump  # noqa: E402


def fake_nso(build_id_prefix: str, text=0x1000, ro=0x2000, data=0x800, bss=0x3000) -> bytes:
    hdr = bytearray(0x100)
    hdr[0:4] = b"NSO0"
    struct.pack_into("<I", hdr, 0x0C, 7)
    struct.pack_into("<III", hdr, 0x10, 0x100, 0, text)
    struct.pack_into("<III", hdr, 0x20, 0x100 + text, text, ro)
    struct.pack_into("<III", hdr, 0x30, 0x100 + text + ro, text + ro, data)
    struct.pack_into("<I", hdr, 0x3C, bss)
    hdr[0x40:0x50] = bytes.fromhex(build_id_prefix)
    return bytes(hdr)


def fake_npdm(sys_res=0) -> bytes:
    meta = bytearray(0x80)
    meta[0:4] = b"META"
    meta[0x0C] = 1
    meta[0x0E] = 44
    meta[0x0F] = 0
    struct.pack_into("<I", meta, 0x14, sys_res)
    struct.pack_into("<I", meta, 0x1C, 0x100000)
    meta[0x20:0x24] = b"test"
    return bytes(meta)


class InspectDumpTest(unittest.TestCase):
    def make_exefs(self, d: Path, ids: dict[str, str]) -> None:
        for m, bid in ids.items():
            (d / m).write_bytes(fake_nso(bid))
        (d / "main.npdm").write_bytes(fake_npdm())

    def test_identifies_130(self):
        known = json.loads(inspect_dump.KNOWN.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            self.make_exefs(d, known["builds"]["1.3.0"]["modules"])
            out = d / "r.json"
            with redirect_stdout(io.StringIO()):
                rc = inspect_dump.main(["--exefs", str(d), "--out", str(out)])
            self.assertEqual(rc, 0)
            r = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(r["version"], "1.3.0")
            self.assertEqual(r["npdm"]["system_resource_size"], 0)
            self.assertEqual(r["modules"]["main"]["image_size"], 0x7000)

    def test_unknown_build_fails(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            self.make_exefs(d, {m: "00" * 16 for m in inspect_dump.MODULES})
            with redirect_stdout(io.StringIO()):
                self.assertEqual(inspect_dump.main(["--exefs", str(d)]), 1)

    def test_romfs_classify(self):
        self.assertEqual(inspect_dump.classify("asset/system.rdb"), "rdb-index")
        self.assertEqual(inspect_dump.classify("asset/system.rdb.bin1"), "rdb-data")
        self.assertEqual(inspect_dump.classify("asset/x.rdb.bin3_0"), "rdb-dlc")
        self.assertEqual(inspect_dump.classify("asset/data/0001.file"), "rdb-file")


class CheckContentTest(unittest.TestCase):
    def check(self, rel: str, content: bytes) -> list[str]:
        # Escreve num diretório temporário: o teste nunca cria arquivos dentro do repositório.
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            return check_content.check_file(rel, root=Path(t))

    def test_clean_source_passes(self):
        self.assertEqual(self.check("tests/_tmp_ok.py", b"print('ok')\n"), [])

    def test_blocks_game_files(self):
        self.assertTrue(check_content.check_file("asset/system.rdb.bin1"))
        self.assertTrue(check_content.check_file("asset/x.rdb.bin3_0"))
        self.assertTrue(check_content.check_file("game/base.nsp"))
        self.assertTrue(check_content.check_file("build/v130/exefs/main"))
        self.assertTrue(check_content.check_file("prod.keys"))
        self.assertEqual(check_content.check_file("runtime/binding.c"), [])

    def test_blocks_binary_magic(self):
        self.assertTrue(self.check("tests/_tmp_nso.dat", b"NSO0" + b"\0" * 60))

    def test_blocks_keys_text(self):
        self.assertTrue(self.check("tests/_tmp_k.txt", b"header_key = " + b"ab" * 32 + b"\n"))

    def test_blocks_generated_marker(self):
        self.assertTrue(self.check("tests/_tmp_g.c", f"// {check_content.GENERATED_MARKER}\n".encode()))


if __name__ == "__main__":
    unittest.main()

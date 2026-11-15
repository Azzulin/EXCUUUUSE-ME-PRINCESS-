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


try:   # nx.py precisa do pacote cryptography, que o CI mínimo não instala
    import extract_dlc
except ImportError:
    extract_dlc = None


def fake_ivfc(data: bytes, block_log2: int = 12):
    """Cabeçalho de seção IVFC e bytes da seção para `data` no nível de dados: (fs, seção)."""
    import hashlib
    block = 1 << block_log2

    def hashes(level: bytes) -> bytes:
        out = b""
        for pos in range(0, len(level), block):
            part = level[pos:pos + block]
            out += hashlib.sha256(part + bytes(block - len(part))).digest()
        return out

    levels = [data]
    for _ in range(5):
        levels.insert(0, hashes(levels[0]))
    fs = bytearray(0x200)
    fs[8:12] = b"IVFC"
    struct.pack_into("<II", fs, 0x10, 0x20, 7)
    section, off = b"", 0
    for k, level in enumerate(levels):
        struct.pack_into("<QQII", fs, 0x18 + 0x18 * k, off, len(level), block_log2, 0)
        padded = level + bytes(-len(level) % block)
        section += padded
        off += len(padded)
    fs[0xC8:0xE8] = hashes(levels[0])[:32]
    return bytes(fs), section


class FakeSection:
    def __init__(self, fs: bytes, data: bytes):
        self.fs, self.data = fs, data

    def read(self, offset: int, size: int) -> bytes:
        return self.data[offset:offset + size]


@unittest.skipUnless(extract_dlc, "sem o pacote cryptography")
class ExtractDlcTest(unittest.TestCase):
    DATA = bytes(range(256)) * 97 + b"fim"   # não é múltiplo do bloco: o último bloco é completado com zeros

    def test_copy_checks_the_hash_tree(self):
        fs, section = fake_ivfc(self.DATA)
        with tempfile.TemporaryDirectory() as d:
            size, sha = extract_dlc.copy_verified(FakeSection(fs, section), Path(d) / "dlc.bin")
            self.assertEqual(size, len(self.DATA))
            self.assertEqual((Path(d) / "dlc.bin").read_bytes(), self.DATA)
            import hashlib
            self.assertEqual(sha, hashlib.sha256(self.DATA).hexdigest())

    def test_changed_data_block_fails(self):
        fs, section = fake_ivfc(self.DATA)
        bad = bytearray(section)
        bad[len(section) - (-len(self.DATA) % 4096) - 100] ^= 1   # um byte do nível de dados (antes do enchimento)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                extract_dlc.copy_verified(FakeSection(fs, bytes(bad)), Path(d) / "dlc.bin")
            self.assertFalse((Path(d) / "dlc.bin").exists())

    def test_changed_hash_table_fails(self):
        fs, section = fake_ivfc(self.DATA)
        bad = bytearray(section)
        bad[3] ^= 1   # o nível 0
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            extract_dlc.copy_verified(FakeSection(fs, bytes(bad)), Path(d) / "dlc.bin")


if __name__ == "__main__":
    unittest.main()

"""Leitura de containers do Switch direto do arquivo (NSP/XCI → NCA → seções), sem extrair o NCA inteiro.

Adaptado de MacNativeGames `games/totk/scripts/extract_exefs.py` @ b75be8cfa704df3701e86130c8ced268e79d6b11
(MIT, Copyright (c) 2026 MacNativeGames contributors), na forma vendorizada pelo astral-chain-pc-recomp
(`tools/vendor/macnativegames/extract_exefs.py`). Mudanças: biblioteca em vez de script, sem IDs de jogo
embutidos, inventário de NCAs e de tickets reutilizável, leitura de seção genérica para RomFS/BKTR depois.

Formatos: switchbrew.org/wiki/NCA, /PFS0, /Ticket. As chaves ficam só em memória e nunca são impressas.
"""
from __future__ import annotations

import hashlib
import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

CONTENT_TYPES = {0: "Program", 1: "Meta", 2: "Control", 3: "Manual", 4: "Data", 5: "PublicData"}
MAX_READ = 512 * 1024 * 1024


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def decrypt(key: bytes, mode, data: bytes) -> bytes:
    ctx = Cipher(algorithms.AES(key), mode).decryptor()
    return ctx.update(data) + ctx.finalize()


def read_at(f: BinaryIO, offset: int, length: int) -> bytes:
    require(0 <= offset and 0 <= length <= MAX_READ, "Leitura inválida ou grande demais")
    f.seek(offset)
    data = f.read(length)
    require(len(data) == length, "Arquivo truncado")
    return data


def partition_entries(f: BinaryIO, offset: int, bound: int, magic: bytes = b"PFS0",
                      stride: int = 24) -> list[tuple[str, int, int]]:
    """Tabela PFS0/HFS0 limitada: (nome, offset absoluto, tamanho), sem ler os dados."""
    require(bound >= 16, "Cabeçalho de partição truncado")
    hdr = read_at(f, offset, 16)
    require(hdr[:4] == magic, f"Esperado {magic.decode()}")
    count, strings_size = struct.unpack_from("<II", hdr, 4)
    require(count <= 4096 and strings_size <= 1024 * 1024, "Tabela de partição inválida")
    size = 16 + count * stride + strings_size
    require(size <= bound, "Tabela de partição fora dos limites")
    raw = read_at(f, offset, size)
    strings = raw[16 + count * stride:]
    entries: list[tuple[str, int, int]] = []
    names: set[str] = set()
    for i in range(count):
        off, length, nameoff = struct.unpack_from("<QQI", raw, 16 + i * stride)
        require(nameoff < len(strings), "Offset de nome inválido")
        end = strings.find(b"\0", nameoff)
        require(end >= 0, "Nome sem terminador")
        name = strings[nameoff:end].decode("utf-8")
        require(name not in ("", ".", "..") and "/" not in name and "\\" not in name, "Nome inseguro")
        require(name not in names, "Nome duplicado")
        names.add(name)
        require(size + off + length <= bound, "Entrada fora dos limites")
        entries.append((name, offset + size + off, length))
    return entries


def container_entries(f: BinaryIO, size: int) -> tuple[str, list[tuple[str, int, int]]]:
    if read_at(f, 0, 4) == b"PFS0":
        return "nsp", partition_entries(f, 0, size)
    require(size >= 0x138 and read_at(f, 0x100, 4) == b"HEAD", "Esperado um XCI ou NSP (PFS0)")
    root = struct.unpack("<Q", read_at(f, 0x130, 8))[0]
    parts = partition_entries(f, root, size - root, b"HFS0", 64)
    secure = [e for e in parts if e[0] == "secure"]
    require(len(secure) == 1, "XCI sem partição secure")
    return "xci", partition_entries(f, secure[0][1], secure[0][2], b"HFS0", 64)


def load_keys(path: Path) -> dict[str, bytes]:
    keys: dict[str, bytes] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            name, value = line.split("=", 1)
            try:
                keys[name.strip().lower()] = bytes.fromhex(value.strip())
            except ValueError:
                raise ValueError(f"Chave mal formada na linha {number}") from None
    return keys


def common_tickets(f: BinaryIO, entries) -> dict[bytes, bytes]:
    """Title keys (ainda cifradas) dos .tik do container: rights ID → chave."""
    tickets: dict[bytes, bytes] = {}
    bodies = {0x10000: 0x240, 0x10001: 0x140, 0x10002: 0x80,
              0x10003: 0x240, 0x10004: 0x140, 0x10005: 0x80}
    for name, offset, size in entries:
        if not name.lower().endswith(".tik"):
            continue
        sig = struct.unpack("<I", read_at(f, offset, 4))[0]
        require(sig in bodies, "Tipo de assinatura de ticket não suportado")
        body = bodies[sig]
        require(size >= body + 0x180, "Ticket truncado")
        data = read_at(f, offset + body, 0x180)
        require(data[0x141] == 0, "Ticket personalizado não é suportado; é preciso um ticket comum")
        rights, key = data[0x160:0x170], data[0x40:0x50]
        require(rights not in tickets or tickets[rights] == key, "Tickets conflitantes")
        tickets[rights] = key
    return tickets


@dataclass
class Nca:
    name: str
    offset: int          # offset absoluto do NCA dentro do container
    size: int
    header: bytes = field(repr=False)

    @property
    def content_type(self) -> int:
        return self.header[0x205]

    @property
    def content_name(self) -> str:
        return CONTENT_TYPES.get(self.content_type, str(self.content_type))

    @property
    def title_id(self) -> str:
        return f"{struct.unpack_from('<Q', self.header, 0x210)[0]:016X}"

    @property
    def key_generation(self) -> int:
        return max(self.header[0x206], self.header[0x220])

    @property
    def sdk_version(self) -> str:
        v = struct.unpack_from("<I", self.header, 0x21C)[0]
        return f"{v >> 24}.{(v >> 16) & 0xff}.{(v >> 8) & 0xff}"

    @property
    def rights_id(self) -> bytes:
        return self.header[0x230:0x240]

    def fs_header(self, i: int) -> bytes:
        return self.header[0x400 + 512 * i:0x600 + 512 * i]

    def section_bounds(self, i: int) -> tuple[int, int]:
        start, end = struct.unpack_from("<II", self.header, 0x240 + 16 * i)
        return start * 512, end * 512

    def sections(self) -> list[int]:
        return [i for i in range(4) if self.section_bounds(i)[1] > 0]

    def section_kind(self, i: int) -> str:
        fs = self.fs_header(i)
        if fs[4] == 4:
            return "bktr"
        return {(1, 2): "pfs0", (0, 3): "romfs"}.get((fs[2], fs[3]), f"tipo {fs[2]}/{fs[3]}")


def read_nca_header(f: BinaryIO, offset: int, size: int, keys: dict[str, bytes]) -> bytes:
    require(size >= 0xC00, "Cabeçalho NCA truncado")
    require("header_key" in keys, "header_key ausente no prod.keys")
    raw = read_at(f, offset, 0xC00)
    hdr = b"".join(decrypt(keys["header_key"], modes.XTS(i.to_bytes(16, "big")), raw[i * 512:(i + 1) * 512])
                   for i in range(6))
    require(hdr[0x200:0x204] == b"NCA3", "Não é NCA3 (confira o prod.keys e o arquivo)")
    require(struct.unpack_from("<Q", hdr, 0x208)[0] == size, "Tamanho do NCA não bate com o container")
    for i in range(4):
        start, end = struct.unpack_from("<II", hdr, 0x240 + i * 16)
        require((start == end == 0) or 0xC00 <= start * 512 < end * 512 <= size, "Seção NCA fora dos limites")
    for i in range(4):
        start, end = struct.unpack_from("<II", hdr, 0x240 + i * 16)
        if end:
            fs = hdr[0x400 + 512 * i:0x600 + 512 * i]
            require(hashlib.sha256(fs).digest() == hdr[0x280 + 32 * i:0x2A0 + 32 * i], "Hash do FS header não bate")
    return hdr


def nca_inventory(f: BinaryIO, entries, keys) -> list[Nca]:
    return [Nca(name, off, size, read_nca_header(f, off, size, keys))
            for name, off, size in entries if name.lower().endswith(".nca")]


def nca_ctr_key(nca: Nca, keys: dict[str, bytes], tickets: dict[bytes, bytes]) -> bytes:
    generation = max(nca.key_generation - 1, 0)
    if nca.rights_id != bytes(16):
        require(nca.rights_id in tickets, "NCA com rights ID sem ticket comum no container")
        name = f"titlekek_{generation:02x}"
        require(name in keys, f"{name} ausente no prod.keys")
        return decrypt(keys[name], modes.ECB(), tickets[nca.rights_id])
    area = ("application", "ocean", "system")[nca.header[0x207]]
    name = f"key_area_key_{area}_{generation:02x}"
    require(name in keys, f"{name} ausente no prod.keys")
    return decrypt(keys[name], modes.ECB(), nca.header[0x300:0x340])[32:48]


class SectionReader:
    """Leitura decifrada (AES-CTR) de uma seção de NCA, por offset relativo à seção."""

    def __init__(self, f: BinaryIO, nca: Nca, index: int, key: bytes):
        self.f, self.nca, self.key = f, nca, key
        self.fs = nca.fs_header(index)
        self.start, end = nca.section_bounds(index)
        self.size = end - self.start
        require(self.fs[4] in (3, 4), "Só AES-CTR/CTR-EX é suportado")

    def read(self, relative: int, size: int) -> bytes:
        require(relative >= 0 and relative + size <= self.size, "Leitura fora da seção")
        absolute = self.start + relative
        aligned = absolute & ~15
        iv = self.fs[0x140:0x148][::-1] + (aligned // 16).to_bytes(8, "big")
        data = read_at(self.f, self.nca.offset + aligned, size + absolute - aligned)
        return decrypt(self.key, modes.CTR(iv), data)[absolute - aligned:]


def read_exefs(f: BinaryIO, nca: Nca, key: bytes) -> list[tuple[str, bytes]]:
    """ExeFS (PFS0 com tabela de hashes de 2 níveis) verificado bloco a bloco."""
    for i in nca.sections():
        if nca.section_kind(i) != "pfs0":
            continue
        sec = SectionReader(f, nca, i, key)
        fs = sec.fs
        blocksize, levels = struct.unpack_from("<II", fs, 0x28)
        hashoff, hashsize, pfsoff, pfssize = struct.unpack_from("<QQQQ", fs, 0x30)
        require(levels == 2 and blocksize > 0 and pfssize <= MAX_READ, "Layout de hash do ExeFS não suportado")
        hashes = sec.read(hashoff, hashsize)
        require(hashlib.sha256(hashes).digest() == fs[8:40], "Tabela de hash do ExeFS não bate")
        pfs = sec.read(pfsoff, pfssize)
        for index, pos in enumerate(range(0, pfssize, blocksize)):
            require(hashlib.sha256(pfs[pos:pos + blocksize]).digest() == hashes[index * 32:(index + 1) * 32],
                    f"Hash do bloco {index} do ExeFS não bate")
        files = [(name, pfs[off:off + size]) for name, off, size in
                 partition_entries(io.BytesIO(pfs), 0, len(pfs))]
        if any(name == "main.npdm" for name, _ in files):
            return files
    raise ValueError("NCA sem ExeFS")


def romfs_files(sec: SectionReader) -> list[tuple[str, int, int]]:
    """Lista do RomFS de uma seção IVFC: (caminho, offset do dado na seção, tamanho). Lê só os metadados."""
    fs = sec.fs
    require(fs[8:12] == b"IVFC", "Seção sem IVFC")
    level_off, level_size = struct.unpack_from("<QQ", fs, 0x18 + 0x18 * 5)
    hdr = sec.read(level_off, 0x50)
    (hsize, _dh_off, _dh_size, dm_off, dm_size, _fh_off, _fh_size, fm_off, fm_size,
     data_off) = struct.unpack_from("<10Q", hdr)
    require(hsize == 0x50, "Cabeçalho de RomFS inesperado")
    dmeta = sec.read(level_off + dm_off, dm_size)
    fmeta = sec.read(level_off + fm_off, fm_size)
    out: list[tuple[str, int, int]] = []
    empty = 0xFFFFFFFF

    def walk_files(first: int, prefix: str) -> None:
        cur = first
        while cur != empty:
            _parent, sibling, off, size, _hash, nlen = struct.unpack_from("<IIQQII", fmeta, cur)
            name = fmeta[cur + 0x20:cur + 0x20 + nlen].decode("utf-8")
            out.append((prefix + name, level_off + data_off + off, size))
            cur = sibling

    def walk_dir(at: int, prefix: str) -> None:
        _parent, _sibling, child, files, _hash, _nlen = struct.unpack_from("<IIIIII", dmeta, at)
        walk_files(files, prefix)
        cur = child
        while cur != empty:
            _p, sibling, _c, _f, _h, nlen = struct.unpack_from("<IIIIII", dmeta, cur)
            name = dmeta[cur + 0x18:cur + 0x18 + nlen].decode("utf-8")
            walk_dir(cur, prefix + name + "/")
            cur = sibling

    walk_dir(0, "")
    require(level_size >= 0x50, "Nível de RomFS vazio")
    return out


def romfs_image_files(f: BinaryIO, base: int = 0) -> list[tuple[str, int, int]]:
    """Lista de uma imagem RomFS simples (ex.: build/v130/romfs.bin): (caminho, offset absoluto, tamanho)."""
    hdr = read_at(f, base, 0x50)
    (hsize, _dh_off, _dh_size, dm_off, dm_size, _fh_off, _fh_size, fm_off, fm_size,
     data_off) = struct.unpack_from("<10Q", hdr)
    require(hsize == 0x50, "Não é uma imagem RomFS (cabeçalho inesperado)")
    dmeta = read_at(f, base + dm_off, dm_size)
    fmeta = read_at(f, base + fm_off, fm_size)
    out: list[tuple[str, int, int]] = []
    empty = 0xFFFFFFFF

    def walk_dir(at: int, prefix: str) -> None:
        _parent, _sibling, child, files, _hash, _nlen = struct.unpack_from("<IIIIII", dmeta, at)
        cur = files
        while cur != empty:
            _p, sibling, off, size, _h, nlen = struct.unpack_from("<IIQQII", fmeta, cur)
            out.append((prefix + fmeta[cur + 0x20:cur + 0x20 + nlen].decode("utf-8"), base + data_off + off, size))
            cur = sibling
        cur = child
        while cur != empty:
            _p, sibling, _c, _f, _h, nlen = struct.unpack_from("<IIIIII", dmeta, cur)
            walk_dir(cur, prefix + dmeta[cur + 0x18:cur + 0x18 + nlen].decode("utf-8") + "/")
            cur = sibling

    walk_dir(0, "")
    return out


class SectionFile:
    """Arquivo somente-leitura sobre o nível RomFS (IVFC nível 5) de uma seção de NCA: permite usar
    romfs_image_files() e as ferramentas de censo direto no NSP, sem extrair nada."""

    def __init__(self, sec: SectionReader):
        require(sec.fs[8:12] == b"IVFC", "Seção sem IVFC")
        self.sec = sec
        self.base, self.size = struct.unpack_from("<QQ", sec.fs, 0x18 + 0x18 * 5)
        self.pos = 0

    def seek(self, pos: int, whence: int = 0) -> int:
        self.pos = pos if whence == 0 else self.pos + pos if whence == 1 else self.size + pos
        return self.pos

    def tell(self) -> int:
        return self.pos

    def read(self, n: int = -1) -> bytes:
        n = self.size - self.pos if n < 0 else min(n, self.size - self.pos)
        if n <= 0:
            return b""
        data = self.sec.read(self.base + self.pos, n)
        self.pos += n
        return data


def dlc_romfs(game_dir: Path, keys: dict[str, bytes], prefix: str = "01002B00111A3"):
    """(title id, SectionFile) do RomFS de cada NSP de DLC em game_dir. O NSP fica aberto enquanto o gerador vive."""
    for path in sorted(p for p in Path(game_dir).rglob("*.nsp")):
        f = path.open("rb")
        _, entries = container_entries(f, path.stat().st_size)
        tickets = common_tickets(f, entries)
        for nca in nca_inventory(f, entries, keys):
            if nca.content_type != 5 or not nca.title_id.startswith(prefix):
                continue
            key = nca_ctr_key(nca, keys, tickets)
            for i in nca.sections():
                if nca.section_kind(i) == "romfs":
                    yield nca.title_id, SectionFile(SectionReader(f, nca, i, key))

#!/usr/bin/env python3
"""Censo de imports e exports dos módulos NSO (Fase 0).

Descomprime os segmentos (LZ4), acha o MOD0 e a tabela .dynamic, e lista os símbolos indefinidos (imports) de
cada módulo agrupados por namespace (`nn::fs`, `nn::os`, `nv`, libc...). Responde a duas perguntas do plano:

- quais funções do SDK o jogo chama (a fronteira `nn::*` que o host vai implementar);
- se há `__cxa_throw`, `_Unwind_*` ou `longjmp` (decide a otimização de registradores callee-saved do lifter).

Só nomes de símbolos e contagens; nenhum código do jogo é gravado fora de build/.

Uso:
    python3 tools/census_imports.py --exefs build/v130/exefs [--out build/v130/imports.json]
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path

import lz4.block

MODULES = ("main", "subsdk0", "sdk")
DT_NULL, DT_HASH, DT_STRTAB, DT_SYMTAB, DT_STRSZ = 0, 4, 5, 6, 10
DT_GNU_HASH = 0x6FFFFEF5
RISKY = ("__cxa_throw", "__cxa_begin_catch", "_Unwind_Resume", "_Unwind_RaiseException", "longjmp",
         "_longjmp", "siglongjmp", "setjmp", "_setjmp")


def load_nso(path: Path) -> bytes:
    raw = path.read_bytes()
    assert raw[:4] == b"NSO0", f"{path.name} não é NSO"
    flags = struct.unpack_from("<I", raw, 0x0C)[0]
    segs = []
    for i, off in enumerate((0x10, 0x20, 0x30)):
        file_off, mem_off, size = struct.unpack_from("<III", raw, off)
        fsize = struct.unpack_from("<I", raw, 0x60 + 4 * i)[0]
        blob = raw[file_off:file_off + fsize]
        if flags & (1 << i):
            blob = lz4.block.decompress(blob, uncompressed_size=size)
        segs.append((mem_off, blob))
    bss = struct.unpack_from("<I", raw, 0x3C)[0]
    end = max(m + len(b) for m, b in segs) + bss
    image = bytearray(end)
    for mem_off, blob in segs:
        image[mem_off:mem_off + len(blob)] = blob
    return bytes(image)


def dynamic(image: bytes) -> dict[int, int]:
    mod0 = struct.unpack_from("<I", image, 4)[0]
    assert image[mod0:mod0 + 4] == b"MOD0", "MOD0 não encontrado"
    dyn = mod0 + struct.unpack_from("<i", image, mod0 + 4)[0]
    tags: dict[int, int] = {}
    pos = dyn
    while True:
        tag, val = struct.unpack_from("<qQ", image, pos)
        if tag == DT_NULL:
            break
        tags.setdefault(tag, val)
        pos += 16
    return tags


def symbol_count(image: bytes, tags: dict[int, int]) -> int:
    if DT_HASH in tags:
        return struct.unpack_from("<II", image, tags[DT_HASH])[1]
    if DT_GNU_HASH in tags:
        off = tags[DT_GNU_HASH]
        nbuckets, symoffset, bloom_size, _shift = struct.unpack_from("<IIII", image, off)
        buckets = off + 16 + 8 * bloom_size
        chains = buckets + 4 * nbuckets
        last = max(struct.unpack_from(f"<{nbuckets}I", image, buckets))
        if last < symoffset:
            return symoffset
        while not (struct.unpack_from("<I", image, chains + 4 * (last - symoffset))[0] & 1):
            last += 1
        return last + 1
    return (tags[DT_STRTAB] - tags[DT_SYMTAB]) // 24


def symbols(image: bytes) -> tuple[list[str], list[str]]:
    tags = dynamic(image)
    strtab, symtab = tags[DT_STRTAB], tags[DT_SYMTAB]
    imports, exports = [], []
    for i in range(1, symbol_count(image, tags)):
        name_off, info, _other, shndx, _value, _size = struct.unpack_from("<IBBHQQ", image, symtab + 24 * i)
        end = image.index(b"\0", strtab + name_off)
        name = image[strtab + name_off:end].decode("ascii", "replace")
        if not name:
            continue
        (imports if shndx == 0 else exports).append(name)
    return imports, exports


def namespace(sym: str) -> str:
    """`_ZN2nn2fs8MountRomE...` → `nn::fs`; nomes C ficam em 'C'."""
    m = re.match(r"_ZN(?:K|VK|V)?(\d+)", sym)
    if not m:
        return "C" if not sym.startswith("_Z") else "C++ (outros)"
    parts, pos = [], m.start(1)
    while len(parts) < 2 and pos < len(sym) and sym[pos].isdigit():
        n = re.match(r"\d+", sym[pos:]).group(0)
        pos += len(n)
        parts.append(sym[pos:pos + int(n)])
        pos += int(n)
    if parts and parts[0] in ("nn", "nv", "nvn") and len(parts) == 2:
        return "::".join(parts)
    return parts[0] if parts else "C++ (outros)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exefs", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    report = {}
    exports_all: set[str] = set()
    per_mod = {}
    for m in MODULES:
        imp, exp = symbols(load_nso(args.exefs / m))
        per_mod[m] = (imp, exp)
        exports_all.update(exp)
    for m in MODULES:
        imp, exp = per_mod[m]
        groups = Counter(namespace(s) for s in imp)
        unresolved = sorted(s for s in imp if s not in exports_all)
        risky = sorted(s for s in imp if s in RISKY)
        report[m] = {"imports": len(imp), "exports": len(exp), "by_namespace": dict(groups.most_common()),
                     "unresolved_by_modules": unresolved, "exceptions_or_longjmp": risky,
                     "import_names": sorted(imp)}
        print(f"{m}: {len(imp)} imports, {len(exp)} exports; sem dono entre os módulos: {len(unresolved)};"
              f" exceções/longjmp: {', '.join(risky) or 'nenhum'}")
        for ns, n in groups.most_common(18):
            print(f"    {ns:24s} {n}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        print(f"relatório: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

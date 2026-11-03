#!/usr/bin/env python3
"""Censo dos arquivos RDB do Koei Tecmo (Fase 0): o que há dentro do RomFS 1.3.0 e dos DLCs, por tipo.

Os dados do jogo ficam em `asset/*.rdb.bin*` e `asset/data/*.file`: uma sequência de entradas IDRK
('IDRK0000', u64 tamanho da entrada, u64 tamanho guardado, u64 tamanho real, u32 0, u32 KTID do arquivo,
u32 KTID do tipo, u32 flags; os dados guardados ficam no fim da entrada; flag 0x100000 = zlib em blocos
de até 16 KB). Formato descrito pelo nxnative (`dm/gfx/tools/shader_split.py`, `idrk_entries`/`idrk_data`).

Para cada tipo conta entradas, bytes guardados e bytes reais, e anota a "magic" dos dados de algumas
amostras (ex.: `_S2G` = shaders G2S, `GT1G` = texturas G1T). Para as texturas G1T lê o cabeçalho de cada
uma e conta os códigos de formato — é o que decide o custo de ASTC no Steam Deck.

Só lê cabeçalhos e o primeiro bloco das entradas; retoma de onde parou (--budget segundos por execução).

Uso:
    python3 tools/census_rdb.py --romfs build/v130/romfs.bin [--budget 150]
    python3 tools/census_rdb.py --report      # junta os resultados em build/v130/rdb-census.json
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
import zlib
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IDRK = b"IDRK0000"
SAMPLES_PER_TYPE = 3
# Códigos de formato do G1T. 0x59–0x5F e 0x06/0x08: Amicitia Wiki (G1T), conferidos no nosso dump pela razão
# tamanho/pixels (BC1 e BC4 dão 4 bpp, BC5/BC6H/BC7 dão 8 bpp, com mipmaps). 0x01–0x04 só aparecem em texturas
# de 1×1 (placeholders não comprimidos).
G1T_FORMATS = {0x01: "BGRA8 (1×1)", 0x02: "32 bpp (1×1)", 0x03: "não comprimido (1×1?)", 0x04: "não comprimido (1×1)",
               0x06: "BC1 (antigo)", 0x08: "BC3 (antigo)", 0x59: "BC1", 0x5A: "BC2", 0x5B: "BC3", 0x5C: "BC4",
               0x5D: "BC5", 0x5E: "BC6H", 0x5F: "BC7"}


def first_bytes(f, start: int, end: int, flags: int, n: int) -> bytes:
    """Primeiros n bytes reais de uma entrada (descomprime só o primeiro bloco)."""
    if not flags & 0x100000:
        return nx.read_at(f, start, min(n, end - start))
    head = nx.read_at(f, start, min(end - start, 4 + 0x4400))
    cs = struct.unpack_from("<I", head, 0)[0]
    if not cs:
        return b""
    if cs > len(head) - 4:
        head = nx.read_at(f, start, 4 + cs)
    return zlib.decompressobj().decompress(head[4:4 + cs], n)


def g1t_formats(data: bytes) -> list[int]:
    """Códigos de formato das texturas de um G1T ('GT1G'): u32 magic, u32 versão, u32 tamanho, u32 offset da
    tabela, u32 número de texturas; a tabela tem um u32 por textura (relativo à tabela); no cabeçalho de cada
    textura o 2º byte é o formato."""
    if data[:4] != b"GT1G" or len(data) < 0x14:
        return []
    table, count = struct.unpack_from("<II", data, 0x0C)
    out = []
    for i in range(min(count, 4096)):
        if table + 4 * i + 4 > len(data):
            break
        off = table + struct.unpack_from("<I", data, table + 4 * i)[0]
        if off + 2 <= len(data):
            out.append(data[off + 1])
    return out


def scan_file(f, path: str, base: int, size: int, deadline: float, state: dict) -> bool:
    """Percorre as entradas de um arquivo RDB a partir de state['pos']; devolve True quando termina."""
    pos = state.get("pos", 0)
    types = state.setdefault("types", {})
    while pos + 0x30 <= size:
        if time.time() > deadline:
            state["pos"] = pos
            return False
        hdr = nx.read_at(f, base + pos, 0x30)
        if hdr[:8] != IDRK:
            # entradas podem vir depois de preenchimento até 64 KB: procura a próxima
            window = nx.read_at(f, base + pos, min(0x10000, size - pos))
            nxt = window.find(IDRK, 1)
            if nxt < 0:
                pos = (pos // 0x10000 + 1) * 0x10000
                continue
            pos += nxt
            continue
        esz, csz, length = struct.unpack_from("<QQQ", hdr, 8)
        type_ktid, flags = struct.unpack_from("<II", hdr, 0x28)
        if esz < 0x30 or csz > esz:
            state.setdefault("bad", 0)
            state["bad"] += 1
            pos += 8
            continue
        key = f"{type_ktid:08x}"
        t = types.setdefault(key, {"count": 0, "stored": 0, "length": 0, "magic": {}, "g1t_formats": {}})
        t["count"] += 1
        t["stored"] += csz
        t["length"] += length
        start, end = base + pos + esz - csz, base + pos + esz
        sample = sum(t["magic"].values()) < SAMPLES_PER_TYPE
        is_g1t = t["magic"].get("GT1G", 0) > 0
        if sample or is_g1t:
            data = first_bytes(f, start, end, flags, 0x4000 if (is_g1t or sample) else 8)
            magic = data[:4].decode("ascii", "replace") if data[:4].isascii() else data[:4].hex()
            if sample:
                t["magic"][magic] = t["magic"].get(magic, 0) + 1
            if magic == "GT1G":
                for code in g1t_formats(data):
                    k = f"0x{code:02x}"
                    t["g1t_formats"][k] = t["g1t_formats"].get(k, 0) + 1
        pos += esz
    state["pos"] = size
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--romfs", type=Path, default=ROOT / "build" / "v130" / "romfs.bin")
    ap.add_argument("--state", type=Path, default=ROOT / "build" / "v130" / "rdb-census-state.json")
    ap.add_argument("--budget", type=float, default=150.0)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    state = json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else {"files": {}}

    if not args.report:
        deadline = time.time() + args.budget
        with args.romfs.open("rb") as f:
            files = [(p, o, s) for p, o, s in nx.romfs_image_files(f)
                     if ".rdb.bin" in p.rsplit("/", 1)[-1] or p.endswith(".file")]
            pending = [x for x in files if not state["files"].get(x[0], {}).get("done")]
            for path, off, size in sorted(pending, key=lambda x: x[2]):
                st = state["files"].setdefault(path, {})
                st["done"] = scan_file(f, path, off, size, deadline, st)
                if not st["done"]:
                    break
        args.state.write_text(json.dumps(state) + "\n", encoding="utf-8")
        done = sum(1 for v in state["files"].values() if v.get("done"))
        print(f"arquivos RDB processados: {done}/{len(files)}" + ("" if done == len(files) else " (rode de novo para continuar)"))
        if done < len(files):
            return 2

    total: dict = defaultdict(lambda: {"count": 0, "stored": 0, "length": 0, "magic": Counter(), "g1t_formats": Counter()})
    for st in state["files"].values():
        for k, t in st.get("types", {}).items():
            a = total[k]
            a["count"] += t["count"]; a["stored"] += t["stored"]; a["length"] += t["length"]
            a["magic"].update(t["magic"]); a["g1t_formats"].update(t["g1t_formats"])
    rows = sorted(total.items(), key=lambda kv: kv[1]["length"], reverse=True)
    print(f"{'tipo KTID':10s} {'magic':8s} {'entradas':>9s} {'guardado':>10s} {'real':>10s}")
    for k, t in rows[:30]:
        magic = ",".join(m for m, _ in t["magic"].most_common(2))
        print(f"{k:10s} {magic:8s} {t['count']:9d} {t['stored'] / 2**20:8.0f}Mi {t['length'] / 2**20:8.0f}Mi")
    g1t = Counter()
    for _k, t in rows:
        g1t.update(t["g1t_formats"])
    if g1t:
        print("formatos de textura G1T:")
        for code, n in g1t.most_common():
            print(f"    {code}  {G1T_FORMATS.get(int(code, 16), '?'):24s} {n}")
    out = args.state.with_name("rdb-census.json")
    out.write_text(json.dumps({k: {**t, "magic": dict(t["magic"]), "g1t_formats": dict(t["g1t_formats"])}
                               for k, t in rows}, indent=1) + "\n", encoding="utf-8")
    print(f"relatório: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

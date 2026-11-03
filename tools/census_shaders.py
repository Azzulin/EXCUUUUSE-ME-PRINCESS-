#!/usr/bin/env python3
"""Censo dos shaders (Fase 0): quantos são, de que estágio, quantos únicos, quanto código.

Fontes, todas estáticas (não precisa rodar o jogo nem emulador):
- containers G2S (`_S2G3000`, tipo KTID 0x7bcd279f) e `_DOK0000` (0x20a6a0bb) dentro das entradas IDRK dos RDB do
  RomFS 1.3.0 mesclado;
- saídas GLSLC embutidas no `main` (ExeFS 1.3.0).

Cada shader é uma saída do compilador GLSLC da Nintendo: uma seção de controle (0x850 ou 0x880 bytes) e o código
Maxwell. A chave de cada shader é a mesma que o runtime vai usar para achar a tradução: os 16 primeiros dígitos
hexadecimais do SHA-256 de (seção de controle até o próprio tamanho + código).

Leitura de GLSLC portada de nxnative `dm/gfx/tools/shader_split.py` @ 3ace3df33b81681cdc9d17bfa48eadaccd446b5c
(funções sph_stage, ctl_len, skey, check, glslc_stage, glslc_layout, glslc_section, glslc_shaders, idrk_data;
MIT, Copyright (c) 2026 seedds). Sem o caminho NVN2 (Switch 2) e sem o perfil de jogo (o AoC não pula bytes na chave).

Retoma de onde parou (--budget segundos por execução). Saídas em build/v130/ (fora do git):
shader-census-state.json (progresso) e, no fim, shader-inventory.tsv (chave, estágio, ocorrências, bytes de código)
e shader-census.json (resumo).

Uso:
    python3 tools/census_shaders.py [--budget 150]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import time
import zlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IDRK = b"IDRK0000"
SHADER_TYPES = {0x7BCD279F: "G2S", 0x20A6A0BB: "_DOK"}
CTL_MAGIC, GFX_MAGIC, CS_MAGIC = bytes.fromhex("34127698"), bytes.fromhex("78563412"), bytes.fromhex("79563412")
GLSLC_MAGIC = b"\x91\x68\x86\x19"
SPH_STAGE = {1: "vs", 2: "hs", 3: "ds", 4: "gs", 5: "ps"}
STAGE_NAME = {"vs": "vertex", "hs": "hull", "ds": "domain", "gs": "geometry", "ps": "pixel", "cs": "compute"}


# ---- GLSLC (portado do nxnative) -----------------------------------------------------------------------------------

def sph_stage(code: bytes):
    if len(code) < 0x34:
        return None
    w = struct.unpack_from("<I", code, 0x30)[0]
    return "vs" if (w >> 10) & 0xF == 0 and w & 0x1F == 1 else SPH_STAGE.get((w >> 10) & 0xF)


def ctl_len(ctl: bytes) -> int:
    n = struct.unpack_from("<I", ctl, 0x20)[0]
    return n if 0x760 <= n < 0x880 else 0x880


def skey(ctl: bytes, code: bytes) -> str:
    return hashlib.sha256(ctl[:ctl_len(ctl)] + code).hexdigest()[:16]


def check(st: str, ctl: bytes, code: bytes):
    if ctl[:4] != CTL_MAGIC or len(ctl) < 0x24 or len(ctl) < ctl_len(ctl):
        return "seção de controle inválida"
    if (st == "cs" and code[:4] in (CS_MAGIC, GFX_MAGIC) and code[:4] != CS_MAGIC) or (st != "cs" and code[:4] != GFX_MAGIC):
        return "magic do código não bate com o estágio"
    if struct.unpack_from("<I", ctl, 0x704)[0] != len(code):
        return "controle +0x704 não bate com o tamanho do código"
    return None


def glslc_stage(ctl: bytes, code: bytes):
    headerless_cs = (code[:4] not in (CS_MAGIC, GFX_MAGIC) and len(ctl) >= 0x754
                     and all(struct.unpack_from("<3I", ctl, 0x748)))
    if code[:4] == CS_MAGIC or headerless_cs:
        return "cs"
    return sph_stage(code) if code[:4] == GFX_MAGIC and len(code) >= 0x34 else None


def glslc_layout(d: bytes, h: int):
    w = lambda o: struct.unpack_from("<I", d, h + o)[0]  # noqa: E731
    return (w(0x44), w(0x4C), 0x90, 0x90) if h + 0x50 <= len(d) else (0, 0, 0x90, 0x90)


def glslc_section(d: bytes, h: int, size: int):
    _, n, first, stride = glslc_layout(d, h)
    secs = []
    if not 0 < n <= 16 or h + first + stride * n > len(d):
        return None
    for i in range(n):
        s = h + first + stride * i
        ssz, soff, typ = struct.unpack_from("<3I", d, s)
        if typ:
            continue
        co, ko, kn, cn = struct.unpack_from("<4I", d, s + 0x30)
        if soff + ssz > size or co + cn > ssz or ko + kn > ssz:
            return None
        secs.append((d[h + soff + co:h + soff + co + cn], d[h + soff + ko:h + soff + ko + kn]))
    return secs


def glslc_program(d: bytes, h: int, size: int):
    secs = glslc_section(d, h, size) or []
    sts = [glslc_stage(c, k) for c, k in secs]
    if len(secs) < 2 or len(set(sts)) < len(sts) or any(not st or check(st, c, k) for st, (c, k) in zip(sts, secs)):
        return []
    return [(st, c, k) for st, (c, k) in zip(sts, secs)]


def glslc_shaders(d: bytes):
    """Todas as saídas GLSLC em d → [(estágio, controle, código)]."""
    out = []
    for m in re.finditer(re.escape(GLSLC_MAGIC), d):
        h = m.start()
        if h + 0x48 > len(d):
            continue
        size = glslc_layout(d, h)[0]
        c = d.find(CTL_MAGIC, h, h + size) if 0x760 < size <= len(d) - h else -1
        if c < 0:
            continue
        if d.find(CTL_MAGIC, c + 4, h + size) >= 0:
            out += glslc_program(d, h, size)
            continue
        nctl, ncode = ((struct.unpack_from("<I", d, c + 0x20)[0], struct.unpack_from("<I", d, c + 0x704)[0])
                       if c + 0x708 <= h + size else (0, 0))
        ctl, code = d[c:c + nctl], d[c + nctl:c + nctl + ncode]
        st = glslc_stage(ctl, code) if nctl >= 0x760 and not nctl & 3 and c + nctl + ncode <= h + size else None
        if not st or check(st, ctl, code):
            sec = glslc_section(d, h, size)
            if not sec or len(sec) != 1:
                continue
            (ctl, code), = sec
            st = glslc_stage(ctl, code)
            if not st or check(st, ctl, code):
                continue
        out.append((st, ctl, code))
    return out


def idrk_inflate(f, start: int, end: int, flags: int) -> bytes:
    """Dados reais de uma entrada IDRK do AoC: flag 0x100000 = zlib em blocos (u32 tamanho + stream, 0 termina)."""
    d = nx.read_at(f, start, end - start)
    if not flags & 0x100000:
        return d
    out, a = [], 0
    while a + 4 <= len(d):
        cs = struct.unpack_from("<I", d, a)[0]
        a += 4
        if not cs:
            break
        out.append(zlib.decompress(d[a:a + cs]))
        a += cs
    return b"".join(out)


# ---- censo -----------------------------------------------------------------------------------------------------------

def add(state: dict, source: str, shaders) -> None:
    keys = state["keys"]
    for st, ctl, code in shaders:
        k = skey(ctl, code)
        e = keys.get(k)
        if e is None:
            keys[k] = e = [st, 0, len(code), ctl_len(ctl), {}]
        e[1] += 1
        e[4][source] = e[4].get(source, 0) + 1


def scan_rdb(f, base: int, size: int, fst: dict, state: dict, deadline: float) -> bool:
    pos = fst.get("pos", 0)
    while pos + 0x30 <= size:
        if time.time() > deadline:
            fst["pos"] = pos
            return False
        hdr = nx.read_at(f, base + pos, 0x30)
        if hdr[:8] != IDRK:
            window = nx.read_at(f, base + pos, min(0x10000, size - pos))
            nxt = window.find(IDRK, 1)
            pos = pos + nxt if nxt > 0 else (pos // 0x10000 + 1) * 0x10000
            continue
        esz, csz, _length = struct.unpack_from("<QQQ", hdr, 8)
        typ, flags = struct.unpack_from("<II", hdr, 0x28)
        if esz < 0x30 or csz > esz:
            pos += 8
            continue
        kind = SHADER_TYPES.get(typ)
        if kind:
            data = idrk_inflate(f, base + pos + esz - csz, base + pos + esz, flags)
            found = glslc_shaders(data)
            state["containers"][kind] = state["containers"].get(kind, 0) + 1
            if found:
                state["containers_with_shaders"][kind] = state["containers_with_shaders"].get(kind, 0) + 1
            add(state, kind, found)
        pos += esz
    fst["pos"] = size
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", type=Path, default=ROOT / "build" / "v130")
    ap.add_argument("--budget", type=float, default=150.0)
    args = ap.parse_args(argv)
    state_path = args.work / "shader-census-state.json"
    state = (json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else
             {"files": {}, "keys": {}, "containers": {}, "containers_with_shaders": {}, "main_done": False})
    deadline = time.time() + args.budget

    if not state["main_done"]:
        from census_imports import load_nso
        add(state, "main", glslc_shaders(load_nso(args.work / "exefs" / "main")))
        state["main_done"] = True

    with (args.work / "romfs.bin").open("rb") as f:
        files = [(p, o, s) for p, o, s in nx.romfs_image_files(f)
                 if ".rdb.bin" in p.rsplit("/", 1)[-1] or p.endswith(".file")]
        for path, off, size in sorted(files, key=lambda x: x[2]):
            fst = state["files"].setdefault(path, {})
            if fst.get("done"):
                continue
            fst["done"] = scan_rdb(f, off, size, fst, state, deadline)
            if not fst["done"]:
                break
    state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
    done = sum(1 for v in state["files"].values() if v.get("done"))
    if done < len(files):
        print(f"arquivos RDB: {done}/{len(files)}; shaders únicos até agora: {len(state['keys'])} (rode de novo)")
        return 2

    keys = state["keys"]
    by_stage = Counter()
    occ_stage = Counter()
    code_stage = Counter()
    ctl_sizes = Counter()
    by_source = Counter()
    for k, (st, n, ncode, nctl, sources) in keys.items():
        by_stage[st] += 1
        occ_stage[st] += n
        code_stage[st] += ncode
        ctl_sizes[f"0x{nctl:x}"] += 1
        for s in sources:
            by_source[s] += 1
    total_occ = sum(occ_stage.values())
    print(f"shaders: {total_occ} ocorrências, {len(keys)} únicos")
    for st in ("vs", "ps", "cs", "gs", "hs", "ds"):
        if by_stage[st]:
            print(f"    {STAGE_NAME[st]:9s} {by_stage[st]:7d} únicos  {occ_stage[st]:7d} ocorrências"
                  f"  código {code_stage[st] / 2**20:7.1f} MiB")
    print("containers lidos:", dict(state["containers"]), " com shaders:", dict(state["containers_with_shaders"]))
    print("únicos por origem:", dict(by_source), " tamanhos de controle:", dict(ctl_sizes))
    inv = args.work / "shader-inventory.tsv"
    inv.write_text("chave\testagio\tocorrencias\tbytes_codigo\torigens\n" + "".join(
        f"{k}\t{STAGE_NAME[st]}\t{n}\t{ncode}\t{','.join(sorted(src))}\n"
        for k, (st, n, ncode, _c, src) in sorted(keys.items())), encoding="utf-8")
    summary = {"unique": len(keys), "occurrences": total_occ, "by_stage_unique": dict(by_stage),
               "by_stage_occurrences": dict(occ_stage), "code_bytes": dict(code_stage),
               "control_sizes": dict(ctl_sizes), "unique_by_source": dict(by_source),
               "containers": state["containers"], "containers_with_shaders": state["containers_with_shaders"]}
    (args.work / "shader-census.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(f"inventário: {inv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

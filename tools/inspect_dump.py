#!/usr/bin/env python3
"""Fase 0: confere um dump extraído de Age of Calamity sem modificar nada.

Lê o ExeFS (cabeçalhos NSO e main.npdm) e, opcionalmente, o RomFS extraído, e responde:

- os build IDs de main/subsdk0/sdk batem com uma versão conhecida (tools/data/known-builds.json)?
- quanto cada módulo ocupa em memória (texto, rodata, data, bss) e no total — o perfil do nxnative diz 66,6 MB,
  o que obriga o host a reportar mem_used = 72 MB;
- o que o NPDM declara (prioridade/core/pilha da thread principal, system resource size);
- quantos arquivos e bytes o RomFS tem, por extensão (RDB, dados RDB, DLC), para o orçamento do cartão SD.

Só lê cabeçalhos e tamanhos: não descomprime código, não abre NCA/NSP e nunca toca nas chaves.
O relatório (opcional, --out) deve ir para build/, que o git ignora.

Uso:
    python3 tools/inspect_dump.py --exefs build/v130/exefs [--romfs build/v130/romfs] [--out build/v130/inspect.json]
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWN = ROOT / "tools" / "data" / "known-builds.json"

MODULES = ("main", "subsdk0", "sdk")
PAGE = 0x1000


def _align(v: int, a: int = PAGE) -> int:
    return (v + a - 1) & ~(a - 1)


def read_nso_header(path: Path) -> dict:
    """Cabeçalho NSO0 (0x100 bytes), layout em switchbrew.org/wiki/NSO."""
    with path.open("rb") as f:
        hdr = f.read(0x100)
    if len(hdr) < 0x100 or hdr[:4] != b"NSO0":
        raise ValueError(f"{path.name}: não é um NSO (magic {hdr[:4]!r})")
    flags = struct.unpack_from("<I", hdr, 0x0C)[0]

    def seg(off: int) -> dict:
        file_off, mem_off, size = struct.unpack_from("<III", hdr, off)
        return {"file_offset": file_off, "mem_offset": mem_off, "size": size}

    text, ro, data = seg(0x10), seg(0x20), seg(0x30)
    bss = struct.unpack_from("<I", hdr, 0x3C)[0]
    build_id = hdr[0x40:0x60]
    image = _align(data["mem_offset"] + data["size"] + bss)
    return {
        "flags": {
            "text_compressed": bool(flags & 1),
            "ro_compressed": bool(flags & 2),
            "data_compressed": bool(flags & 4),
        },
        "text": text,
        "rodata": ro,
        "data": data,
        "bss": bss,
        "image_size": image,
        "build_id": build_id.hex(),
        "build_id_prefix": build_id[:16].hex(),
    }


def read_npdm(path: Path) -> dict:
    """Cabeçalho META do main.npdm (switchbrew.org/wiki/NPDM)."""
    with path.open("rb") as f:
        meta = f.read(0x80)
    if len(meta) < 0x30 or meta[:4] != b"META":
        raise ValueError(f"{path.name}: não é um NPDM (magic {meta[:4]!r})")
    flags = meta[0x0C]
    name = meta[0x20:0x30].split(b"\0", 1)[0].decode("ascii", "replace")
    return {
        "name": name,
        "is_64bit": bool(flags & 1),
        "address_space_type": (flags >> 1) & 7,
        "main_thread_priority": meta[0x0E],
        "main_thread_core": meta[0x0F],
        "system_resource_size": struct.unpack_from("<I", meta, 0x14)[0],
        "version": struct.unpack_from("<I", meta, 0x18)[0],
        "main_thread_stack_size": struct.unpack_from("<I", meta, 0x1C)[0],
    }


def classify(rel: str) -> str:
    low = rel.lower()
    base = low.rsplit("/", 1)[-1]
    if ".rdb.bin3_" in base:
        return "rdb-dlc"
    if base.endswith(".rdb"):
        return "rdb-index"
    if ".rdb.bin" in base:
        return "rdb-data"
    if base.endswith(".file"):
        return "rdb-file"
    ext = base.rsplit(".", 1)[-1] if "." in base else "(sem extensão)"
    return ext


def scan_romfs(root: Path) -> dict:
    count: Counter[str] = Counter()
    size: Counter[str] = Counter()
    total_files = total_bytes = 0
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            p = Path(dirpath) / fn
            rel = p.relative_to(root).as_posix()
            n = p.stat().st_size
            k = classify(rel)
            count[k] += 1
            size[k] += n
            total_files += 1
            total_bytes += n
    kinds = {k: {"files": count[k], "bytes": size[k]} for k in sorted(size, key=size.get, reverse=True)}
    return {"files": total_files, "bytes": total_bytes, "by_kind": kinds,
            "has_marker": (root / "asset" / "MaterialEditor.rdb.bin").exists()}


def match_version(mods: dict, known: dict) -> str | None:
    for ver, info in known.get("builds", {}).items():
        want = info["modules"]
        if all(m in mods and mods[m]["build_id_prefix"] == want[m] for m in want):
            return ver
    return None


def human(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unit == "GiB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return str(n)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exefs", type=Path, required=True, help="pasta com main, subsdk0, sdk, main.npdm")
    ap.add_argument("--romfs", type=Path, help="pasta do RomFS extraído (opcional)")
    ap.add_argument("--known", type=Path, default=KNOWN)
    ap.add_argument("--out", type=Path, help="grava o relatório JSON (use build/...)")
    args = ap.parse_args(argv)

    known = json.loads(args.known.read_text(encoding="utf-8"))
    report: dict = {"modules": {}, "problems": []}

    for m in MODULES:
        p = args.exefs / m
        if not p.exists():
            report["problems"].append(f"módulo ausente: {m}")
            continue
        report["modules"][m] = read_nso_header(p)

    extra = sorted(x.name for x in args.exefs.iterdir()
                   if x.is_file() and x.name not in (*MODULES, "rtld", "main.npdm"))
    if extra:
        report["problems"].append(f"arquivos inesperados no ExeFS: {', '.join(extra)}")

    npdm = args.exefs / "main.npdm"
    if npdm.exists():
        report["npdm"] = read_npdm(npdm)
    else:
        report["problems"].append("main.npdm ausente")

    total = sum(v["image_size"] for v in report["modules"].values())
    report["modules_total_image"] = total
    report["version"] = match_version(report["modules"], known)
    if report["version"] is None:
        report["problems"].append("build IDs não batem com nenhuma versão conhecida (esperado 1.3.0)")

    if args.romfs:
        report["romfs"] = scan_romfs(args.romfs)
        if not report["romfs"]["has_marker"]:
            report["problems"].append("RomFS sem asset/MaterialEditor.rdb.bin (pasta errada?)")

    # Saída legível
    print(f"Versão identificada: {report['version'] or 'DESCONHECIDA'}")
    for m, h in report["modules"].items():
        print(f"  {m:8s} build {h['build_id_prefix']}  imagem {human(h['image_size'])}"
              f"  (text {human(h['text']['size'])}, ro {human(h['rodata']['size'])},"
              f" data {human(h['data']['size'])}, bss {human(h['bss'])})")
    print(f"  total dos módulos: {human(total)}  ({total / 1e6:.1f} MB)")
    if "npdm" in report:
        n = report["npdm"]
        print(f"  NPDM '{n['name']}': prioridade {n['main_thread_priority']}, core {n['main_thread_core']},"
              f" pilha 0x{n['main_thread_stack_size']:x}, system resource 0x{n['system_resource_size']:x}")
    if "romfs" in report:
        r = report["romfs"]
        print(f"  RomFS: {r['files']} arquivos, {human(r['bytes'])}")
        for k, v in list(r["by_kind"].items())[:12]:
            print(f"    {k:16s} {v['files']:7d} arquivos  {human(v['bytes'])}")
    for p in report["problems"]:
        print(f"PROBLEMA: {p}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"relatório: {args.out}")
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())

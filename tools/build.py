#!/usr/bin/env python3
"""Build do AoC Recomp no Linux (WSL2 ou Linux nativo): gera o C do jogo e compila com clang + ninja.

Passos (cada um pula o que já está feito):

1. `gen`   — recomp/gen.py: ExeFS 1.3.0 → C em <work>/generated/ (~600 MB, ~3 min).
2. `guest` — compila todo o C gerado em objetos e junta em <work>/lib/libaoc_guest.a. As ~35 funções gigantes do
             `main` (um arquivo de 1–7 MB de C cada) recebem flags que cortam os passes do LLVM que crescem de forma
             superlinear (medido: ~40 % menos tempo); são compiladas primeiro, para não ficarem para o fim.
3. `dist`  — (Fase 2 em diante, quando houver runtime) linka o executável e monta a pasta única para o Deck.

O diretório de trabalho deve ficar no disco do Linux (ex.: ~/aoc-build), não em /mnt/c ou /mnt/d: compilar sobre
o disco do Windows pelo WSL é muitas vezes mais lento. Só a pasta final (dist) vai para o disco D.

Uso (na raiz do repositório):
    python3 tools/build.py --work ~/aoc-build            # gen + guest, com todos os núcleos
    python3 tools/build.py --work ~/aoc-build --jobs 8   # limita os núcleos (cada gigante usa até ~2–4 GB de RAM)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Flags do código gerado, como no Astral Chain (tools/build_game.py GEN_FLAGS).
GEN_FLAGS = ["-O1", "-fno-strict-aliasing", "-Wno-return-type", "-Wno-unused-label", "-fvisibility=hidden",
             "-march=x86-64-v3"]
# Para arquivos de uma função só com mais de BIG_BYTES de C: sem machine sinking, sem coalescer de intervalos e sem
# rotação de laços. Em main_0053.c (1 MB, 1 função): 89 s → 51 s, sem erro.
BIG_BYTES = 900_000
BIG_EXTRA = ["-mllvm", "-disable-machine-sink", "-mllvm", "-join-liveintervals=false",
             "-mllvm", "-rotation-max-header-size=0"]
MODULES = ("main", "subsdk0", "sdk")


def need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        sys.exit(f"ERRO: '{tool}' não encontrado no PATH (rode tools/setup_wsl.sh)")
    return path


def step_gen(args) -> Path:
    out = args.work / "generated"
    if all((out / m / "manifest.json").exists() for m in MODULES) and not args.regen:
        print("gen: C já gerado (use --regen para refazer)")
        return out
    cmd = [sys.executable, str(ROOT / "recomp" / "gen.py"), "--exefs", str(args.exefs), "--out", str(out),
           "--modules", ",".join(MODULES)]
    if args.jobs:
        cmd += ["--jobs", str(args.jobs)]
    print("gen:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return out


def ninja_escape(p: Path | str) -> str:
    return str(p).replace("$", "$$").replace(" ", "$ ").replace(":", "$:")


def step_guest(args, gen: Path) -> Path:
    cc, ar = need("clang"), shutil.which("llvm-ar") or need("ar")
    ninja = need("ninja")
    obj_dir = args.work / "obj"
    lib = args.work / "lib" / "libaoc_guest.a"
    sources = []
    for m in MODULES:
        manifest = json.loads((gen / m / "manifest.json").read_text())
        info = {c["file"]: c for c in manifest["chunk_info"]}
        for name in manifest["chunks"] + [manifest["table"]]:
            c = info.get(name, {"functions": 0, "bytes": (gen / m / name).stat().st_size})
            big = c["functions"] == 1 and c["bytes"] > BIG_BYTES
            sources.append((gen / m / name, obj_dir / m / (Path(name).stem + ".o"), big, c["bytes"]))
    # Maiores primeiro: as gigantes começam logo e não seguram o fim do build.
    sources.sort(key=lambda s: -s[3])
    flags = " ".join(GEN_FLAGS + ["-I", ninja_escape(ROOT / "runtime"), "-I", ninja_escape(gen)])
    lines = [
        "ninja_required_version = 1.10",
        f"cc = {cc}",
        f"ar = {ar}",
        f"cflags = {flags}",
        f"bigflags = {' '.join(BIG_EXTRA)}",
        "rule cc",
        "  command = $cc $cflags $extra -c $in -o $out",
        "  description = cc $in",
        "rule ar",
        "  command = rm -f $out && $ar rcs $out @$out.rsp",
        "  rspfile = $out.rsp",
        "  rspfile_content = $in",
        "  description = ar $out",
    ]
    for src, obj, big, _ in sources:
        lines.append(f"build {ninja_escape(obj)}: cc {ninja_escape(src)}")
        if big:
            lines.append("  extra = $bigflags")
    lines.append(f"build {ninja_escape(lib)}: ar " + " ".join(ninja_escape(o) for _, o, _, _ in sources))
    lines.append(f"default {ninja_escape(lib)}")
    for d in {o.parent for _, o, _, _ in sources} | {lib.parent}:
        d.mkdir(parents=True, exist_ok=True)
    build_file = args.work / "guest.ninja"
    build_file.write_text("\n".join(lines) + "\n")
    big = sum(1 for s in sources if s[2])
    print(f"guest: {len(sources)} arquivos de C ({big} com função gigante) → {lib}")
    if args.ninja_only:
        print(f"guest: só o arquivo ninja foi escrito ({build_file})")
        return lib
    t0 = time.time()
    cmd = [ninja, "-f", str(build_file)] + (["-j", str(args.jobs)] if args.jobs else [])
    subprocess.run(cmd, check=True, cwd=args.work)
    print(f"guest: pronto em {time.time() - t0:.0f} s ({lib.stat().st_size / 2**20:.0f} MiB)")
    return lib


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", type=Path, required=True, help="diretório de build no disco do Linux (ex.: ~/aoc-build)")
    ap.add_argument("--exefs", type=Path, default=ROOT / "build" / "v130" / "exefs")
    ap.add_argument("--jobs", type=int, default=0, help="núcleos (padrão: todos)")
    ap.add_argument("--regen", action="store_true", help="gerar o C de novo")
    ap.add_argument("--ninja-only", action="store_true", help="só escreve o guest.ninja, sem compilar")
    ap.add_argument("steps", nargs="*", help="gen, guest (padrão: os dois)")
    args = ap.parse_args(argv)
    args.steps = args.steps or ["gen", "guest"]
    if set(args.steps) - {"gen", "guest"}:
        ap.error("passos válidos: gen, guest")
    args.work = args.work.expanduser().resolve()
    args.work.mkdir(parents=True, exist_ok=True)
    if not (args.exefs / "main").exists():
        sys.exit(f"ERRO: ExeFS não encontrado em {args.exefs} (rode tools/extract.py exefs)")
    gen = step_gen(args) if "gen" in args.steps else args.work / "generated"
    if "guest" in args.steps:
        step_guest(args, gen)
    return 0


if __name__ == "__main__":
    sys.exit(main())

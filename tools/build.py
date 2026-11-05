#!/usr/bin/env python3
"""Build do AoC Recomp no Linux (WSL2 ou Linux nativo): gera o C do jogo e compila com clang + ninja.

Passos (cada um pula o que já está feito):

0. `extract` — se build/v130/exefs não existir (máquina nova), extrai o ExeFS do NSP do update em "Game Files/".
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
import shlex
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
# Tabela de patches do lifter (spin waits; depois os patches de jogo). Obrigatória: sem os spin waits o jogo pode travar.
PATCHES = ROOT / "recomp" / "patches-v130.txt"
# RAM que uma compilação de função gigante pode usar (medido: 1,8 GB na de 5 MB; a de 6,6 MB passa disso).
BIG_MEM = 4 << 30
GEN_WORKER_MEM = 1536 << 20   # recomp/gen.py WORKER_MEM


def mem_available() -> int:
    """MemAvailable do Linux em bytes (0 se não der para ler)."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except OSError:
        pass
    return 0


def need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        sys.exit(f"ERRO: '{tool}' não encontrado no PATH (rode tools/setup_wsl.sh)")
    return path


def step_extract(args) -> None:
    """Numa máquina nova o ExeFS ainda não existe: extrai do NSP do update em "Game Files/" (tools/extract.py)."""
    game, keys = ROOT / "Game Files", ROOT / "Game Files" / "prod.keys"
    if args.exefs != ROOT / "build" / "v130" / "exefs":
        sys.exit(f"ERRO: ExeFS não encontrado em {args.exefs}")
    if not keys.exists() or not any(game.rglob("*.nsp")):
        sys.exit("ERRO: o código do jogo ainda não foi extraído e não achei o dump.\n"
                 f"  Coloque os NSPs (base, update 1.3.0 e DLCs) e o prod.keys em: {game}\n"
                 "  (a pasta 'Game Files' fica na raiz do repositório e é ignorada pelo git)")
    print("extract: ExeFS ausente, extraindo do update 1.3.0 em 'Game Files/'")
    subprocess.run([sys.executable, str(ROOT / "tools" / "extract.py"), "inventory"], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools" / "extract.py"), "exefs"], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools" / "inspect_dump.py"), "--exefs", str(args.exefs)], check=True)


def step_gen(args) -> Path:
    out = args.work / "generated"
    manifests = [out / m / "manifest.json" for m in MODULES]
    # Mudanças no gerador ou na tabela de patches pedem C novo; o gerador só reescreve os arquivos que mudaram.
    inputs = [PATCHES] + list((ROOT / "recomp").glob("*.py"))
    fresh = all(p.exists() for p in manifests) and \
        min(p.stat().st_mtime for p in manifests) > max(p.stat().st_mtime for p in inputs)
    if fresh and not args.regen:
        print("gen: C já gerado e mais novo que recomp/ (use --regen para refazer)")
        return out
    cmd = [sys.executable, str(ROOT / "recomp" / "gen.py"), "--exefs", str(args.exefs), "--out", str(out),
           "--modules", ",".join(MODULES), "--patches", str(PATCHES)]
    # gen.py só mede a memória livre no Windows; aqui ela limita os workers (cada um carrega os módulos: ~1,5 GB).
    jobs = args.jobs or max(1, min(os.cpu_count() or 1, int(mem_available() * 0.8) // GEN_WORKER_MEM or 1))
    cmd += ["--jobs", str(jobs)]
    print("gen:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return out


def ninja_escape(p: Path | str) -> str:
    """Caminho numa linha `build` do ninja (saídas e entradas)."""
    return str(p).replace("$", "$$").replace(" ", "$ ").replace(":", "$:")


def shell_arg(p: Path | str) -> str:
    """Argumento dentro do valor de uma variável do ninja, que o ninja passa ao shell como está."""
    return shlex.quote(str(p)).replace("$", "$$")


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
    # Valores de variável do ninja vão para o shell como texto: os caminhos (o repositório costuma ter espaços, como
    # "Age of Calamity") precisam de aspas do shell, e só o "$" precisa de escape do ninja.
    flags = " ".join(GEN_FLAGS + ["-I", shell_arg(ROOT / "runtime"), "-I", shell_arg(gen)])
    # As gigantes rodam num pool limitado pela RAM livre, para várias delas juntas não esgotarem a memória do WSL.
    big_depth = args.big_jobs or max(1, int(mem_available() * 0.8) // BIG_MEM)
    lines = [
        "ninja_required_version = 1.10",
        f"cc = {cc}",
        f"ar = {ar}",
        f"cflags = {flags}",
        f"bigflags = {' '.join(BIG_EXTRA)}",
        "pool big",
        f"  depth = {big_depth}",
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
            lines.append("  pool = big")
    lines.append(f"build {ninja_escape(lib)}: ar " + " ".join(ninja_escape(o) for _, o, _, _ in sources))
    lines.append(f"default {ninja_escape(lib)}")
    for d in {o.parent for _, o, _, _ in sources} | {lib.parent}:
        d.mkdir(parents=True, exist_ok=True)
    build_file = args.work / "guest.ninja"
    build_file.write_text("\n".join(lines) + "\n")
    big = sum(1 for s in sources if s[2])
    print(f"guest: {len(sources)} arquivos de C ({big} com função gigante, até {big_depth} ao mesmo tempo) → {lib}")
    if args.ninja_only:
        print(f"guest: só o arquivo ninja foi escrito ({build_file})")
        return lib
    t0 = time.time()
    cmd = [ninja, "-f", str(build_file)] + (["-j", str(args.jobs)] if args.jobs else [])
    subprocess.run(cmd, check=True, cwd=args.work)
    print(f"guest: pronto em {time.time() - t0:.0f} s ({lib.stat().st_size / 2**20:.0f} MiB)")
    return lib


# ---- host: runtime + executável (adaptado de astral-chain-pc-recomp / totk-pc-recomp tools/build_game.py, MIT)
RUNTIME = ROOT / "runtime"
RT_FLAGS = ["-O2", "-g", "-Wall", "-fno-strict-aliasing", "-march=x86-64-v3"]
# -no-pie: as tabelas de funções dos módulos (centenas de milhares de ponteiros) não precisam de relocação na carga.
# $ORIGIN: uma libSDL3.so.0 ao lado do executável vem antes da do sistema (a pasta do Deck).
LINK_FLAGS = ["-fuse-ld=lld", "-no-pie", "-Wl,-z,noexecstack", "'-Wl,-rpath,$$ORIGIN/lib'"]
LINK_LIBS = ["-lvulkan", "-lSDL3", "-lopus", "-lvpx", "-lzstd", "-l:libstdc++.a", "-lm", "-lpthread", "-ldl"]
# vk_mem_alloc.h: o do sistema, senão a versão que o TotK Recomp fixa (VMA 3.4.0, MIT), baixada uma vez em
# toolchain/vma e conferida pelo hash.
VMA_FETCH = ("https://raw.githubusercontent.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator/v3.4.0/include/vk_mem_alloc.h",
             "8487b7995ad3b263eb73bc5b9a77d71aa69b6bef5d58a715c02d2663afd81f1a")
GAME_VERSION = 130   # host.h rt_game_version
ROMFS_IMAGE = ROOT / "build" / "v130" / "romfs.bin"


def vma_include() -> Path:
    import hashlib
    import urllib.request
    if Path("/usr/include/vk_mem_alloc.h").is_file():
        return Path("/usr/include")
    local = ROOT / "toolchain" / "vma"
    dst = local / "vk_mem_alloc.h"
    if not dst.is_file():
        url, sha = VMA_FETCH
        print(f"host: baixando VMA 3.4.0 para {local}")
        data = urllib.request.urlopen(url, timeout=60).read()
        if hashlib.sha256(data).hexdigest() != sha:
            sys.exit(f"ERRO: {url} não bate com o hash fixado")
        local.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    return local


def runtime_sources() -> list[Path]:
    """Todo runtime/*.c, *.cpp, platform/*.c, ui/*.cpp e o Dear ImGui, sem os arquivos de outro sistema (Win32)."""
    pats = ("*.c", "*.cpp", "platform/*.c", "ui/*.cpp", "third_party/imgui/*.cpp", "third_party/imgui/backends/*.cpp")

    def other_os(p: Path) -> bool:
        return p.stem.endswith("_win") or p.name == "win32.c"
    return sorted(p for pat in pats for p in RUNTIME.glob(pat) if not other_os(p))


def c_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def module_glue(gen: Path, exefs: Path) -> str:
    """C de modules.c: layout, tabelas de funções dos módulos (dispatch.h), SHA-256 esperados do ExeFS, versão do jogo
    e caminhos padrão (host.h). Os caminhos são os desta máquina; na pasta do Deck o runtime acha exefs/, romfs/ e
    profile/ ao lado do executável (main.c portable_paths)."""
    sys.path.insert(0, str(ROOT / "tools"))
    from check_content import GENERATED_MARKER
    layout = json.loads((gen / "layout.json").read_text())
    manifest = json.loads((exefs.parent / "exefs-manifest.json").read_text())
    hashes = {f["name"]: f["sha256"] for f in manifest["files"]}
    out = [f"// Cola dos módulos escrita por tools/build.py; não editar. {GENERATED_MARKER}",
           '#include "dispatch.h"', '#include "host.h"', '#include "layout.h"', ""]
    for m in layout:
        u = m["name"].upper()
        out.append(f'_Static_assert(MOD_{u}_BASE == {m["base"]}ull && MOD_{u}_SIZE == {m["size"]}ull, '
                   f'"layout.h e layout.json discordam em {m["name"]}");')
    out += ["", "const RtLayoutEntry rt_layout[] = {"]
    out += [f'    {{"{m["name"]}", MOD_{m["name"].upper()}_BASE, MOD_{m["name"].upper()}_SIZE}},' for m in layout]
    out += ["};", f"const int rt_layout_count = {len(layout)};", ""]
    for m in MODULES:
        out += [f"extern const uint64_t {m}_fn_addrs[];", f"extern const GuestFn {m}_fn_ptrs[];",
                f"extern const uint64_t {m}_fn_count;"]
    out += ["", "int rt_linked_modules(RtModule *out, int max) {", "    int n = 0;"]
    for m in MODULES:
        u = m.upper()
        out.append(f'    if (n < max) out[n++] = (RtModule){{"{m}", MOD_{u}_BASE, MOD_{u}_SIZE, {m}_fn_addrs, '
                   f"{m}_fn_ptrs, {m}_fn_count}};")
    out += ["    return n;", "}", "", "const RtFileHash rt_exefs_sha256[] = {"]
    out += [f"    {{{c_string(f)}, {c_string(h)}}}," for f, h in sorted(hashes.items())]
    out += ["};", f"const int rt_exefs_sha256_count = {len(hashes)};", ""]
    paths = {"exefs": exefs, "romfs": ROMFS_IMAGE.parent, "profile": ROMFS_IMAGE.parent / "profile"}
    for name, p in paths.items():
        out.append(f"const char rt_default_{name}[] = {c_string(str(p))};")
    version = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").is_file() else "unknown"
    out += [f"const int rt_game_version = {GAME_VERSION};", f"const char rt_port_version[] = {c_string(version)};", ""]
    return "\n".join(out)


def write_if_changed(path: Path, text: str) -> None:
    if path.exists() and path.read_text() == text:
        return
    path.write_text(text)


def step_host(args, gen: Path, lib: Path) -> Path:
    """Compila o runtime e linka <work>/host/aoc com a libaoc_guest.a."""
    cc, ninja = need("clang"), need("ninja")
    out = args.work / "host"
    out.mkdir(parents=True, exist_ok=True)
    write_if_changed(out / "modules.c", module_glue(gen, args.exefs))
    sys.path.insert(0, str(ROOT / "tools"))
    import romfs_index
    if ROMFS_IMAGE.is_file():
        n, size, dt = romfs_index.write(ROMFS_IMAGE, out)
        print(f"host: índice do RomFS com {n} arquivos ({dt:.1f} s)")
    else:
        romfs_index.write_placeholder(out)
        print(f"host: AVISO: {ROMFS_IMAGE} não existe; o executável compila mas não inicia o jogo")
    inc = ["-I", shell_arg(RUNTIME), "-I", shell_arg(gen), "-I", shell_arg(out), "-I", shell_arg(vma_include()),
           "-I", shell_arg(RUNTIME / "third_party" / "imgui")]
    lines = [
        "ninja_required_version = 1.10",
        f"builddir = {ninja_escape(out)}",
        f"cc = {cc}",
        f"rtflags = {' '.join(RT_FLAGS + inc)}",
        f"ldflags = {' '.join(LINK_FLAGS)}",
        f"libs = {' '.join(LINK_LIBS)}",
        "rule cc_rt",
        "  command = $cc $rtflags -MD -MF $out.d -c $in -o $out",
        "  deps = gcc",
        "  depfile = $out.d",
        "  description = cc $in",
        "rule link",
        "  command = $cc $ldflags @$out.rsp $libs -o $out",
        "  rspfile = $out.rsp",
        "  rspfile_content = $in_newline",
        "  description = link $out",
    ]
    objs = []
    for src in runtime_sources() + [out / "modules.c"]:
        rel = src.relative_to(RUNTIME) if src.is_relative_to(RUNTIME) else Path(src.name)
        o = out / "obj" / rel.with_suffix(".o")
        o.parent.mkdir(parents=True, exist_ok=True)
        lines.append(f"build {ninja_escape(o)}: cc_rt {ninja_escape(src)}")
        objs.append(o)
    exe = out / "aoc"
    lines.append(f"build {ninja_escape(exe)}: link " + " ".join(ninja_escape(o) for o in objs) + f" {ninja_escape(lib)}")
    lines.append(f"build runtime: phony " + " ".join(ninja_escape(o) for o in objs))
    lines.append(f"default {ninja_escape(exe)}")
    build_file = args.work / "host.ninja"
    build_file.write_text("\n".join(lines) + "\n")
    target = ["runtime"] if args.runtime_only else []
    t0 = time.time()
    cmd = [ninja, "-f", str(build_file)] + (["-j", str(args.jobs)] if args.jobs else []) + ["-k", "0"] + target
    subprocess.run(cmd, check=True, cwd=args.work)
    print(f"host: pronto em {time.time() - t0:.0f} s → {exe if not args.runtime_only else 'objetos do runtime'}")
    return exe


# ---- dist: a pasta única do Steam Deck, compilada contra o sysroot "sniper" do Steam Runtime 3 (glibc 2.31), como o
# tools/make_release_linux.py do TotK Recomp (MIT). O Arch/Ubuntu do WSL tem glibc mais nova que a do SteamOS; um
# executável linkado contra ela pediria símbolos GLIBC_2.3x/2.4x que o Deck não tem.
SNIPER = "3.0.20261021.266025"
SNIPER_TAR = (f"https://repo.steampowered.com/steamrt-images-sniper/snapshots/{SNIPER}/"
              "com.valvesoftware.SteamRuntime.Sdk-amd64%2Ci386-sniper-sysroot.tar.gz",
              "8f71947035f97925a311b2ed753f22efcf2f13d6f1631945b8e537f8903ce2cf")
SNIPER_MEMBERS = ["usr/include", "usr/share/pkgconfig", "usr/lib/x86_64-linux-gnu", "usr/lib/gcc/x86_64-linux-gnu",
                  "lib/x86_64-linux-gnu", "lib64"]
ZSTD_TAR = ("https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz",
            "eb33e51f49a15e023950cd7825ca74a4a2b43db8354825ac24fc1b7ee09e6fa3")
# Opus e libvpx estáticos do sysroot (o SteamOS tem outra libvpx.so), zstd estática compilada aqui, SDL3 dinâmica
# copiada para lib/ ao lado do executável, Vulkan do sistema (o loader é estável).
DIST_LIBS = ["-lvulkan", "-lSDL3", "-l:libopus.a", "-l:libvpx.a", "-l:libzstd.a", "-l:libstdc++.a", "-lm", "-lpthread",
             "-ldl"]
GLIBC_MAX = (2, 31)


def fetch(url_sha: tuple[str, str], dst: Path) -> Path:
    import hashlib
    import urllib.request
    if dst.is_file():
        return dst
    url, sha = url_sha
    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"dist: baixando {url}")
    part = dst.with_suffix(dst.suffix + ".part")
    subprocess.run(["curl", "-sL", "--http1.1", "--retry", "5", "-C", "-", "-o", str(part), url], check=True)
    h = hashlib.sha256()
    with part.open("rb") as f:
        while chunk := f.read(16 << 20):
            h.update(chunk)
    if h.hexdigest() != sha:
        part.unlink()
        sys.exit(f"ERRO: {url} não bate com o hash fixado")
    part.rename(dst)
    return dst


def sniper_sysroot(work: Path) -> Path:
    """O sysroot extraído em <work>/toolchain/sniper, com os links simbólicos absolutos tornados relativos (o SDK aponta
    alguns para /lib e /usr/lib, que fora do contêiner seriam os do sistema)."""
    root = work / "toolchain" / "sniper"
    if (root / ".relinked").is_file():
        return root
    tar = fetch(SNIPER_TAR, work / "dl" / "sniper-sysroot.tar.gz")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    print("dist: extraindo o sysroot sniper")
    subprocess.run(["tar", "-xf", str(tar), "-C", str(root), "--wildcards", "--no-wildcards-match-slash",
                    *SNIPER_MEMBERS], check=True)
    for p in root.rglob("*"):
        if p.is_symlink() and os.readlink(p).startswith("/"):
            target = root / os.readlink(p).lstrip("/")
            p.unlink()
            p.symlink_to(os.path.relpath(target, p.parent))
    (root / ".relinked").write_text("")
    return root


def dist_deps(work: Path, cc: list[str]) -> Path:
    """<work>/deps: headers Vulkan 1.4.363 e VMA (só headers) e libzstd.a 1.5.7 compilada contra o sysroot."""
    deps = work / "deps"
    inc, lib = deps / "include", deps / "lib"
    inc.mkdir(parents=True, exist_ok=True)
    lib.mkdir(parents=True, exist_ok=True)
    for d in ("vulkan", "vk_video"):
        if not (inc / d).is_dir():
            if not Path(f"/usr/include/{d}").is_dir():
                sys.exit("ERRO: faltam os headers do Vulkan (pacman -S vulkan-headers / apt install libvulkan-dev)")
            shutil.copytree(f"/usr/include/{d}", inc / d)
    if not (inc / "vk_mem_alloc.h").is_file():
        shutil.copy(vma_include() / "vk_mem_alloc.h", inc / "vk_mem_alloc.h")
    if not (lib / "libzstd.a").is_file():
        tar = fetch(ZSTD_TAR, work / "dl" / "zstd-1.5.7.tar.gz")
        src = work / "dl" / "zstd-1.5.7"
        if not src.is_dir():
            subprocess.run(["tar", "-xf", str(tar), "-C", str(work / "dl")], check=True)
        print("dist: compilando libzstd.a contra o sysroot")
        subprocess.run(["make", "-C", str(src / "lib"), f"-j{os.cpu_count() or 4}", "libzstd.a",
                        f"CC={' '.join(cc)}", "CFLAGS=-O2 -march=x86-64-v3", "ZSTD_LEGACY_SUPPORT=0"],
                       check=True, stdout=subprocess.DEVNULL)
        shutil.copy(src / "lib" / "libzstd.a", lib / "libzstd.a")
        shutil.copy(src / "lib" / "zstd.h", inc / "zstd.h")
        shutil.copy(src / "lib" / "zstd_errors.h", inc / "zstd_errors.h")
    return deps


def glibc_needed(exe: Path) -> tuple[int, int]:
    """A maior versão GLIBC_x.y que o executável pede."""
    out = subprocess.run(["llvm-readelf" if shutil.which("llvm-readelf") else "readelf", "-V", str(exe)],
                         capture_output=True, text=True, check=True).stdout
    import re
    vers = [tuple(map(int, m)) for m in re.findall(r"GLIBC_(\d+)\.(\d+)", out)]
    return max(vers) if vers else (0, 0)


def step_dist(args, gen: Path, lib: Path) -> Path:
    """Compila o runtime e linka contra o sniper, e monta dist/aoc-deck/ (layout em docs/steam-deck.md)."""
    clang, ninja = need("clang"), need("ninja")
    sysroot = sniper_sysroot(args.work)
    cc = [clang, "--target=x86_64-linux-gnu", f"--sysroot={sysroot}"]
    deps = dist_deps(args.work, cc)
    out = args.work / "dist"
    out.mkdir(parents=True, exist_ok=True)
    host = args.work / "host"   # modules.c e romfs_config.h do passo host
    host.mkdir(parents=True, exist_ok=True)
    write_if_changed(host / "modules.c", module_glue(gen, args.exefs))
    sys.path.insert(0, str(ROOT / "tools"))
    import romfs_index
    if not ROMFS_IMAGE.is_file():
        sys.exit(f"ERRO: {ROMFS_IMAGE} não existe (tools/windows/merge_romfs.bat)")
    romfs_index.write(ROMFS_IMAGE, host)
    inc = ["-I", shell_arg(deps / "include"), "-I", shell_arg(RUNTIME), "-I", shell_arg(gen), "-I", shell_arg(host),
           "-I", shell_arg(RUNTIME / "third_party" / "imgui")]
    ccs = " ".join(shell_arg(a) for a in cc)
    lines = [
        "ninja_required_version = 1.10",
        f"builddir = {ninja_escape(out)}",
        f"cc = {ccs}",
        f"rtflags = {' '.join(RT_FLAGS + inc)}",
        f"ldflags = -fuse-ld=lld -no-pie -Wl,-z,noexecstack '-Wl,-rpath,$$ORIGIN/lib' -L {shell_arg(deps / 'lib')}",
        f"libs = {' '.join(DIST_LIBS)}",
        "rule cc_rt",
        "  command = $cc $rtflags -MD -MF $out.d -c $in -o $out",
        "  deps = gcc",
        "  depfile = $out.d",
        "  description = cc $in",
        "rule link",
        "  command = $cc $ldflags @$out.rsp $libs -o $out",
        "  rspfile = $out.rsp",
        "  rspfile_content = $in_newline",
        "  description = link $out",
    ]
    objs = []
    for src in runtime_sources() + [host / "modules.c"]:
        rel = src.relative_to(RUNTIME) if src.is_relative_to(RUNTIME) else Path(src.name)
        o = out / "obj" / rel.with_suffix(".o")
        o.parent.mkdir(parents=True, exist_ok=True)
        lines.append(f"build {ninja_escape(o)}: cc_rt {ninja_escape(src)}")
        objs.append(o)
    exe = out / "aoc"
    lines.append(f"build {ninja_escape(exe)}: link " + " ".join(ninja_escape(o) for o in objs) + f" {ninja_escape(lib)}")
    lines.append(f"default {ninja_escape(exe)}")
    build_file = args.work / "dist.ninja"
    build_file.write_text("\n".join(lines) + "\n")
    t0 = time.time()
    subprocess.run([ninja, "-f", str(build_file)] + (["-j", str(args.jobs)] if args.jobs else []), check=True,
                   cwd=args.work)
    need_glibc = glibc_needed(exe)
    if need_glibc > GLIBC_MAX:
        sys.exit(f"ERRO: {exe} pede GLIBC_{need_glibc[0]}.{need_glibc[1]}, acima da {GLIBC_MAX} do sniper")
    print(f"dist: executável pronto em {time.time() - t0:.0f} s, pede no máximo GLIBC_{need_glibc[0]}.{need_glibc[1]}")
    return assemble_dist(args, exe, sysroot, host)


LAUNCHER = """#!/bin/sh
# Lançador do AoC Recomp na pasta do Deck (tools/build.py dist). Caches do driver ao lado do jogo, no cartão SD,
# e não em ~/.cache (memória interna).
here="$(cd "$(dirname "$0")" && pwd)"
export MESA_SHADER_CACHE_DIR="$here/mesa-cache"
export MESA_SHADER_CACHE_MAX_SIZE=4G
mkdir -p "$here/mesa-cache" "$here/logs"
# o FTP a partir do Windows não leva o bit de execução: garante que o executável roda
[ -x "$here/aoc" ] || chmod +x "$here/aoc" 2>/dev/null
cd "$here"
exec "$here/aoc" "$@"
"""


# Configuração inicial da pasta do Deck (cfg.c: "chave = valor", sem o prefixo AOC_). FPS e modo vêm do perfil "deck"
# do runtime (30 fps, portátil); aqui só o idioma do menu.
INI_DECK = """# Configurações do AoC Recomp. O menu (Menos+Mais) e o menu rápido (segurar L3+R3) gravam aqui.
[menu]
menu_lang = pt-BR
"""

README_DECK = """Hyrule Warriors: Age of Calamity - port nativo para o Steam Deck (AoC Recomp)
================================================================================

Uso pessoal: esta pasta contém o jogo (do seu próprio console). Não compartilhe.

INSTALAR (uma vez)
1. No Deck, em Desktop Mode, copie a pasta inteira "aoc-deck" para o cartão SD (FTP, nuvem ou cabo).
   Exemplo: /run/media/mmcblk0p1/aoc-deck   (o romfs/romfs.bin tem 10,9 GiB)
2. Abra o Konsole dentro da pasta e rode uma vez:   sh instalar-atalho.sh
   (dá permissão de execução e põe o jogo no menu de aplicativos do SteamOS)
3. Steam > Jogos > "Adicionar um jogo que não é da Steam" > marque
   "Hyrule Warriors: Age of Calamity (AoC Recomp)" > Adicionar selecionados.
4. Volte ao Game Mode: o jogo fica na biblioteca, em "Não Steam".

PRIMEIRO TESTE (Konsole, dentro da pasta)
  ./aoc --selftest                         deve terminar com "selftest: passed"
  AOC_GPU=null AOC_TRACE=perf ./aoc.sh     sem imagem; deve mostrar linhas "fps: ... (30.0 fps)" (Ctrl+C para sair)
  ./aoc.sh                                 janela Vulkan. AINDA SEM IMAGEM (tela preta): falta o tradutor de
                                           shaders, a próxima fase do projeto; o jogo roda por trás a 30 fps.
Depois mande de volta o arquivo logs/aoc.log.

CONTROLES DO PORT
  Segurar L3+R3 (~1,5 s)  menu rápido: taxa de quadros, resolução interna, overlay de desempenho
  Tocar L3+R3            liga/desliga o overlay de FPS
  Menos + Mais juntos    menu completo
  B                      fecha os menus

PARA NÃO FORÇAR O DECK
  - Padrão: 30 FPS (a taxa do próprio jogo) e resolução interna "Portátil" (a mais leve do jogo).
  - No menu de desempenho do Steam (botão "..." > bateria) dá para limitar também o TDP e a taxa de atualização.

ARQUIVOS
  aoc, aoc.sh, lib/            o programa
  exefs/, romfs/, romfs-index.bin   o jogo
  aoc.ini                      suas configurações (não é sobrescrito nas atualizações)
  profile/, logs/, mesa-cache/ saves, registros e cache de shaders (criados ao jogar)
ATUALIZAR: copie por cima só "aoc" (e "lib/" se mudar). O romfs não muda.
"""


# Registra o jogo como aplicativo do desktop (~/.local/share/applications), com o caminho de onde a pasta estiver: a
# janela "Adicionar um jogo que não é da Steam" lista esses aplicativos, e um script solto no cartão SD não aparece nela.
INSTALL_SH = """#!/bin/sh
# Cria o atalho do AoC Recomp no menu de aplicativos do SteamOS. Rode uma vez (Desktop Mode, Konsole):
#   sh instalar-atalho.sh
# Depois: Steam > Jogos > "Adicionar um jogo que não é da Steam" > marque "Hyrule Warriors: Age of Calamity".
here="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$here/aoc" "$here/aoc.sh"
mkdir -p "$HOME/.local/share/applications"
f="$HOME/.local/share/applications/aoc-recomp.desktop"
printf '%s\\n' '[Desktop Entry]' 'Type=Application' 'Name=Hyrule Warriors: Age of Calamity (AoC Recomp)' \\
    'Comment=Port nativo (uso pessoal)' "Exec=$here/aoc.sh" "Path=$here" 'Terminal=false' 'Categories=Game;' \\
    'Icon=applications-games' > "$f"
chmod +x "$f"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null
echo "Atalho criado: $f"
echo "Agora: Steam > Jogos > Adicionar um jogo que nao e da Steam > marque Hyrule Warriors: Age of Calamity"
"""


def assemble_dist(args, exe: Path, sysroot: Path, host: Path) -> Path:
    """dist/aoc-deck/: aoc, aoc.sh, lib/libSDL3.so.0, exefs/, romfs-index.bin e romfs/ (o romfs.bin de 10,9 GiB só é
    copiado com --with-romfs: no Deck basta copiá-lo uma vez). Saves, aoc.ini, logs/ e mesa-cache/ nunca são tocados."""
    dist = Path(args.dist).expanduser().resolve()
    (dist / "lib").mkdir(parents=True, exist_ok=True)
    (dist / "exefs").mkdir(exist_ok=True)
    (dist / "romfs").mkdir(exist_ok=True)

    def copy(src: Path, dst: Path) -> None:
        if dst.exists() and dst.stat().st_size == src.stat().st_size and dst.stat().st_mtime >= src.stat().st_mtime:
            return
        shutil.copy2(src, dst)

    copy(exe, dist / "aoc")
    (dist / "aoc").chmod(0o755)
    copy((sysroot / "usr/lib/x86_64-linux-gnu/libSDL3.so.0").resolve(), dist / "lib" / "libSDL3.so.0")
    for f in ("main", "subsdk0", "sdk", "main.npdm"):
        copy(args.exefs / f, dist / "exefs" / f)
    copy(host / "romfs-index.bin", dist / "romfs-index.bin")
    (dist / "aoc.sh").write_text(LAUNCHER)
    (dist / "aoc.sh").chmod(0o755)
    (dist / "LEIA-ME.txt").write_text(README_DECK, encoding="utf-8")
    (dist / "instalar-atalho.sh").write_text(INSTALL_SH, encoding="utf-8")
    (dist / "instalar-atalho.sh").chmod(0o755)
    if not (dist / "aoc.ini").exists():   # só na primeira vez: depois o arquivo é do jogador (o menu grava nele)
        (dist / "aoc.ini").write_text(INI_DECK, encoding="utf-8")
    if args.with_romfs:
        dst = dist / "romfs" / "romfs.bin"
        if not (dst.exists() and dst.stat().st_size == ROMFS_IMAGE.stat().st_size):
            dst.unlink(missing_ok=True)
            try:   # mesmo disco: um hardlink não ocupa outros 10,9 GiB
                os.link(ROMFS_IMAGE, dst)
                print(f"dist: romfs.bin ligado (hardlink) a {ROMFS_IMAGE}")
            except OSError:
                print(f"dist: copiando {ROMFS_IMAGE} ({ROMFS_IMAGE.stat().st_size / 2**30:.1f} GiB)")
                shutil.copy2(ROMFS_IMAGE, dst)
    elif not (dist / "romfs" / "romfs.bin").exists():
        print(f"dist: AVISO: copie {ROMFS_IMAGE} para {dist / 'romfs' / 'romfs.bin'} uma vez (ou use --with-romfs)")
    print(f"dist: pasta pronta em {dist}")
    return dist


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", type=Path, required=True, help="diretório de build no disco do Linux (ex.: ~/aoc-build)")
    ap.add_argument("--exefs", type=Path, default=ROOT / "build" / "v130" / "exefs")
    ap.add_argument("--jobs", type=int, default=0, help="núcleos (padrão: todos)")
    ap.add_argument("--regen", action="store_true", help="gerar o C de novo")
    ap.add_argument("--big-jobs", type=int, default=0, help="funções gigantes compiladas ao mesmo tempo (padrão: pela RAM)")
    ap.add_argument("--ninja-only", action="store_true", help="só escreve o guest.ninja, sem compilar")
    ap.add_argument("--runtime-only", action="store_true", help="host: só compila o runtime, sem linkar")
    ap.add_argument("--dist", default=str(ROOT / "dist" / "aoc-deck"), help="dist: pasta de saída para o Deck")
    ap.add_argument("--with-romfs", action="store_true", help="dist: põe também o romfs.bin (hardlink no mesmo disco, senão cópia)")
    ap.add_argument("steps", nargs="*", help="gen, guest, host, dist (padrão: gen, guest, host)")
    args = ap.parse_args(argv)
    args.steps = args.steps or ["gen", "guest", "host"]
    if set(args.steps) - {"gen", "guest", "host", "dist"}:
        ap.error("passos válidos: gen, guest, host, dist")
    args.work = args.work.expanduser().resolve()
    args.work.mkdir(parents=True, exist_ok=True)
    if not (args.exefs / "main").exists():
        step_extract(args)
    gen = step_gen(args) if "gen" in args.steps else args.work / "generated"
    lib = step_guest(args, gen) if "guest" in args.steps else args.work / "lib" / "libaoc_guest.a"
    if "host" in args.steps:
        step_host(args, gen, lib)
    if "dist" in args.steps:
        step_dist(args, gen, lib)
    return 0


if __name__ == "__main__":
    sys.exit(main())

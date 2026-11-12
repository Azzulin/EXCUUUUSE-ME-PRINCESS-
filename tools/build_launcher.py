"""Builds the launcher (launcher/launcher.cpp) as one self-contained executable.

  Windows, in MSYS2 UCRT64:  python3 tools/build_launcher.py          -> build/launcher/aoc-launcher.exe
  Linux (WSL is fine):       python3 tools/build_launcher.py --linux  -> build/launcher-linux/aoc-launcher

Both link SDL3 and the C++ runtime statically, so nothing has to sit beside the executable. The Linux build is made
against the Steam Runtime "sniper" sysroot that tools/build.py's dist step downloads (glibc 2.31, SDL 3.4 static), so it
runs on any current distribution; --sysroot points at another copy.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMGUI = ROOT / "runtime" / "third_party" / "imgui"
SOURCES = [ROOT / "launcher" / "launcher.cpp"] + [IMGUI / f for f in ("imgui.cpp", "imgui_draw.cpp", "imgui_tables.cpp",
                                                                       "imgui_widgets.cpp")] + \
          [IMGUI / "backends" / f for f in ("imgui_impl_sdl3.cpp", "imgui_impl_sdlrenderer3.cpp")]
CXXFLAGS = ["-O2", "-std=c++17", "-DNDEBUG", "-I", str(IMGUI), "-I", str(IMGUI / "backends")]


def build_windows() -> Path:
    out = ROOT / "build" / "launcher"
    out.mkdir(parents=True, exist_ok=True)
    res = out / "launcher.res.o"
    windres = shutil.which("llvm-windres") or shutil.which("windres")
    if not windres:
        sys.exit("ERRO: llvm-windres/windres não encontrado (pacote mingw-w64-ucrt-x86_64-llvm)")
    subprocess.run([windres, "-i", str(ROOT / "launcher" / "launcher.rc"), "-o", str(res)], check=True,
                   cwd=str(ROOT / "launcher"))
    exe = out / "aoc-launcher.exe"
    # The C++ runtime and winpthread inside the exe; SDL3 stays a DLL: MSYS2's static libSDL3.a pulls in libiconv
    # (LGPL), which is not linked statically here. Beside the exe goes MSYS2's SDL3.dll (and its libiconv-2.dll) for a
    # developer; tools/make_release.py ships the upstream SDL3.dll instead, which imports no libiconv.
    cmd = ["clang++", *CXXFLAGS, *map(str, SOURCES), str(res), "-o", str(exe), "-fuse-ld=lld", "-mwindows",
           "-static-libgcc", "-static-libstdc++", "-Wl,-Bstatic", "-lwinpthread", "-Wl,-Bdynamic", "-lSDL3",
           "-lshell32"]
    subprocess.run(cmd, check=True)
    for old in out.glob("*.dll"):   # an earlier build's DLLs
        old.unlink()
    p = subprocess.run(["ldd", str(exe)], capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if "/ucrt64/" in line and "=>" in line:
            dll = line.split("=>")[1].split("(")[0].strip()
            win = subprocess.run(["cygpath", "-w", dll], capture_output=True, text=True).stdout.strip()
            if Path(win).name.lower() not in ("sdl3.dll", "libiconv-2.dll"):
                sys.exit(f"ERRO: o launcher importa {Path(win).name} do MSYS2 (só a SDL3 deveria ficar fora do exe)")
            shutil.copy2(win, out / Path(win).name)
            print("  ", Path(win).name)
    return exe


def build_linux(sysroot: Path) -> Path:
    if not (sysroot / "usr/lib/x86_64-linux-gnu/libSDL3.a").is_file():
        sys.exit(f"ERRO: {sysroot} não tem a SDL3 estática; rode antes tools/build.py dist (baixa o sniper)")
    out = ROOT / "build" / "launcher-linux"
    out.mkdir(parents=True, exist_ok=True)
    exe = out / "aoc-launcher"
    cc = ["clang++", "--target=x86_64-linux-gnu", f"--sysroot={sysroot}", "-fuse-ld=lld"]
    # SDL3 as the game's Deck build has it: the sniper's libSDL3.so.0 beside the executable (rpath $ORIGIN), which
    # opens X11, Wayland, PulseAudio... with dlopen. The sniper's static libSDL3.a links those directly, so a missing
    # one would stop the launcher from starting. The C++ runtime is static.
    cmd = cc + CXXFLAGS + [*map(str, SOURCES), "-o", str(exe), "-static-libstdc++", "-static-libgcc",
                           "-Wl,-rpath,$ORIGIN", "-lSDL3", "-lpthread", "-ldl", "-lm"]
    subprocess.run(cmd, check=True)
    subprocess.run(["llvm-strip", str(exe)], check=True)
    shutil.copy2((sysroot / "usr/lib/x86_64-linux-gnu/libSDL3.so.0").resolve(), out / "libSDL3.so.0")
    p = subprocess.run(["objdump", "-T", str(exe)], capture_output=True, text=True)
    vers = sorted(set(re.findall(r"GLIBC_(2\.[0-9.]+)", p.stdout)), key=lambda v: tuple(int(x) for x in v.split(".")))
    print(f"glibc máxima pedida: {vers[-1] if vers else '?'}")
    return exe


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--linux", action="store_true")
    ap.add_argument("--sysroot", type=Path, default=Path.home() / "aoc-build" / "toolchain" / "sniper")
    args = ap.parse_args()
    exe = build_linux(args.sysroot) if args.linux else build_windows()
    print(f"pronto: {exe} ({exe.stat().st_size / 2**20:.1f} MiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

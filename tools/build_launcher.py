"""Builds the launcher (launcher/launcher.cpp) into build/launcher/aoc-launcher.exe, with the DLLs it imports beside it.

Runs in MSYS2 UCRT64 (clang++, SDL3): python3 tools/build_launcher.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMGUI = ROOT / "runtime" / "third_party" / "imgui"
OUT = ROOT / "build" / "launcher"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    res = OUT / "launcher.res.o"
    windres = shutil.which("llvm-windres") or shutil.which("windres")
    if not windres:
        sys.exit("ERRO: llvm-windres/windres não encontrado (pacote mingw-w64-ucrt-x86_64-llvm)")
    subprocess.run([windres, "-i", str(ROOT / "launcher" / "launcher.rc"), "-o", str(res)], check=True,
                   cwd=str(ROOT / "launcher"))
    srcs = [ROOT / "launcher" / "launcher.cpp"] + [IMGUI / f for f in ("imgui.cpp", "imgui_draw.cpp", "imgui_tables.cpp",
                                                                        "imgui_widgets.cpp")]
    srcs += [IMGUI / "backends" / f for f in ("imgui_impl_sdl3.cpp", "imgui_impl_sdlrenderer3.cpp")]
    exe = OUT / "aoc-launcher.exe"
    cmd = ["clang++", "-O2", "-std=c++17", "-DNDEBUG", "-I", str(IMGUI), "-I", str(IMGUI / "backends"),
           *map(str, srcs), str(res), "-o", str(exe), "-lSDL3", "-lshell32", "-mwindows"]
    print(" ".join(Path(c).name if "/" in c or "\\" in c else c for c in cmd[:6]), "...", flush=True)
    subprocess.run(cmd, check=True)
    # the DLLs it imports from MSYS2 (SDL3 and the C++ runtime) go beside it
    p = subprocess.run(["ldd", str(exe)], capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if "/ucrt64/" in line and "=>" in line:
            dll = line.split("=>")[1].split("(")[0].strip()
            win = subprocess.run(["cygpath", "-w", dll], capture_output=True, text=True).stdout.strip()
            shutil.copy2(win, OUT / Path(win).name)
            print("  ", Path(win).name)
    print(f"pronto: {exe}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

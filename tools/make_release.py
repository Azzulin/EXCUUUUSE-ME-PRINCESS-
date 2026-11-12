"""Builds the downloadable launcher packages for a GitHub release: one for Windows, one for Linux.

Each package is the repository at HEAD (git archive: our code, no game data) plus what a player's PC cannot be asked
to build before the launcher runs:

  Windows  AoC-Recomp-<v>-Windows.zip
             AoC-Launcher.exe + SDL3.dll       the launcher (tools/build_launcher.py) and upstream SDL 3.4.18
             python/                           Python 3.13 embeddable + cryptography, lz4, numpy (runs make_build.py,
                                               the dump extraction and the C generator)
             prebuilt/hactool/win-x64/         hactool 1.4.0 (ISC) for the RomFS merge
             prebuilt/xlate/{win,linux}-x64/   the shader translator (Ryujinx 1.3.2 + our patches, MIT), so nobody
                                               needs .NET: win-x64 for aoc.exe, linux-x64 for the Deck build in WSL
  Linux    AoC-Recomp-<v>-Linux.tar.gz
             aoc-launcher + libSDL3.so.0       the launcher, built against the Steam Runtime sniper sysroot
             prebuilt/hactool/linux-x64/, prebuilt/xlate/linux-x64/

Run on Windows in MSYS2 UCRT64, from a clean commit, with the development WSL distro set up (its ~/aoc-build has the
sniper sysroot and the Linux translator, its venv has pip):

  python3 tools/make_release.py [--wsl-distro archlinux] [--win-xlate C:/aoc-win/host] [--allow-dirty]

Output in build/release/; the sha256 of each package is printed and written next to it.
"""
import argparse
import hashlib
import io
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "release"
DL = OUT / "dl"
TOP = "AoC-Recomp"   # the folder each package unpacks into
PY_EMBED = ("https://www.python.org/ftp/python/3.13.17/python-3.13.17-embed-amd64.zip",
            "9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38")
SDL_WIN = ("https://github.com/libsdl-org/SDL/releases/download/release-3.4.18/SDL3-3.4.18-win32-x64.zip",
           "75c2c0fc74e7d1206aaedc22893a35887332f4f85f5c8b74fddc10d177985f2c")
WHEELS = ["cryptography", "lz4", "numpy"]
# MSYS2 has no git of its own by default: Git for Windows, else the one on PATH.
GIT = next((g for g in ("C:/Program Files/Git/cmd/git.exe",) if Path(g).is_file()), None) or shutil.which("git") or "git"
# Python's own search path for the launcher's make_build.py and the tools it starts: with a ._pth file the embeddable
# Python ignores the script's folder, so tools/ and recomp/ are listed (no module name is in both).
PTH = "python313.zip\n.\nLib\\site-packages\n..\\tools\n..\\recomp\nimport site\n"


def sh(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def wsl(distro: str, script: str) -> None:
    sh(["wsl", "-d", distro, "-e", "bash", "-lc", script])


def wsl_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return f"/mnt/{s[0].lower()}{s[2:]}" if len(s) > 1 and s[1] == ":" else s


def fetch(url: str, sha: str) -> bytes:
    dst = DL / url.rsplit("/", 1)[1]
    if not dst.is_file() or hashlib.sha256(dst.read_bytes()).hexdigest() != sha:
        DL.mkdir(parents=True, exist_ok=True)
        print(f"baixando {url}", flush=True)
        data = urllib.request.urlopen(url, timeout=120).read()
        if hashlib.sha256(data).hexdigest() != sha:
            sys.exit(f"ERRO: {url} não bate com o hash fixado")
        dst.write_bytes(data)
    return dst.read_bytes()


def git_tree() -> list:
    """(path, mode, bytes) of every file at HEAD, from git archive (keeps the executable bits)."""
    tar = subprocess.run([GIT, "-C", str(ROOT), "archive", "--format=tar", "HEAD"], check=True,
                         capture_output=True).stdout
    files = []
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        for m in t.getmembers():
            if m.isfile():
                files.append((m.name, m.mode, t.extractfile(m).read()))
    return files


def python_embed(wheel_dir: Path) -> list:
    """(path, mode, bytes) of python/: the embeddable zip, our ._pth, and the wheels unpacked into Lib/site-packages."""
    files = []
    with zipfile.ZipFile(io.BytesIO(fetch(*PY_EMBED))) as z:
        for n in z.namelist():
            if not n.endswith("/") and not n.endswith("._pth"):
                files.append((f"python/{n}", 0o644, z.read(n)))
    files.append(("python/python313._pth", 0o644, PTH.encode()))
    wheels = sorted(wheel_dir.glob("*.whl"))
    names = {w.name.split("-")[0].lower() for w in wheels}
    for need in WHEELS:
        if need not in names:
            sys.exit(f"ERRO: falta a wheel de {need} em {wheel_dir}")
    for w in wheels:
        with zipfile.ZipFile(w) as z:
            for n in z.namelist():
                if not n.endswith("/"):
                    files.append((f"python/Lib/site-packages/{n}", 0o644, z.read(n)))
    return files


def write_zip(path: Path, files: list) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, mode, data in files:
            zi = zipfile.ZipInfo(f"{TOP}/{name}", date_time=time.localtime()[:6])
            zi.external_attr = (0o100000 | mode) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)


def write_tgz(path: Path, files: list) -> None:
    now = int(time.time())
    with tarfile.open(path, "w:gz", compresslevel=9) as t:
        for name, mode, data in files:
            ti = tarfile.TarInfo(f"{TOP}/{name}")
            ti.size, ti.mode, ti.mtime = len(data), mode, now
            t.addfile(ti, io.BytesIO(data))


def read(p: Path, mode: int = 0o644) -> tuple:
    return p.read_bytes(), mode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--wsl-distro", default="archlinux", help="the development WSL distro")
    ap.add_argument("--win-xlate", type=Path, default=Path("C:/aoc-win/host"),
                    help="folder with aoc_xlate.exe and aoc_xlate.id for Windows")
    ap.add_argument("--allow-dirty", action="store_true", help="package HEAD even with uncommitted changes")
    args = ap.parse_args()
    version = (ROOT / "VERSION").read_text().strip()
    dirty = subprocess.run([GIT, "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True).stdout.strip()
    if dirty and not args.allow_dirty:
        sys.exit(f"ERRO: há mudanças não commitadas (o pacote leva o HEAD):\n{dirty}")
    OUT.mkdir(parents=True, exist_ok=True)
    stage = OUT / "stage"
    stage.mkdir(exist_ok=True)

    # The translator must match the sources at HEAD (its identity is a hash of them; tools/build_xlate.py). Computed
    # in WSL, where the translator is built: on Windows Python sorts paths without case, which changes the hash.
    ident = subprocess.run(["wsl", "-d", args.wsl_distro, "-e", "bash", "-lc",
                            f"cd '{wsl_path(ROOT)}' && python3 -c 'import sys; sys.path.insert(0, \"tools\"); "
                            f"import build_xlate; print(build_xlate.identity())'"],
                           check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]
    print(f"identidade do tradutor: {ident[:16]}")

    # Linux parts, made in WSL: the launcher, hactool, the Linux translator, and the Windows wheels (pip download)
    s = wsl_path(stage)
    hsrc = wsl_path(ROOT / "toolchain/hactool-1.4.0/hactool-1.4.0")
    wsl(args.wsl_distro, f"cd '{wsl_path(ROOT)}' && python3 tools/build_launcher.py --linux && "
                         f"bash tools/build_hactool_linux.sh '{hsrc}' '{s}/hactool-linux' && "
                         f"mkdir -p '{s}/xlate-linux' && cp ~/aoc-build/xlate/aoc_xlate ~/aoc-build/xlate/aoc_xlate.id "
                         f"'{s}/xlate-linux/' && rm -rf '{s}/wheels' && ~/.venvs/aoc/bin/python -m pip download -q "
                         f"--only-binary=:all: --platform win_amd64 --python-version 3.13 --implementation cp "
                         f"-d '{s}/wheels' {' '.join(WHEELS)}")
    for idf in (stage / "xlate-linux/aoc_xlate.id", args.win_xlate / "aoc_xlate.id"):
        got = idf.read_text().strip()
        if got != ident:
            sys.exit(f"ERRO: {idf} é {got[:16]}, as fontes do tradutor no HEAD dão {ident[:16]}; recompile o tradutor")
    # The Windows launcher (MSYS2: this Python)
    sh([sys.executable, ROOT / "tools/build_launcher.py", "--out", stage / "launcher-win"])   # not the one in use

    tree = git_tree()
    print(f"repositório no HEAD: {len(tree)} arquivos, {sum(len(d) for _, _, d in tree) / 1e6:.1f} MB")
    lic = (ROOT / "toolchain/hactool-1.4.0/hactool-1.4.0/LICENSE").read_bytes()

    # ---- Windows
    with zipfile.ZipFile(io.BytesIO(fetch(*SDL_WIN))) as z:
        sdl_dll = z.read("SDL3.dll")
    win = list(tree)
    win.append(("AoC-Launcher.exe", 0o755, (stage / "launcher-win/aoc-launcher.exe").read_bytes()))
    win.append(("SDL3.dll", 0o644, sdl_dll))
    win += python_embed(stage / "wheels")
    win.append(("prebuilt/hactool/win-x64/hactool.exe", 0o755, (ROOT / "toolchain/hactool-1.4.0-win/hactool.exe").read_bytes()))
    win.append(("prebuilt/hactool/LICENSE", 0o644, lic))
    for f in ("aoc_xlate.exe", "aoc_xlate.id"):
        win.append((f"prebuilt/xlate/win-x64/{f}", 0o755, (args.win_xlate / f).read_bytes()))
    for f in ("aoc_xlate", "aoc_xlate.id"):
        win.append((f"prebuilt/xlate/linux-x64/{f}", 0o755, (stage / "xlate-linux" / f).read_bytes()))

    # ---- Linux
    lin = list(tree)
    lin.append(("aoc-launcher", 0o755, (ROOT / "build/launcher-linux/aoc-launcher").read_bytes()))
    lin.append(("libSDL3.so.0", 0o644, (ROOT / "build/launcher-linux/libSDL3.so.0").read_bytes()))
    lin.append(("prebuilt/hactool/linux-x64/hactool", 0o755, (stage / "hactool-linux/hactool").read_bytes()))
    lin.append(("prebuilt/hactool/LICENSE", 0o644, lic))
    for f in ("aoc_xlate", "aoc_xlate.id"):
        lin.append((f"prebuilt/xlate/linux-x64/{f}", 0o755, (stage / "xlate-linux" / f).read_bytes()))

    outs = [(OUT / f"AoC-Recomp-{version}-Windows.zip", write_zip, win),
            (OUT / f"AoC-Recomp-{version}-Linux.tar.gz", write_tgz, lin)]
    for path, writer, files in outs:
        writer(path, files)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        path.with_name(path.name + ".sha256").write_text(f"{digest}  {path.name}\n")
        print(f"{path.name}: {path.stat().st_size / 1e6:.1f} MB, {len(files)} arquivos, sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

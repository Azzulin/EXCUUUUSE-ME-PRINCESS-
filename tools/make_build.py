"""Builds the game from the player's own dump, start to finish, for the launcher (launcher/launcher.cpp) or by hand.

Runs on Windows (the launcher's embedded Python, or MSYS2's) and on Linux (the system python3: this script needs only
the standard library; the tools it calls run in ~/.venvs/aoc, which the tools step makes).

Steps (each prints "@@STEP <id> <run|ok|fail|skip> <text>"; every other line is log; the last line is "@@DONE ok|fail";
"@@NEED wsl" asks the launcher to offer installing WSL):

  check     the dump folder (NSPs of the base, update 1.3.0 and DLCs, and prod.keys), free disk and memory
  tools     the build environment, set up once and then only checked:
              Windows + Deck: WSL and a private Arch Linux distro "AoC-Recomp" (wsl --install archlinux --name), with
                              tools/setup_wsl.sh --minimal inside (clang, lld, ninja, Python venv)
              Windows target: MSYS2 UCRT64 (C:/msys64; a pinned msys2-base is unpacked there if missing) with clang,
                              SDL3, Opus, libvpx, zstd and Vulkan
              Linux:          the distro's packages and the venv (tools/setup_wsl.sh --minimal; pkexec asks for the
                              password in a window)
  extract   build/v130/exefs from the update (tools/extract.py exefs), once
  romfs     build/v130/romfs.bin, base + update merged (tools/merge_romfs.py with hactool), once
  deck      dist/aoc-deck: generate the C, compile and assemble (tools/build.py gen guest dist), in WSL or natively
  wingen    the generated C for Windows: copied from WSL when the Deck step made it, else generated here
  winxlate  aoc_xlate.exe, the shader translator for Windows (prebuilt/xlate/win-x64 from the release package)
  winbuild  aoc.exe in MSYS2 UCRT64 (tools/build.py guest host)
  windist   dist/aoc-windows: aoc.exe, its DLLs, the translator, exefs/, romfs/ (a hard link), romfs-index.bin
  send      the Deck folder's changed files to the Steam Deck over SSH (tools/deck/deploy.sh --no-build)

Nothing here reads or prints key values: the key file's path goes to the tools that need it.

  python tools/make_build.py --game-dir "D:/dump" --deck --windows [--send] [--with-romfs] [--lang en]
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_ID, UPDATE_ID = "01002B00111A2000", "01002B00111A2800"
WIN = os.name == "nt"
DISTRO = "AoC-Recomp"   # the private WSL distro the tools step makes
VENV_PY = Path.home() / ".venvs" / "aoc" / "bin" / "python"
# MSYS2 base, pinned (https://github.com/msys2/msys2-installer/releases/tag/2026-09-27); unpacked only when the PC has
# no MSYS2. The packages come from MSYS2's own mirrors.
MSYS2_SFX = ("https://github.com/msys2/msys2-installer/releases/download/2026-09-27/msys2-base-x86_64-20260927.sfx.exe",
             "ad336cccfda47758b5e15cda993fbba421115cb0b126697daef1ee4dfe37209f")
# python-cryptography and python-lz4: tools/build.py's host step indexes the RomFS (romfs_index.py imports nx.py).
MSYS2_PKGS = ["clang", "lld", "llvm", "ninja", "sdl3", "opus", "libvpx", "zstd", "vulkan-headers", "vulkan-loader",
              "vulkan-memory-allocator", "python", "python-cryptography", "python-lz4"]
GIB = 2**30

LANG = "pt"
TEXT = {
    # step titles
    "t_check": ("Conferir os arquivos", "Check your files"),
    "t_tools": ("Preparar as ferramentas", "Set up the build tools"),
    "t_extract": ("Extrair o código do jogo", "Extract the game code"),
    "t_romfs": ("Montar o RomFS 1.3.0", "Build the 1.3.0 RomFS"),
    "t_deck": ("Compilar para Steam Deck / Linux", "Compile for Steam Deck / Linux"),
    "t_wingen": ("Gerar o código para o Windows", "Generate the code for Windows"),
    "t_winxlate": ("Tradutor de shaders do Windows", "Windows shader translator"),
    "t_winbuild": ("Compilar para o Windows", "Compile for Windows"),
    "t_windist": ("Montar a pasta do Windows", "Assemble the Windows folder"),
    "t_send": ("Enviar ao Steam Deck", "Send to the Steam Deck"),
    # messages
    "no_dir": ("a pasta do jogo não existe: {0}", "the game folder does not exist: {0}"),
    "missing": ("faltam na pasta escolhida: {0}", "missing from the chosen folder: {0}"),
    "base": ("o jogo base (01002B00111A2000)", "the base game (01002B00111A2000)"),
    "update": ("o update 1.3.0 (01002B00111A2800)", "update 1.3.0 (01002B00111A2800)"),
    "disk": ("pouco espaço livre em {0}: {1:.0f} GB livres, a forja precisa de ~{2:.0f} GB",
             "not enough free space on {0}: {1:.0f} GB free, the build needs about {2:.0f} GB"),
    "ram": ("AVISO: {0:.0f} GB de RAM; com menos de 8 GB a compilação pode falhar ou levar horas",
            "WARNING: {0:.0f} GB of RAM; with less than 8 GB the build may fail or take hours"),
    "send_deck": ("enviar ao Deck pede a pasta do Deck", "sending to the Deck needs the Deck folder"),
    "need_wsl": ("o WSL não está instalado: clique em \"Instalar o WSL\" (pede administrador) e reinicie o PC",
                 "WSL is not installed: click \"Install WSL\" (asks for administrator) and restart the PC"),
    "wsl_install": ("criando a distro Linux privada {0} (Arch Linux, ~1 GB, só na primeira vez)...",
                    "creating the private Linux distro {0} (Arch Linux, ~1 GB, first time only)..."),
    "wsl_old": ("o WSL não criou a distro: atualize-o (num terminal como administrador: wsl --update) e forje de novo",
                "WSL could not create the distro: update it (in an administrator terminal: wsl --update) and forge again"),
    "no_distro": ("a distro do WSL \"{0}\" não existe (wsl -l -v)", "the WSL distro \"{0}\" does not exist (wsl -l -v)"),
    "msys_get": ("baixando o MSYS2 ({0:.0f} MB, só na primeira vez)...", "downloading MSYS2 ({0:.0f} MB, first time only)..."),
    "msys_hash": ("o download do MSYS2 não bate com o hash fixado", "the MSYS2 download does not match the pinned hash"),
    "msys_pkgs": ("instalando o compilador e as bibliotecas no MSYS2 (~1,5 GB, só na primeira vez)...",
                  "installing the compiler and libraries into MSYS2 (~1.5 GB, first time only)..."),
    "tools_ok": ("ferramentas prontas", "tools ready"),
    "exit": ("o comando terminou com o código {0}", "the command ended with code {0}"),
    "no_win_linux": ("a versão Windows só é compilada no Windows", "the Windows version can only be built on Windows"),
    "missing_file": ("falta {0}", "missing {0}"),
    "folder_ok": ("pasta pronta: {0}", "folder ready: {0}"),
    "no_xlate": ("falta o tradutor de shaders do Windows (prebuilt/xlate/win-x64) e não há .NET para compilá-lo",
                 "the Windows shader translator is missing (prebuilt/xlate/win-x64) and there is no .NET to build it"),
    "no_bash": ("o Git Bash não está em C:/Program Files/Git (o envio usa ssh e scp dele)",
                "Git Bash is not in C:/Program Files/Git (sending uses its ssh and scp)"),
    "unexpected": ("ERRO inesperado: {0}", "Unexpected ERROR: {0}"),
}


def tr(key: str, *a) -> str:
    pt, en = TEXT[key]
    return (en if LANG == "en" else pt).format(*a)


def out(line: str) -> None:
    print(line, flush=True)


def step(sid: str, state: str, text: str = "") -> None:
    out(f"@@STEP {sid} {state} {text}".rstrip())


class StepFailed(Exception):
    pass


def run(cmd, cwd=None, env=None) -> None:
    """Runs a command, its output going to the log line by line; a non-zero exit fails the step."""
    env = dict(env or os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", WSL_UTF8="1")
    p = subprocess.Popen([str(c) for c in cmd], cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL)
    for raw in iter(p.stdout.readline, b""):
        line = raw.decode("utf-8", "replace").rstrip("\r\n").replace("\x00", "")
        if line.strip():
            out(line)
    if p.wait():
        raise StepFailed(tr("exit", p.returncode))


def capture(cmd, env=None) -> subprocess.CompletedProcess:
    env = dict(env or os.environ, WSL_UTF8="1")
    return subprocess.run([str(c) for c in cmd], capture_output=True, env=env, stdin=subprocess.DEVNULL)


def wsl_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return f"/mnt/{s[0].lower()}{s[2:]}" if len(s) > 1 and s[1] == ":" else s


def msys_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return f"/{s[0].lower()}{s[2:]}" if len(s) > 1 and s[1] == ":" else s


def sh_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def distro(args) -> str:
    return args.wsl_distro or DISTRO


def wsl(args, script: str, root: bool = False) -> None:
    run(["wsl", "-d", distro(args)] + (["-u", "root"] if root else []) + ["-e", "bash", "-lc", script])


def msys_root(args) -> Path:
    return Path(args.msys2 or os.environ.get("AOC_MSYS2", "") or "C:/msys64")


def msys(args, script: str) -> None:
    env = dict(os.environ, MSYSTEM="UCRT64", CHERE_INVOKING="1")
    run([msys_root(args) / "usr/bin/bash.exe", "-lc", script], cwd=str(ROOT), env=env)


def tool_python() -> str:
    """The Python with cryptography, lz4 and numpy: this one on Windows (the launcher's embedded Python or MSYS2's),
    the venv on Linux."""
    if not WIN and VENV_PY.is_file():
        return str(VENV_PY)
    return sys.executable


def mem_gib() -> float:
    try:
        if WIN:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                            ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]
            m = MS()
            m.len = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.total / GIB
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / GIB
    except Exception:
        return 0.0


# ---- steps

def s_check(args) -> None:
    g = args.game_dir
    if not g.is_dir():
        raise StepFailed(tr("no_dir", g))
    nsps = sorted(g.rglob("*.nsp"))
    base = [p for p in nsps if BASE_ID in p.name.upper()]
    upd = [p for p in nsps if UPDATE_ID in p.name.upper()]
    dlc = [p for p in nsps if "01002B00111A3" in p.name.upper()]
    out(f"{g}: {len(nsps)} NSP; base {'ok' if base else '--'}; update 1.3.0 {'ok' if upd else '--'}; "
        f"DLC {len(dlc)}; prod.keys {'ok' if args.keys.is_file() else '--'}")
    miss = [tr("base")] * (not base) + [tr("update")] * (not upd) + ["prod.keys"] * (not args.keys.is_file())
    if miss:
        raise StepFailed(tr("missing", ", ".join(miss)))
    # The inventory reads the NSP headers (needs cryptography: on Linux only once the venv exists).
    if WIN or VENV_PY.is_file():
        run([tool_python(), ROOT / "tools/extract.py", "inventory", "--game-dir", g, "--keys", args.keys])
    if args.windows and not WIN:
        raise StepFailed(tr("no_win_linux"))
    if args.send and not args.deck:
        raise StepFailed(tr("send_deck"))
    # Space: the RomFS merge holds the NCAs (~11 GB) and the image (10.9 GB) at once; each build ~6-8 GB.
    need = (23 if not (ROOT / "build/v130/romfs.bin").is_file() else 0) + 7 * args.deck + 9 * args.windows
    free = shutil.disk_usage(ROOT).free / 1e9
    out(f"{ROOT}: {free:.0f} GB")
    if free < need:
        raise StepFailed(tr("disk", ROOT.anchor or ROOT, free, need))
    ram = mem_gib()
    if ram and ram < 7.5:
        out(tr("ram", ram))


def wsl_ready() -> bool:
    try:
        return capture(["wsl", "--status"]).returncode == 0
    except OSError:
        return False


def wsl_distros() -> list:
    p = capture(["wsl", "-l", "-q"])
    text = p.stdout.decode("utf-8", "replace").replace("\x00", "")
    return [l.strip() for l in text.splitlines() if l.strip()]


def tools_wsl(args) -> None:
    if not wsl_ready():
        out("@@NEED wsl")
        raise StepFailed(tr("need_wsl"))
    d = distro(args)
    if d not in wsl_distros():
        if args.wsl_distro and args.wsl_distro != DISTRO:
            raise StepFailed(tr("no_distro", d))
        out(tr("wsl_install", d))
        loc = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AoC-Recomp" / "wsl"
        loc.mkdir(parents=True, exist_ok=True)
        try:
            run(["wsl", "--install", "archlinux", "--name", d, "--location", loc, "--no-launch"])
        except StepFailed:   # --name and --location need WSL 2.4 or newer (Windows 10 may ship an older one)
            raise StepFailed(tr("wsl_old"))
    # The managed distro runs as root (the Arch image's default user); a distro of the user's own runs as its user.
    wsl(args, f"cd {sh_quote(wsl_path(ROOT))} && bash tools/setup_wsl.sh --minimal", root=d == DISTRO)


def download(url: str, sha: str, dst: Path) -> None:
    if dst.is_file() and hashlib.sha256(dst.read_bytes()).hexdigest() == sha:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=60) as r, open(part, "wb") as f:
        total, got, mark = int(r.headers.get("Content-Length") or 0), 0, 0
        h = hashlib.sha256()
        while chunk := r.read(1 << 20):
            f.write(chunk)
            h.update(chunk)
            got += len(chunk)
            if total and got * 10 // total > mark:
                mark = got * 10 // total
                out(f"  {got / 1e6:.0f} / {total / 1e6:.0f} MB")
    if h.hexdigest() != sha:
        part.unlink(missing_ok=True)
        raise StepFailed(tr("msys_hash"))
    part.replace(dst)


def tools_msys2(args) -> None:
    root = msys_root(args)
    bash = root / "usr/bin/bash.exe"
    if not bash.is_file():
        url, sha = MSYS2_SFX
        out(tr("msys_get", 43))
        sfx = ROOT / "build" / "dl" / url.rsplit("/", 1)[1]
        download(url, sha, sfx)
        # the self-extracting archive makes <parent>/msys64
        run([sfx, "-y", f"-o{root.parent}"])
        if root.name != "msys64":
            (root.parent / "msys64").rename(root)
        sfx.unlink(missing_ok=True)
        msys(args, "true")   # first start: makes the home folder and the pacman keyring
        # A fresh base updates its core first and MSYS2 closes every one of its processes, this shell included (exit
        # code 1): that first round may "fail"; the second updates the rest and must succeed.
        try:
            msys(args, "pacman -Syuu --noconfirm --disable-download-timeout")
        except StepFailed:
            out("MSYS2: core updated, second round")
        msys(args, "pacman -Syuu --noconfirm --disable-download-timeout")
    pkgs = [f"mingw-w64-ucrt-x86_64-{p}" for p in MSYS2_PKGS]
    q = capture([bash, "-lc", "pacman -Q " + " ".join(pkgs)], env=dict(os.environ, MSYSTEM="UCRT64"))
    if q.returncode != 0:
        out(tr("msys_pkgs"))
        msys(args, "pacman -S --needed --noconfirm --disable-download-timeout " + " ".join(pkgs))


def s_tools(args) -> str:
    if WIN:
        if args.deck:
            tools_wsl(args)
        if args.windows:
            tools_msys2(args)
    else:
        run(["bash", ROOT / "tools/setup_wsl.sh", "--minimal"], cwd=str(ROOT))
    out(tr("tools_ok"))
    return "ok"


def s_extract(args) -> str:
    if (ROOT / "build/v130/exefs/main").is_file():
        return "skip"
    run([tool_python(), ROOT / "tools/extract.py", "exefs", "--game-dir", args.game_dir, "--keys", args.keys])
    run([tool_python(), ROOT / "tools/inspect_dump.py", "--exefs", ROOT / "build/v130/exefs"])
    return "ok"


def s_romfs(args) -> str:
    if (ROOT / "build/v130/romfs.bin").is_file():
        return "skip"
    run([tool_python(), ROOT / "tools/merge_romfs.py", "--game-dir", args.game_dir, "--keys", args.keys])
    return "ok"


def s_deck(args) -> str:
    extra = " --with-romfs" if args.with_romfs else ""
    if WIN:
        wsl(args, f"cd {sh_quote(wsl_path(ROOT))} && . ~/.venvs/aoc/bin/activate && "
                  f"python3 -u tools/build.py --work ~/aoc-build gen guest dist{extra}", root=distro(args) == DISTRO)
    else:
        run([tool_python(), "-u", ROOT / "tools/build.py", "--work", Path.home() / "aoc-build", "gen", "guest", "dist"]
            + (["--with-romfs"] if args.with_romfs else []), cwd=str(ROOT))
    return "ok"


def s_wingen(args) -> str:
    gen = args.win_work / "generated"
    if not args.deck:   # no WSL build: generate the C here (the generator runs on Windows too)
        run([tool_python(), "-u", ROOT / "tools/build.py", "--work", args.win_work, "gen"], cwd=str(ROOT))
        return "ok"
    # the Deck step generated it in WSL: copy only the files that changed
    w = wsl_path(gen)
    wsl(args, "cd ~/aoc-build/generated && n=0 && while IFS= read -r -d '' f; do d=" + sh_quote(w) + "\"/$f\"; "
              "if ! cmp -s \"$f\" \"$d\"; then mkdir -p \"$(dirname \"$d\")\"; cp \"$f\" \"$d\"; n=$((n+1)); fi; "
              "done < <(find . -type f -print0) && echo \"$n arquivos gerados copiados\"", root=distro(args) == DISTRO)
    return "ok"


def s_winxlate(args) -> str:
    host = args.win_work / "host"
    host.mkdir(parents=True, exist_ok=True)
    pre = ROOT / "prebuilt/xlate/win-x64"
    if (pre / "aoc_xlate.exe").is_file():
        for f in ("aoc_xlate.exe", "aoc_xlate.id"):
            if not (host / f).is_file() or (host / f).read_bytes() != (pre / f).read_bytes():
                shutil.copy2(pre / f, host / f)
        return "ok"
    # developer tree: published from the WSL build of the translator (dotnet in WSL)
    if not args.deck and not wsl_ready():
        raise StepFailed(tr("no_xlate"))
    w = wsl_path(host)
    wsl(args, f"cd {sh_quote(wsl_path(ROOT))} && . ~/.venvs/aoc/bin/activate && "
              f"( [ -x ~/aoc-build/xlate/aoc_xlate ] || python3 tools/build_xlate.py --out ~/aoc-build/xlate "
              f"--sysroot ~/aoc-build/toolchain/sniper ) && "
              f"if [ -f '{w}/aoc_xlate.exe' ] && cmp -s ~/aoc-build/xlate/aoc_xlate.id '{w}/aoc_xlate.id'; then "
              f"echo 'tradutor do Windows em dia'; else B=~/aoc-build/xlate && rm -rf /tmp/aoc-xlwin && "
              f"dotnet publish \"$B/xlate/aoc_xlate.csproj\" -c Release -r win-x64 --self-contained -p:PublishAot=false "
              f"-p:PublishSingleFile=true -p:InvariantGlobalization=true -p:RyuSrc=\"$B/ryujinx\" -o /tmp/aoc-xlwin "
              f"| tail -2 && cp /tmp/aoc-xlwin/aoc_xlate.exe '{w}/' && cp \"$B/aoc_xlate.id\" '{w}/'; fi")
    return "ok"


def s_winbuild(args) -> str:
    msys(args, f"python3 -u tools/build.py --work {sh_quote(msys_path(args.win_work))} --big-jobs 2 guest host")
    return "ok"


def s_windist(args) -> str:
    src, dist = args.win_work / "host", ROOT / "dist/aoc-windows"
    (dist / "exefs").mkdir(parents=True, exist_ok=True)
    (dist / "romfs").mkdir(exist_ok=True)

    def copy(a: Path, b: Path) -> None:
        if not a.is_file():
            raise StepFailed(tr("missing_file", a))
        if b.exists() and b.stat().st_size == a.stat().st_size and b.stat().st_mtime >= a.stat().st_mtime:
            return
        shutil.copy2(a, b)

    for f in ("aoc.exe", "aoc_xlate.exe", "aoc_xlate.id", "romfs-index.bin"):
        copy(src / f, dist / f)
    # the DLLs aoc.exe imports from MSYS2 (SDL3, libopus and what they pull in)
    p = capture([msys_root(args) / "usr/bin/bash.exe", "-lc", f"ldd {sh_quote(msys_path(dist / 'aoc.exe'))}"],
                env=dict(os.environ, MSYSTEM="UCRT64"))
    lines = p.stdout.decode("utf-8", "replace").splitlines()
    dlls = [l.split("=>")[1].split("(")[0].strip() for l in lines if "/ucrt64/" in l]
    for d in dlls:
        win = msys_root(args) / d.lstrip("/")
        copy(win, dist / win.name)
        out(f"  {win.name}")
    for f in ("main", "subsdk0", "sdk", "main.npdm"):
        copy(ROOT / "build/v130/exefs" / f, dist / "exefs" / f)
    rom, dst = ROOT / "build/v130/romfs.bin", dist / "romfs/romfs.bin"
    if not dst.exists():
        try:
            os.link(rom, dst)   # same disk: no second 10.9 GiB
            out("romfs.bin: hard link")
        except OSError:
            out("romfs.bin: copy (10.9 GiB)")
            shutil.copy2(rom, dst)
    ini = dist / "aoc.ini"
    if not ini.exists():
        lang = "en" if LANG == "en" else "pt-BR"
        ini.write_text(f"# AoC Recomp settings. The menu (F1) writes here.\n[menu]\nmenu_lang = {lang}\n", encoding="utf-8")
    out(tr("folder_ok", dist))
    return "ok"


def s_send(args) -> str:
    bash = Path("C:/Program Files/Git/bin/bash.exe") if WIN else Path(shutil.which("bash") or "/bin/bash")
    if not bash.is_file():
        raise StepFailed(tr("no_bash"))
    env = dict(os.environ)
    if args.deck_host:
        env["AOC_DECK"] = args.deck_host
    run([bash, ROOT / "tools/deck/deploy.sh", "--no-build"], cwd=str(ROOT), env=env)
    return "ok"


def main() -> int:
    global LANG
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # the launcher reads UTF-8
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game-dir", type=Path, default=ROOT / "Game Files", help="folder with the NSPs and prod.keys")
    ap.add_argument("--keys", type=Path, help="key file (default: prod.keys in the game folder)")
    ap.add_argument("--deck", action="store_true", help="Steam Deck / Linux folder (dist/aoc-deck)")
    ap.add_argument("--windows", action="store_true", help="Windows version (dist/aoc-windows)")
    ap.add_argument("--with-romfs", action="store_true", help="Deck: also put romfs.bin in the folder (first install)")
    ap.add_argument("--send", action="store_true", help="send to the Deck over SSH at the end")
    ap.add_argument("--deck-host", default="", help="user@address of the Deck (default: tools/deck/deploy.sh's)")
    ap.add_argument("--win-work", type=Path, default=None, help="work folder of the Windows build")
    ap.add_argument("--wsl-distro", default=os.environ.get("AOC_WSL_DISTRO", ""),
                    help=f"WSL distro (default: {DISTRO}, made by the tools step)")
    ap.add_argument("--msys2", default="", help="MSYS2 folder (default: C:/msys64, installed there if missing)")
    ap.add_argument("--lang", choices=("pt", "en"), default="pt")
    ap.add_argument("--check-only", action="store_true", help="only the check step")
    args = ap.parse_args()
    LANG = args.lang
    args.game_dir = args.game_dir.expanduser()
    args.keys = (args.keys or args.game_dir / "prod.keys").expanduser()
    if args.win_work is None:
        args.win_work = Path("C:/aoc-win") if Path("C:/aoc-win/host").is_dir() else ROOT / "build/win"
    if not (args.deck or args.windows):
        ap.error("--deck, --windows or both")
    plan = [("check", s_check), ("tools", s_tools), ("extract", s_extract), ("romfs", s_romfs)]
    if args.deck:
        plan.append(("deck", s_deck))
    if args.windows:
        plan += [("wingen", s_wingen), ("winxlate", s_winxlate), ("winbuild", s_winbuild), ("windist", s_windist)]
    if args.send:
        plan.append(("send", s_send))
    if args.check_only:
        plan = plan[:1]
    for sid, _ in plan:
        out(f"@@PLAN {sid} {tr('t_' + sid)}")
    for sid, fn in plan:
        title = tr("t_" + sid)
        step(sid, "run", title)
        try:
            r = fn(args)
            step(sid, r or "ok", title)
        except StepFailed as e:
            out(f"ERROR: {e}" if LANG == "en" else f"ERRO: {e}")
            step(sid, "fail", str(e))
            out("@@DONE fail")
            return 1
        except Exception as e:   # anything unexpected still ends the protocol cleanly
            out(tr("unexpected", repr(e)))
            step(sid, "fail", repr(e))
            out("@@DONE fail")
            return 1
    out("@@DONE ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

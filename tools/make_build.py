"""Builds the game from the player's own dump, start to finish, for the launcher (launcher/launcher.cpp) or by hand.

Runs on Windows (the launcher's embedded Python, or MSYS2's) and on Linux (the system python3: this script needs only
the standard library; the tools it calls run in ~/.venvs/aoc, which the tools step makes).

Steps (each prints "@@STEP <id> <run|ok|fail|skip> <text>"; every other line is log; the last line is "@@DONE ok|fail";
"@@NEED wsl" asks the launcher to offer installing WSL):

  check     the dump folder (NSPs of the base, update 1.3.0 and DLCs, and prod.keys; each package is identified by
            its contents, not its file name, and an update of another version is refused), free disk and memory
  tools     the build environment, set up once and then only checked:
              Windows + Deck: WSL and a private Arch Linux distro "AoC-Recomp" (wsl --install archlinux --name), with
                              tools/setup_wsl.sh --minimal inside (clang, lld, ninja, Python venv)
              Windows target: MSYS2 UCRT64 (C:/msys64; a pinned msys2-base is unpacked there if missing) with clang,
                              SDL3, Opus, libvpx, zstd and Vulkan
              Linux:          the distro's packages and the venv (tools/setup_wsl.sh --minimal; pkexec asks for the
                              password in a window)
              Linux whose system cannot take packages (SteamOS, Bazzite and other Fedora Atomic, NixOS): a
                              distrobox container "aoc-recomp" (Arch Linux) with tools/setup_wsl.sh --minimal inside;
                              every tool of the later steps runs in it (the home folder is shared, so build/,
                              ~/aoc-build and the venv are the same files)
  extract   build/v130/exefs from the update (tools/extract.py exefs), once
  romfs     build/v130/romfs.bin, base + update merged (tools/merge_romfs.py with hactool), once
  dlc       build/v130/dlc-<title id>.bin, the RomFS of each DLC in the dump (tools/extract_dlc.py), once; the game
            folders get them next to romfs.bin, and a dump without DLCs builds a game without them
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
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").is_file() else "?"
BASE_ID, UPDATE_ID = "01002B00111A2000", "01002B00111A2800"
WIN = os.name == "nt"
DISTRO = "AoC-Recomp"   # the private WSL distro the tools step makes
VENV_PY = Path.home() / ".venvs" / "aoc" / "bin" / "python"
# Linux with a system the forge cannot install into: the tools live in this distrobox container instead. Arch, like the
# WSL distro, so tools/setup_wsl.sh takes the same pacman path that the Windows forge uses every day.
CONTAINER = "aoc-recomp"
CONTAINER_IMAGE = "docker.io/library/archlinux:latest"
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
    "t_dlc": ("Extrair os DLCs", "Extract the DLCs"),
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
    "disk": ("pouco espaço livre em {0}: {1:.0f} GB livres, a geração precisa de ~{2:.0f} GB",
             "not enough free space on {0}: {1:.0f} GB free, the build needs about {2:.0f} GB"),
    "ram": ("AVISO: {0:.0f} GB de RAM; com menos de 8 GB a compilação pode falhar ou levar horas",
            "WARNING: {0:.0f} GB of RAM; with less than 8 GB the build may fail or take hours"),
    "send_deck": ("enviar ao Deck pede a pasta do Deck", "sending to the Deck needs the Deck folder"),
    "need_wsl": ("o WSL não está instalado: clique em \"Instalar o WSL\" (pede administrador) e reinicie o PC",
                 "WSL is not installed: click \"Install WSL\" (asks for administrator) and restart the PC"),
    "wsl_install": ("criando a distro Linux privada {0} (Arch Linux, ~1 GB, só na primeira vez)...",
                    "creating the private Linux distro {0} (Arch Linux, ~1 GB, first time only)..."),
    "wsl_old": ("o WSL não criou a distro: atualize-o (num terminal como administrador: wsl --update) e gere de novo",
                "WSL could not create the distro: update it (in an administrator terminal: wsl --update) and build again"),
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
    # what tools/extract.py inventory found wrong in the dump ("@@PROBLEM <code> <detail>")
    "p_base": ("não achei o jogo base (01002B00111A2000) entre os NSPs da pasta (ou há mais de um)",
               "the base game (01002B00111A2000) is not among the NSPs in the folder (or there is more than one)"),
    "p_update": ("não achei o update 1.3.0 (01002B00111A2800) entre os NSPs da pasta",
                 "update 1.3.0 (01002B00111A2800) is not among the NSPs in the folder"),
    "p_updates": ("há mais de um update 1.3.0 na pasta; deixe só um", "there is more than one update 1.3.0 in the folder; keep one"),
    "p_wrong_update": ("o update da sua pasta é de outra versão (v{0}; o 1.4.1 é o v458752). O AoC Recomp só funciona "
                       "com o update 1.3.0 (v327680): troque o NSP do update pelo da 1.3.0 e gere de novo",
                       "the update in your folder is another version (v{0}; 1.4.1 is v458752). AoC Recomp only works "
                       "with update 1.3.0 (v327680): replace the update NSP with the 1.3.0 one and build again"),
    "no_nsp": ("não há arquivos .nsp na pasta escolhida", "there are no .nsp files in the chosen folder"),
    "wrong_build": ("o código do jogo extraído não é o da versão 1.3.0. O AoC Recomp só funciona com o update 1.3.0 "
                    "(v327680); o 1.4.1 ainda não é aceito. Troque o NSP do update e gere de novo",
                    "the extracted game code is not version 1.3.0. AoC Recomp only works with update 1.3.0 (v327680); "
                    "1.4.1 is not accepted yet. Replace the update NSP and build again"),
    "stale_exefs": ("o código extraído numa tentativa anterior não é o da versão 1.3.0: extraindo de novo",
                    "the game code extracted by an earlier attempt is not version 1.3.0: extracting again"),
    "stale_romfs": ("o romfs.bin de uma tentativa anterior não é o da versão 1.3.0 ({0} bytes): montando de novo",
                    "the romfs.bin of an earlier attempt is not the 1.3.0 one ({0} bytes): building it again"),
    "romfs_size": ("o RomFS montado tem {0} bytes, o da versão 1.3.0 tem {1}: confira se o jogo base e o update são os "
                   "certos (base v0 e update 1.3.0)",
                   "the merged RomFS has {0} bytes, the 1.3.0 one has {1}: check that the base game and the update are "
                   "the right ones (base v0 and update 1.3.0)"),
    "immutable": ("este Linux ({0}) não deixa instalar as ferramentas de compilação no sistema, e o distrobox, que as "
                  "instalaria num contêiner, não está instalado. Instale o distrobox (o SteamOS 3.5+ e o Bazzite já "
                  "trazem) ou gere num PC com Windows ou Linux e copie a pasta dist/aoc-deck para cá (guia, seção 4)",
                  "this Linux ({0}) does not let the build tools be installed into the system, and distrobox, which "
                  "would install them in a container, is missing. Install distrobox (SteamOS 3.5+ and Bazzite ship "
                  "it) or build on a Windows or Linux PC and copy the dist/aoc-deck folder here (guide, section 4)"),
    "box_make": ("criando o contêiner {0} (Arch Linux, ~1,5 GB, só na primeira vez; o sistema não é alterado)...",
                 "creating the container {0} (Arch Linux, ~1.5 GB, first time only; the system is not changed)..."),
    "box_fail": ("o distrobox não criou o contêiner {0}; veja as linhas acima (o podman ou o docker precisa funcionar)",
                 "distrobox could not create the container {0}; see the lines above (podman or docker must work)"),
    "names_later": ("os nomes dos NSPs não dizem o que são; o conteúdo é conferido depois de preparar as ferramentas",
                    "the NSP names do not say what they are; their contents are checked once the tools are ready"),
    "cpu_old": ("o processador deste PC não tem AVX2/FMA/BMI2 (têm: Intel Core de 4ª geração, de 2013, em diante, e AMD "
                "Ryzen em diante; Pentium e Celeron antigos e AMD FX não têm), e o jogo compilado precisa deles: a "
                "versão Windows não abriria aqui. A versão do Steam Deck pode ser gerada mesmo assim",
                "this PC's processor lacks AVX2/FMA/BMI2 (Intel Core 4th gen, from 2013, and newer and AMD Ryzen and "
                "newer have them; older Pentium and Celeron and AMD FX do not), which the compiled game needs: the "
                "Windows version would not start here. The Steam Deck version can still be built"),
    "cpu_warn": ("AVISO: o processador deste PC não tem AVX2/FMA/BMI2: a pasta gerada roda no Steam Deck, mas não "
                 "neste PC", "WARNING: this PC's processor lacks AVX2/FMA/BMI2: the built folder runs on the Steam "
                 "Deck, not on this PC"),
}


def tr(key: str, *a) -> str:
    pt, en = TEXT[key]
    return (en if LANG == "en" else pt).format(*a)


LOG = None   # build/logs/forge-<time>.log: everything printed, for the launcher's Report button


def out(line: str) -> None:
    print(line, flush=True)
    if LOG:
        LOG.write(line + "\n")
        LOG.flush()


def step(sid: str, state: str, text: str = "") -> None:
    out(f"@@STEP {sid} {state} {text}".rstrip())


class StepFailed(Exception):
    pass


def run(cmd, cwd=None, env=None, problems=None) -> None:
    """Runs a command, its output going to the log line by line; a non-zero exit fails the step. problems: a list that
    receives the (code, detail) of each "@@PROBLEM <code> <detail>" line the command prints."""
    env = dict(env or os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", WSL_UTF8="1")
    p = subprocess.Popen([str(c) for c in cmd], cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL)
    for raw in iter(p.stdout.readline, b""):
        line = raw.decode("utf-8", "replace").rstrip("\r\n").replace("\x00", "")
        if line.startswith("@@PROBLEM ") and problems is not None:
            problems.append(tuple((line.split(" ", 2) + [""])[1:3]))
        elif line.strip():
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
    # MSYS2's login shell sets TMP and TEMP to /tmp, which native programs get as <msys2>\tmp. A missing folder there
    # (removed by a cleaner, or an MSYS2 copied without it) stops llvm-windres with "Unable to create temp file: No
    # such file or directory" at the Windows build's first step (issue #12), so it is made every time.
    run([msys_root(args) / "usr/bin/bash.exe", "-lc", "mkdir -p /tmp && " + script], cwd=str(ROOT), env=env)


def tool_python(args=None) -> str:
    """The Python with cryptography, lz4 and numpy: this one on Windows (the launcher's embedded Python or MSYS2's),
    the venv on Linux (in the container when the forge uses one)."""
    if not WIN and (VENV_PY.is_file() or (args is not None and args.container)):
        return str(VENV_PY)
    return sys.executable


def box(args) -> list:
    """What a tool command is prefixed with: nothing, or "distrobox enter aoc-recomp --" when the Linux tools live in
    the container (its venv's Python and its compiler only work in there)."""
    return ["distrobox", "enter", CONTAINER, "--"] if args.container else []


def tool(args, script: str, *rest) -> list:
    """Command line of one of our Python tools with the tools' Python, in the container when there is one."""
    return box(args) + [tool_python(args), ROOT / "tools" / script] + list(rest)


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


def cpu_v3():
    """Whether this CPU runs x86-64-v3 code (AVX2, FMA, BMI2: tools/build.py compiles the game with
    -march=x86-64-v3); None when it cannot be told. Without them aoc.exe dies on its first such instruction, before it
    can write a word to its log."""
    if not WIN:
        try:
            flags = next((l.split(":", 1)[1].split() for l in Path("/proc/cpuinfo").read_text().splitlines()
                          if l.startswith("flags")), [])
            return {"avx2", "fma", "bmi2"} <= set(flags)
        except (OSError, StopIteration):
            return None
    try:   # numpy (in the launcher's Python) reads CPUID itself, whatever the Windows version
        try:
            from numpy._core._multiarray_umath import __cpu_features__ as f
        except ImportError:
            from numpy.core._multiarray_umath import __cpu_features__ as f
        if "AVX2" in f and "FMA3" in f:
            return bool(f["AVX2"] and f["FMA3"])
    except Exception:
        pass
    try:   # PF_AVX2_INSTRUCTIONS_AVAILABLE (40): a Windows without it in its table answers "no", hence only a hint
        import ctypes
        return True if ctypes.windll.kernel32.IsProcessorFeaturePresent(40) else None
    except Exception:
        return None


def inventory(args) -> None:
    """tools/extract.py inventory: each package identified by what its NCAs say (title id and version), whatever the
    file is called; an update of another version is refused with its own message."""
    found = []
    try:
        run(tool(args, "extract.py", "inventory", "--game-dir", args.game_dir, "--keys", args.keys), problems=found)
    except StepFailed:
        if found and "p_" + found[0][0] in TEXT:
            raise StepFailed(tr("p_" + found[0][0], found[0][1]))
        raise


# ---- steps

def s_check(args) -> None:
    g = args.game_dir
    if not g.is_dir():
        raise StepFailed(tr("no_dir", g))
    nsps = sorted(g.rglob("*.nsp"))
    out(f"{g}: {len(nsps)} NSP; prod.keys {'ok' if args.keys.is_file() else '--'}")
    if not args.keys.is_file():
        raise StepFailed(tr("missing", "prod.keys"))
    if not nsps:
        raise StepFailed(tr("no_nsp"))
    # The inventory needs cryptography: on Linux only once the venv exists. Until then it runs at the end of the tools
    # step, before anything is extracted, so NSPs renamed without their IDs are not refused here by their names.
    args.inventory_later = not (WIN or VENV_PY.is_file())
    if not args.inventory_later:
        inventory(args)
    elif not (any(BASE_ID in p.name.upper() for p in nsps) and any(UPDATE_ID in p.name.upper() for p in nsps)):
        out(tr("names_later"))
    if args.windows and not WIN:
        raise StepFailed(tr("no_win_linux"))
    if args.send and not args.deck:
        raise StepFailed(tr("send_deck"))
    v3 = cpu_v3()
    if v3 is False and args.windows:
        raise StepFailed(tr("cpu_old"))
    if v3 is False:
        out(tr("cpu_warn"))
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


def immutable_host() -> str:
    """Name of a Linux whose system packages the forge cannot install, '' for any other: SteamOS (Steam Deck, Steam
    Machine: read-only, pacman fails with "unable to lock database", issue #2), Fedora Atomic and what is built on it
    (Bazzite, Silverblue, Kinoite, Bluefin: rpm-ostree, and dnf refuses, issue #18), NixOS."""
    if WIN:
        return ""
    if Path("/run/ostree-booted").exists():
        return "rpm-ostree"
    if Path("/etc/NIXOS").exists():
        return "NixOS"
    try:
        text = Path("/etc/os-release").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    ids = " ".join(l.split("=", 1)[1].strip().strip('"') for l in text.splitlines()
                   if l.startswith(("ID=", "ID_LIKE="))).split()
    return "SteamOS" if "steamos" in ids else ""


def host_has_tools() -> bool:
    """The compiler the Deck build needs is already on this Linux (installed some other way): no container then."""
    return all(shutil.which(t) for t in ("clang", "ld.lld", "llvm-ar", "ninja", "make", "curl"))


def box_exists() -> bool:
    p = capture(["distrobox", "list", "--no-color"])
    names = [l.split("|")[1].strip() for l in p.stdout.decode("utf-8", "replace").splitlines() if l.count("|") >= 3]
    return CONTAINER in names


def tools_box(args) -> None:
    if not shutil.which("distrobox"):
        raise StepFailed(tr("immutable", immutable_host() or "Linux"))
    if not box_exists():
        out(tr("box_make", CONTAINER))
        try:
            run(["distrobox", "create", "--yes", "--name", CONTAINER, "--image", CONTAINER_IMAGE])
        except StepFailed:
            raise StepFailed(tr("box_fail", CONTAINER))
    # The first enter sets the container up (distrobox installs sudo and its own needs: some minutes); then the same
    # setup as the WSL distro, its packages going into the container only.
    run(box(args) + ["bash", ROOT / "tools/setup_wsl.sh", "--minimal"], cwd=str(ROOT))


def s_tools(args) -> str:
    if WIN:
        if args.deck:
            tools_wsl(args)
        if args.windows:
            tools_msys2(args)
    elif args.container:
        tools_box(args)
    else:
        run(["bash", ROOT / "tools/setup_wsl.sh", "--minimal"], cwd=str(ROOT))
    if getattr(args, "inventory_later", False):   # NSPs without IDs in their names (s_check): checked now
        inventory(args)
    out(tr("tools_ok"))
    return "ok"


def s_extract(args) -> str:
    # An ExeFS on disk counts only when its build IDs are the 1.3.0 ones (tools/data/known-builds.json): an earlier
    # attempt with another update leaves one that would be skipped here and fail later, at the code generator.
    exefs = ROOT / "build/v130/exefs"
    inspect = tool(args, "inspect_dump.py", "--exefs", exefs)
    if (exefs / "main").is_file():
        if capture(inspect).returncode == 0:
            return "skip"
        out(tr("stale_exefs"))
    if exefs.is_dir():
        shutil.rmtree(exefs)
    run(tool(args, "extract.py", "exefs", "--game-dir", args.game_dir, "--keys", args.keys))
    try:
        run(inspect)
    except StepFailed:
        shutil.rmtree(exefs, ignore_errors=True)
        raise StepFailed(tr("wrong_build"))
    return "ok"


def romfs_size() -> int:
    """Bytes of the merged 1.3.0 RomFS image (tools/data/known-builds.json); 0 when the table has none."""
    try:
        known = json.loads((ROOT / "tools/data/known-builds.json").read_text(encoding="utf-8"))
        return int(known["builds"]["1.3.0"].get("romfs_image_size", 0))
    except (OSError, ValueError, KeyError):
        return 0


def s_romfs(args) -> str:
    rom, want = ROOT / "build/v130/romfs.bin", romfs_size()
    if rom.is_file():
        if not want or rom.stat().st_size == want:
            return "skip"
        out(tr("stale_romfs", rom.stat().st_size))   # merged with another update by an earlier attempt
        rom.unlink()
        rom.with_name("romfs.bin.sha256").unlink(missing_ok=True)
    run(tool(args, "merge_romfs.py", "--game-dir", args.game_dir, "--keys", args.keys))
    got = rom.stat().st_size if rom.is_file() else 0
    if want and got != want:
        rom.unlink(missing_ok=True)
        raise StepFailed(tr("romfs_size", got, want))
    return "ok"


def s_dlc(args) -> str:
    # finds the DLC NCAs by content, checks their hash trees and skips the images already extracted
    run(tool(args, "extract_dlc.py", "--game-dir", args.game_dir, "--keys", args.keys))
    return "ok"


def link_dlc(dist_romfs: Path) -> None:
    """The extracted DLC images into a game folder's romfs/ (hard links on the same disk)."""
    for src in sorted((ROOT / "build/v130").glob("dlc-*.bin")):
        dst = dist_romfs / src.name
        if dst.exists() and dst.stat().st_size == src.stat().st_size and dst.stat().st_mtime >= src.stat().st_mtime:
            continue
        dst.unlink(missing_ok=True)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
        out(f"  {src.name}")


def s_deck(args) -> str:
    extra = " --with-romfs" if args.with_romfs else ""
    lang = f"AOC_MENU_LANG={LANG}"   # the in-game menu's language in a new aoc.ini: the launcher's (tools/build.py)
    if WIN:
        wsl(args, f"cd {sh_quote(wsl_path(ROOT))} && . ~/.venvs/aoc/bin/activate && "
                  f"{lang} python3 -u tools/build.py --work ~/aoc-build gen guest dist{extra}",
            root=distro(args) == DISTRO)
    else:
        run(box(args) + ["env", lang, tool_python(args), "-u", ROOT / "tools/build.py", "--work",
                         Path.home() / "aoc-build", "gen", "guest", "dist"] + (["--with-romfs"] if args.with_romfs else []),
            cwd=str(ROOT))
    return "ok"


def s_wingen(args) -> str:
    gen = args.win_work / "generated"
    if not args.deck:   # no WSL build: generate the C here (the generator runs on Windows too)
        run([tool_python(args), "-u", ROOT / "tools/build.py", "--work", args.win_work, "gen"], cwd=str(ROOT))
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
    # from "/": ldd resolves like the loader, current folder included, and a shell that keeps the caller's folder
    # (CHERE_INVOKING) would find the launcher's own SDL3.dll there instead of MSYS2's and leave the game without one
    p = capture([msys_root(args) / "usr/bin/bash.exe", "-lc", f"cd / && ldd {sh_quote(msys_path(dist / 'aoc.exe'))}"],
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
    if dst.exists() and dst.stat().st_size != rom.stat().st_size:   # the image of an earlier attempt with another update
        dst.unlink()
    if not dst.exists():
        try:
            os.link(rom, dst)   # same disk: no second 10.9 GiB
            out("romfs.bin: hard link")
        except OSError:
            out("romfs.bin: copy (10.9 GiB)")
            shutil.copy2(rom, dst)
    link_dlc(dist / "romfs")
    # monitor mode (captures of hits, F8 marks, frame dumps on a dark scene; runtime/diag.c), always the current one
    shutil.copy2(ROOT / "tools/windows/monitor.bat", dist / "monitor.bat")
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
    ap.add_argument("--container", action="store_true", default=os.environ.get("AOC_CONTAINER", "") == "1",
                    help=f"Linux: the build tools in the distrobox container {CONTAINER} (automatic on SteamOS, "
                         "Bazzite and other systems that cannot take packages)")
    ap.add_argument("--lang", choices=("pt", "en"), default="pt")
    ap.add_argument("--check-only", action="store_true", help="only the check step")
    ap.add_argument("--prepare", action="store_true",
                    help="setup for a launcher: build for this PC (Windows or Linux), print 'progress <0-1> <text>' lines")
    args = ap.parse_args()
    LANG = args.lang
    args.game_dir = args.game_dir.expanduser()
    args.keys = (args.keys or args.game_dir / "prod.keys").expanduser()
    if args.win_work is None:
        args.win_work = Path("C:/aoc-win") if Path("C:/aoc-win/host").is_dir() else ROOT / "build/win"
    if args.prepare:   # the build for this PC: Windows folder on Windows, Deck/Linux folder on Linux
        args.windows, args.deck = WIN, not WIN
    if not (args.deck or args.windows):
        ap.error("--deck, --windows or both")
    # On Linux dist/aoc-deck is also the game this PC plays (the launcher's Play, RecompLauncher's start): without
    # romfs.bin it has no data. On the same disk it is a hard link, so it costs no space; only the copy to a Deck is big.
    if not WIN and args.deck:
        args.with_romfs = True
    args.container = not WIN and (args.container or (bool(immutable_host()) and not host_has_tools()))
    plan = [("check", s_check), ("tools", s_tools), ("extract", s_extract), ("romfs", s_romfs), ("dlc", s_dlc)]
    if args.deck:
        plan.append(("deck", s_deck))
    if args.windows:
        plan += [("wingen", s_wingen), ("winxlate", s_winxlate), ("winbuild", s_winbuild), ("windist", s_windist)]
    if args.send:
        plan.append(("send", s_send))
    if args.check_only:
        plan = plan[:1]
    global LOG
    logs = ROOT / "build" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    for old in sorted(logs.glob("forge-*.log"))[:-9]:   # keep the last ten
        old.unlink(missing_ok=True)
    LOG = open(logs / time.strftime("forge-%Y%m%d-%H%M%S.log"), "w", encoding="utf-8")
    out(f"AoC Recomp {VERSION}, {' '.join(sys.argv[1:])}")
    for sid, _ in plan:
        out(f"@@PLAN {sid} {tr('t_' + sid)}")
    for n, (sid, fn) in enumerate(plan):
        title = tr("t_" + sid)
        if args.prepare:
            out(f"progress {n / len(plan):.2f} {title}")
        step(sid, "run", title)
        try:
            r = fn(args)
            step(sid, r or "ok", title)
        except StepFailed as e:
            out(f"ERROR: {e}" if LANG == "en" else f"ERRO: {e}")
            step(sid, "fail", str(e))
            out("@@DONE fail")
            if args.prepare:
                print(str(e).replace("\n", " "), file=sys.stderr, flush=True)
            return 1
        except Exception as e:   # anything unexpected still ends the protocol cleanly
            out(tr("unexpected", repr(e)))
            step(sid, "fail", repr(e))
            out("@@DONE fail")
            return 1
    if not args.check_only:
        # What was forged and from which version: the launcher shows the build screen again when VERSION changes
        # (an update unpacked over the folder) and the play screen once the folder for this PC is there.
        state = ROOT / "build" / "forge-state.json"
        old = json.loads(state.read_text(encoding="utf-8")) if state.is_file() else {}
        old.update({"version": VERSION, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        old["deck"] = old.get("deck", False) or args.deck
        old["windows"] = old.get("windows", False) or args.windows
        state.write_text(json.dumps(old, indent=1) + "\n", encoding="utf-8")
    if args.prepare:
        out("progress 1.00 " + tr("folder_ok", ROOT / "dist"))
    out("@@DONE ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

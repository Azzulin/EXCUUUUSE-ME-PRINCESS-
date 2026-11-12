"""Builds the game from the player's own dump, start to finish, for the launcher (launcher/launcher.cpp) or by hand.

Steps (each prints "@@STEP <id> <run|ok|fail|skip> <text>"; every other line is log; the last line is
"@@DONE ok|fail"):

  check     the dump folder (NSPs of the base, update 1.3.0 and DLCs, and prod.keys; tools/extract.py inventory) and
            the tools each target needs (WSL for both, MSYS2 UCRT64 for Windows)
  extract   build/v130/exefs from the update (tools/extract.py exefs), once
  romfs     build/v130/romfs.bin, base + update merged (tools/windows/merge_romfs.ps1 with hactool), once
  deck      dist/aoc-deck: generate the C, compile and assemble in WSL (tools/build.py gen guest host dist)
  wingen    the generated C copied from WSL to the Windows work folder (only the files that changed)
  winxlate  aoc_xlate.exe, the shader translator for Windows (dotnet publish win-x64 in WSL), when it is missing or old
  winbuild  aoc.exe in MSYS2 UCRT64 (tools/build.py guest host)
  windist   dist/aoc-windows: aoc.exe, its DLLs, the translator, exefs/, romfs/ (a hard link), romfs-index.bin
  send      the Deck folder's changed files to the Steam Deck over SSH (tools/deck/deploy.sh --no-build)

Nothing here reads or prints key values: the key file's path goes to the tools that need it.

  python tools/make_build.py --game-dir "D:/dump" --deck --windows [--send] [--with-romfs]
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_ID, UPDATE_ID = "01002B00111A2000", "01002B00111A2800"
MSYS = Path("C:/msys64")


def out(line: str) -> None:
    print(line, flush=True)


def step(sid: str, state: str, text: str = "") -> None:
    out(f"@@STEP {sid} {state} {text}".rstrip())


class StepFailed(Exception):
    pass


def run(cmd, cwd=None, env=None) -> None:
    """Runs a command, its output going to the log line by line; a non-zero exit fails the step."""
    env = dict(env or os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")   # child Pythons print UTF-8 into the pipe
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    for raw in iter(p.stdout.readline, b""):
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line:
            out(line)
    if p.wait():
        raise StepFailed(f"o comando terminou com o código {p.returncode}")


def wsl_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return f"/mnt/{s[0].lower()}{s[2:]}" if len(s) > 1 and s[1] == ":" else s


def msys_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return f"/{s[0].lower()}{s[2:]}" if len(s) > 1 and s[1] == ":" else s


def wsl(args, script: str) -> None:
    cmd = ["wsl"] + (["-d", args.wsl_distro] if args.wsl_distro else []) + ["-e", "bash", "-lc", script]
    run(cmd)


def msys(script: str) -> None:
    env = dict(os.environ, MSYSTEM="UCRT64", CHERE_INVOKING="1")
    run([str(MSYS / "usr/bin/bash.exe"), "-lc", script], cwd=str(ROOT), env=env)


def tool_python() -> str:
    return sys.executable


# ---- steps

def s_check(args) -> None:
    g = args.game_dir
    if not g.is_dir():
        raise StepFailed(f"a pasta do jogo não existe: {g}")
    nsps = sorted(g.rglob("*.nsp"))
    base = [p for p in nsps if BASE_ID in p.name.upper()]
    upd = [p for p in nsps if UPDATE_ID in p.name.upper()]
    keys = args.keys
    out(f"pasta do jogo: {g}")
    out(f"  {len(nsps)} NSP; base {'sim' if base else 'NÃO'}; update 1.3.0 {'sim' if upd else 'NÃO'}; "
        f"chaves {'sim' if keys.is_file() else 'NÃO'}")
    if not base or not upd or not keys.is_file():
        raise StepFailed("faltam a base, o update 1.3.0 ou o prod.keys na pasta escolhida")
    run([tool_python(), str(ROOT / "tools/extract.py"), "inventory", "--game-dir", str(g), "--keys", str(keys)])
    if args.deck or args.windows:
        try:
            subprocess.run(["wsl", "--status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except (OSError, subprocess.CalledProcessError):
            raise StepFailed("o WSL não está instalado (no PowerShell como administrador: wsl --install)")
    if args.windows and not (MSYS / "usr/bin/bash.exe").is_file():
        raise StepFailed("o MSYS2 não está em C:/msys64 (docs/building.md, seção Windows nativo)")
    if args.send and not args.deck:
        raise StepFailed("enviar ao Deck pede a pasta do Deck")


def s_extract(args) -> str:
    if (ROOT / "build/v130/exefs/main").is_file():
        return "skip"
    run([tool_python(), str(ROOT / "tools/extract.py"), "exefs", "--game-dir", str(args.game_dir), "--keys", str(args.keys)])
    run([tool_python(), str(ROOT / "tools/inspect_dump.py"), "--exefs", str(ROOT / "build/v130/exefs")])
    return "ok"


def s_romfs(args) -> str:
    if (ROOT / "build/v130/romfs.bin").is_file():
        return "skip"
    run([tool_python(), str(ROOT / "tools/extract.py"), "hactool-home", "--game-dir", str(args.game_dir), "--keys",
         str(args.keys)])
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tools/windows/merge_romfs.ps1"),
         "-GameDir", str(args.game_dir)])
    return "ok"


def s_deck(args) -> str:
    extra = " --with-romfs" if args.with_romfs else ""
    wsl(args, f"cd '{wsl_path(ROOT)}' && bash tools/setup_wsl.sh && . ~/.venvs/aoc/bin/activate && "
              f"python3 -u tools/build.py --work ~/aoc-build gen guest host dist{extra}")
    return "ok"


def s_wingen(args) -> str:
    gen = f"{wsl_path(args.win_work)}/generated"
    if not args.deck:   # the C comes from WSL; the Deck step made it already
        wsl(args, f"cd '{wsl_path(ROOT)}' && bash tools/setup_wsl.sh && . ~/.venvs/aoc/bin/activate && "
                  f"python3 -u tools/build.py --work ~/aoc-build gen")
    wsl(args, "cd ~/aoc-build/generated && n=0 && while IFS= read -r -d '' f; do d=\"" + gen + "/$f\"; "
              "if ! cmp -s \"$f\" \"$d\"; then mkdir -p \"$(dirname \"$d\")\"; cp \"$f\" \"$d\"; n=$((n+1)); fi; "
              "done < <(find . -type f -print0) && echo \"$n arquivos gerados copiados\"")
    return "ok"


def s_winxlate(args) -> str:
    host = args.win_work / "host"
    host.mkdir(parents=True, exist_ok=True)
    w = wsl_path(host)
    wsl(args, f"cd '{wsl_path(ROOT)}' && . ~/.venvs/aoc/bin/activate && "
              f"( [ -x ~/aoc-build/xlate/aoc_xlate ] || python3 tools/build_xlate.py --out ~/aoc-build/xlate "
              f"--sysroot ~/aoc-build/toolchain/sniper ) && "
              f"if [ -f '{w}/aoc_xlate.exe' ] && cmp -s ~/aoc-build/xlate/aoc_xlate.id '{w}/aoc_xlate.id'; then "
              f"echo 'tradutor do Windows em dia'; else B=~/aoc-build/xlate && rm -rf /tmp/aoc-xlwin && "
              f"dotnet publish \"$B/xlate/aoc_xlate.csproj\" -c Release -r win-x64 --self-contained -p:PublishAot=false "
              f"-p:PublishSingleFile=true -p:InvariantGlobalization=true -p:RyuSrc=\"$B/ryujinx\" -o /tmp/aoc-xlwin "
              f"| tail -2 && cp /tmp/aoc-xlwin/aoc_xlate.exe '{w}/' && cp \"$B/aoc_xlate.id\" '{w}/'; fi")
    return "ok"


def s_winbuild(args) -> str:
    msys(f"python3 -u tools/build.py --work '{msys_path(args.win_work)}' --big-jobs 2 guest host")
    return "ok"


def s_windist(args) -> str:
    src, dist = args.win_work / "host", ROOT / "dist/aoc-windows"
    (dist / "exefs").mkdir(parents=True, exist_ok=True)
    (dist / "romfs").mkdir(exist_ok=True)

    def copy(a: Path, b: Path) -> None:
        if not a.is_file():
            raise StepFailed(f"falta {a}")
        if b.exists() and b.stat().st_size == a.stat().st_size and b.stat().st_mtime >= a.stat().st_mtime:
            return
        shutil.copy2(a, b)

    for f in ("aoc.exe", "aoc_xlate.exe", "aoc_xlate.id", "romfs-index.bin"):
        copy(src / f, dist / f)
    # the DLLs aoc.exe imports from MSYS2 (SDL3, libopus and what they pull in)
    p = subprocess.run([str(MSYS / "usr/bin/bash.exe"), "-lc", f"ldd '{msys_path(dist / 'aoc.exe')}'"],
                       env=dict(os.environ, MSYSTEM="UCRT64"), capture_output=True, text=True)
    dlls = [l.split("=>")[1].split("(")[0].strip() for l in p.stdout.splitlines() if "/ucrt64/" in l]
    for d in dlls:
        win = MSYS / d.lstrip("/")
        copy(win, dist / win.name)
        out(f"  {win.name}")
    for f in ("main", "subsdk0", "sdk", "main.npdm"):
        copy(ROOT / "build/v130/exefs" / f, dist / "exefs" / f)
    rom, dst = ROOT / "build/v130/romfs.bin", dist / "romfs/romfs.bin"
    if not dst.exists():
        try:
            os.link(rom, dst)   # same disk: no second 10.9 GiB
            out("romfs.bin ligado (hard link)")
        except OSError:
            out("copiando romfs.bin (10,9 GiB)")
            shutil.copy2(rom, dst)
    ini = dist / "aoc.ini"
    if not ini.exists():
        ini.write_text("# Configurações do AoC Recomp. O menu (F1) grava aqui.\n[menu]\nmenu_lang = pt-BR\n", encoding="utf-8")
    out(f"pasta pronta: {dist}")
    return "ok"


def s_send(args) -> str:
    bash = Path("C:/Program Files/Git/bin/bash.exe")
    if not bash.is_file():
        raise StepFailed("o Git Bash não está em C:/Program Files/Git (o envio usa ssh e scp dele)")
    env = dict(os.environ)
    if args.deck_host:
        env["AOC_DECK"] = args.deck_host
    run([str(bash), str(ROOT / "tools/deck/deploy.sh"), "--no-build"], cwd=str(ROOT), env=env)
    return "ok"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # the launcher reads UTF-8
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game-dir", type=Path, default=ROOT / "Game Files", help="pasta com os NSPs e o prod.keys")
    ap.add_argument("--keys", type=Path, help="arquivo de chaves (padrão: prod.keys na pasta do jogo)")
    ap.add_argument("--deck", action="store_true", help="pasta para o Steam Deck (dist/aoc-deck)")
    ap.add_argument("--windows", action="store_true", help="versão para Windows (dist/aoc-windows)")
    ap.add_argument("--with-romfs", action="store_true", help="Deck: pôr também o romfs.bin (primeira instalação)")
    ap.add_argument("--send", action="store_true", help="enviar ao Deck por SSH no fim")
    ap.add_argument("--deck-host", default="", help="usuário@endereço do Deck (padrão: o de tools/deck/deploy.sh)")
    ap.add_argument("--win-work", type=Path, default=Path("C:/aoc-win") if Path("C:/aoc-win").is_dir() else ROOT / "build/win",
                    help="pasta de trabalho do build do Windows")
    ap.add_argument("--check-only", action="store_true", help="só o passo check")
    ap.add_argument("--wsl-distro", default=os.environ.get("AOC_WSL_DISTRO", ""), help="distro do WSL (padrão: a padrão)")
    args = ap.parse_args()
    args.keys = args.keys or args.game_dir / "prod.keys"
    if not (args.deck or args.windows):
        ap.error("escolha --deck, --windows ou os dois")
    plan = [("check", "Conferir arquivos e ferramentas", s_check), ("extract", "Extrair o código do jogo", s_extract),
            ("romfs", "Montar o RomFS 1.3.0", s_romfs)]
    if args.deck:
        plan.append(("deck", "Compilar para o Steam Deck", s_deck))
    if args.windows:
        plan += [("wingen", "Trazer o código gerado", s_wingen), ("winxlate", "Tradutor de shaders do Windows", s_winxlate),
                 ("winbuild", "Compilar para o Windows", s_winbuild), ("windist", "Montar a pasta do Windows", s_windist)]
    if args.send:
        plan.append(("send", "Enviar ao Steam Deck", s_send))
    if args.check_only:
        plan = plan[:1]
    for sid, title, _ in plan:
        out(f"@@PLAN {sid} {title}")
    for sid, title, fn in plan:
        step(sid, "run", title)
        try:
            r = fn(args)
            step(sid, r or "ok", title)
        except StepFailed as e:
            out(f"ERRO: {e}")
            step(sid, "fail", str(e))
            out("@@DONE fail")
            return 1
        except Exception as e:   # anything unexpected still ends the protocol cleanly
            out(f"ERRO inesperado: {e!r}")
            step(sid, "fail", repr(e))
            out("@@DONE fail")
            return 1
    out("@@DONE ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

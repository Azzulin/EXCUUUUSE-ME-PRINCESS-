"""Mescla o RomFS da base 1.0.0 com o patch BKTR do update 1.3.0 usando o hactool: build/v130/romfs.bin.

Mesmo processo de tools/windows/merge_romfs.ps1, em Python para rodar no Windows e no Linux (o launcher usa este):

  python tools/merge_romfs.py [--game-dir "Game Files"] [--keys <prod.keys>]

1. prepara build/v130/tmp/hactool-home/.switch/{prod,title}.keys (tools/extract.py hactool-home; valores nunca exibidos);
2. liga (hardlink) os NSPs da base e do update com nomes ASCII (o hactool do Windows não abre caminhos Unicode);
3. extrai os NCAs dos dois NSPs (~11 GB temporários) e mescla a seção 1 do NCA de programa do update (BKTR) sobre a
   base, verificando os seis níveis IVFC (-y);
4. apaga os temporários e as chaves copiadas só se a imagem existir.

Precisa de ~23 GB livres durante a mescla (NCAs temporários + a imagem de 10,9 GiB). O hactool vem de
prebuilt/hactool/ (pacote do launcher) ou de toolchain/hactool-1.4.0-win/ (desenvolvimento no Windows).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "v130"
TMP = WORK / "tmp"
HAC_HOME = TMP / "hactool-home"
OUT = WORK / "romfs.bin"
LOG = WORK / "merge.log"
BASE_ID, UPDATE_ID = "01002B00111A2000", "01002B00111A2800"
WIN = os.name == "nt"


def fail(msg: str) -> None:
    print(f"ERRO: {msg}", flush=True)
    sys.exit(1)


def hactool() -> Path:
    cands = ([ROOT / "prebuilt/hactool/win-x64/hactool.exe", ROOT / "toolchain/hactool-1.4.0-win/hactool.exe"] if WIN
             else [ROOT / "prebuilt/hactool/linux-x64/hactool", ROOT / "toolchain/hactool-1.4.0-linux/hactool"])
    for c in cands:
        if c.is_file():
            if not WIN:
                c.chmod(0o755)
            return c
    found = shutil.which("hactool")
    if found:
        return Path(found)
    fail("hactool não encontrado (" + ", ".join(str(c) for c in cands) + ")")


def find_nsp(game_dir: Path, tid: str, base: bool) -> Path:
    for p in sorted(game_dir.rglob("*.nsp")):
        n = p.name.upper()
        if tid in n and (not base or "BASE" in n or "[V0]" in n):
            return p
    fail(f"NSP {tid} não encontrado em {game_dir}")


def link_or_copy(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.link(src, dst)   # mesmo disco: não copia nada
        return
    except OSError:
        pass
    if not WIN:   # outro disco (ex.: o dump em /mnt/c no WSL): o hactool do Linux abre qualquer caminho
        os.symlink(src, dst)
        return
    print(f"hardlink falhou; copiando {dst.name} (pode demorar)...", flush=True)
    shutil.copyfile(src, dst)


def run_hactool(args: list, env=None, log=None) -> int:
    p = subprocess.run([str(hactool())] + args, env=env, stdout=log or subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game-dir", type=Path, default=ROOT / "Game Files")
    ap.add_argument("--keys", type=Path, help="padrão: prod.keys na pasta do jogo")
    args = ap.parse_args()
    keys = args.keys or args.game_dir / "prod.keys"
    if OUT.exists():
        print(f"{OUT} já existe; apague-o para refazer")
        return 0
    hac = hactool()
    print(f"hactool: {hac}", flush=True)

    # 1. chaves para o hactool (o extract.py nunca imprime valores)
    subprocess.run([sys.executable, str(ROOT / "tools/extract.py"), "hactool-home", "--game-dir", str(args.game_dir),
                    "--keys", str(keys)], check=True)
    if not (HAC_HOME / ".switch" / "title.keys").is_file():
        fail("o extract.py hactool-home não criou as chaves")

    # 2. NSPs com nomes ASCII
    inp = TMP / "in"
    inp.mkdir(parents=True, exist_ok=True)
    link_or_copy(find_nsp(args.game_dir, BASE_ID, True), inp / "base.nsp")
    link_or_copy(find_nsp(args.game_dir, UPDATE_ID, False), inp / "update.nsp")

    # 3. NCAs dos dois NSPs (a base tem ~11 GB) e a mescla
    for name in ("base", "update"):
        d = TMP / name
        if not d.is_dir():
            print(f"Extraindo {name}.nsp ...", flush=True)
            if run_hactool(["-t", "pfs0", f"--outdir={d}", str(inp / f"{name}.nsp")]):
                fail(f"hactool falhou ao abrir {name}.nsp")
    base_nca = max((TMP / "base").glob("*.nca"), key=lambda p: p.stat().st_size)
    upd_nca = max((TMP / "update").glob("*.nca"), key=lambda p: p.stat().st_size)
    print(f"NCA de programa da base:   {base_nca.name}")
    print(f"NCA de programa do update: {upd_nca.name}", flush=True)

    # Para seção BKTR o hactool ignora --romfs; só --section1 grava a imagem (o nível RomFS final, sem os níveis de
    # hash). -y verifica os seis níveis IVFC.
    print("Mesclando o RomFS (base + 1.3.0); leva alguns minutos ...", flush=True)
    env = dict(os.environ, HOME=str(HAC_HOME), USERPROFILE=str(HAC_HOME))
    with open(LOG, "wb") as log:
        code = run_hactool(["-x", "-y", "--disablekeywarns", "--suppresskeys", "-k",
                            str(HAC_HOME / ".switch" / "prod.keys"), f"--basenca={base_nca}", f"--section1={OUT}",
                            str(upd_nca)], env=env, log=log)
    text = LOG.read_text(encoding="utf-8", errors="replace")
    # As assinaturas RSA da Nintendo (fixed-key, NPDM, ACID) não dizem nada sobre os dados: o hactool.exe da release
    # as marca GOOD e o compilado no Linux (tools/build_hactool_linux.sh) FAIL. A integridade são os seis níveis IVFC.
    checked = "\n".join(l for l in text.splitlines() if not re.search(r"Signature \(FAIL\)", l))
    levels = sum(1 for i in range(6) if f"Level {i} (GOOD)" in text)
    if code or re.search(r"\(FAIL\)|\(INVALID\)|Failed to|Error:", checked) or levels != 6:
        OUT.unlink(missing_ok=True)
        fail(f"a mesclagem não verificou (código {code}, níveis IVFC bons: {levels}/6). Veja {LOG}")
    if not OUT.is_file() or OUT.stat().st_size < 2**30:
        fail(f"o hactool verificou mas não gravou {OUT}. NCAs mantidos em {TMP} para nova tentativa. Veja {LOG}")

    # 4. limpeza: NCAs temporários, links e as chaves copiadas
    for d in (TMP / "base", TMP / "update", inp, HAC_HOME):
        shutil.rmtree(d, ignore_errors=True)
    print(f"OK: {OUT} ({OUT.stat().st_size / 2**30:.2f} GiB), seis níveis IVFC verificados.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

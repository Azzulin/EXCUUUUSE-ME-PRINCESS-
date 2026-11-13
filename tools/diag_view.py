#!/usr/bin/env python3
"""Lê o aoc.log e explica, em português, os relatórios do gravador de estado (runtime/diag.c).

Uso:
    python tools/diag_view.py                      # dist/aoc-windows/logs/aoc.log
    python tools/diag_view.py <aoc.log> [--threads] [--rows N]

Para cada relatório (sem present por AOC_HANG_SECS, imagem preta por AOC_BLACK_SECS com o jogo apresentando, ou F8)
mostra a linha do tempo dos segundos anteriores, o estado da thread principal e das que seguram ou esperam um núcleo
virtual, quem é o dono do lock que a principal espera e um veredito. Também lê o bloco "hang:" dos logs antigos (antes
do gravador) e, no fim, resume o que tirou conteúdo da imagem (draws pulados, listas lidas como zero).
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "dist" / "aoc-windows" / "logs" / "aoc.log"

RE_THREAD = re.compile(
    r"(?:hang|diag):  thread (0x[0-9a-f]+) prio (\d+)( main)?( render)? core (-?\d+)(?: mask (0x[0-9a-f]+|0))? host (\d+) "
    r"(\w+) addr (0x[0-9a-f]+|0)(?: =(0x[0-9a-f]+|0))? key (0x[0-9a-f]+|0) obj (0x[0-9a-f]+|0) spin (\d+) at (0x[0-9a-f]+|0)")
RE_PC = re.compile(r"(?:hang|diag):    pc (0x[0-9a-f]+)(?: 0x[0-9a-f]+)?(?: \(([^)]+)\))? lr (0x[0-9a-f]+)(?: 0x[0-9a-f]+)?(?: \(([^)]+)\))?")
RE_CHAIN = re.compile(r"(?:hang|diag):    called from (.*)")
RE_OWNERS = re.compile(r"core owners (0x[0-9a-f]+|0) (0x[0-9a-f]+|0) (0x[0-9a-f]+|0); waiting for a core \(handle/prio\):(.*?)(?:; (\d+) owners moved|$)")
RE_ROW = re.compile(
    r"diag:  t\s+([\d.]+) frame\s+(\d+) presents\s+(\d+) luma\s+(-?\d+) lit\s+(-?\d+) draws\s+(\d+) audio ([\d.]+) "
    r"read\s+(\d+) KiB skipped (\d+)/(\d+) zero (\d+) movies (\d+) main (\S+)\s+cores (\d+)(?: hits (\d+))?")

WAIT_PT = {"run": "rodando", "lock": "esperando um lock", "condvar": "esperando uma variável de condição",
           "address": "esperando num endereço (árbitro)", "sync": "esperando objetos do kernel"}


class Thread:
    def __init__(self, m):
        self.handle = int(m.group(1), 16)
        self.prio = int(m.group(2))
        self.main = bool(m.group(3))
        self.render = bool(m.group(4))
        self.core = int(m.group(5))
        self.mask = int(m.group(6), 16) if m.group(6) else None
        self.host = int(m.group(7))
        self.kind = m.group(8)
        self.addr = int(m.group(9), 16)
        self.word = int(m.group(10), 16) if m.group(10) else None
        self.spin = int(m.group(13))
        self.spin_at = int(m.group(14), 16)
        self.pc = self.lr = ""
        self.chain = ""

    def where(self):
        return self.pc or "?"

    def name(self):
        return f"{self.handle:#x}" + (" (principal)" if self.main else "") + (" (render)" if self.render else "")


class Report:
    def __init__(self, why, line_no):
        self.why = why
        self.line_no = line_no
        self.rows = []
        self.tables = []      # each: {"owners": [...], "waiters": str, "moved": int|None, "threads": [Thread]}
        self.extra = []       # movie decoders, picture copies, image totals


def parse(lines):
    reports, image, events, cur, table, last_thread = [], [], [], None, None, None
    for no, raw in enumerate(lines, 1):
        t = raw.rstrip("\n")
        t = t[7:] if t.startswith("[host] ") else t
        m = re.match(r"diag: report \d+: (.*?); ([\d.]+) s after the game started, frame (\d+)", t)
        if m:
            cur = Report(f"{m.group(1)} (aos {float(m.group(2)):.0f} s de jogo, frame {m.group(3)})", no)
            reports.append(cur)
            table = None
            continue
        m = re.match(r"hang: no present for ([\d.]+) s; guest threads", t)   # logs de antes do gravador
        if m:
            cur = Report(f"sem present por {m.group(1)} s (log antigo, sem linha do tempo)", no)
            reports.append(cur)
            table = None
            continue
        if t.startswith("diag: still no present"):
            table = None      # a segunda tabela do mesmo relatório
            continue
        if t.startswith("diag: image:") or "zero view" in t or t.startswith("vk: texel buffer views:"):
            image.append(t)
        if t.startswith("diag: hit ") or t.startswith("diag: mark ") or t.startswith("vk_dump: frame"):
            events.append(t)
        if cur is None:
            continue
        m = RE_ROW.match(t)
        if m:
            g = m.groups()   # t, frame, presents, luma, lit, draws, audio, KiB, skip pipe, skip shader, zero, movies, main, cores
            cur.rows.append([float(g[0])] + [int(x) for x in g[1:6]] + [float(g[6])] + [int(x) for x in g[7:12]]
                            + [g[12], int(g[13]), int(g[14] or 0)])
            continue
        m = RE_OWNERS.search(t)
        if m and (t.startswith("hang:") or t.startswith("diag:")):
            table = {"owners": [int(m.group(i), 16) for i in (1, 2, 3)], "waiters": m.group(4).strip(),
                     "moved": int(m.group(5)) if m.group(5) else None, "threads": []}
            cur.tables.append(table)
            continue
        m = RE_THREAD.match(t)
        if m and table is not None:
            last_thread = Thread(m)
            table["threads"].append(last_thread)
            continue
        m = RE_PC.match(t)
        if m and last_thread is not None:
            last_thread.pc = m.group(2) or m.group(1)
            last_thread.lr = m.group(4) or m.group(3)
            continue
        m = RE_CHAIN.match(t)
        if m and last_thread is not None:
            last_thread.chain = m.group(1)
            continue
        if t.startswith("diag: movie decoders:") or t.startswith("diag: image totals") or "picture copies" in t:
            cur.extra.append(t[6:])
        if t.startswith("diag: end of report"):
            cur, table = None, None
    return reports, image, events


def lock_owner(word, threads):
    """A palavra de um mutex do Horizon guarda o handle do dono nos 30 bits baixos (bit 30: há quem espere)."""
    if word is None:
        return None
    h = word & 0x3FFFFFFF
    return next((t for t in threads if t.handle == h), None)


def a64_hint(where):
    m = re.match(r"main\+0x([0-9a-f]+)", where or "")
    return f"python C:\\aoc-win\\a64.py main 0x{max(int(m.group(1), 16) - 0x40, 0):x} 48" if m else None


def verdict(rep):
    out = []
    if not rep.tables:
        return ["sem tabela de threads neste relatório"]
    tb = rep.tables[0]
    threads = tb["threads"]
    by = {t.handle: t for t in threads}
    main = next((t for t in threads if t.main), None)
    free = [i for i, o in enumerate(tb["owners"]) if not o]
    waiters = re.findall(r"(0x[0-9a-f]+)/(\d+)", tb["waiters"])
    black = rep.rows and ("black" in rep.why or "dark picture" in rep.why)

    if waiters and free:
        out.append(f"TRAVADA DE NÚCLEO VIRTUAL: {len(waiters)} thread(s) esperam um núcleo com o(s) núcleo(s) "
                   f"{', '.join(map(str, free))} livre(s) — elas só podem rodar num núcleo ocupado (afinidade).")
        for i, o in enumerate(tb["owners"]):
            t = by.get(o)
            if t and any(by.get(int(h, 16)) and (by[int(h, 16)].mask is None or by[int(h, 16)].mask >> i & 1) for h, _ in waiters):
                how = "em código do jogo, sem chamada de host" if t.host == 0 else f"numa chamada de host (profundidade {t.host})"
                out.append(f"  núcleo {i}: thread {t.name()} prio {t.prio} {how}, pc {t.where()}, lr {t.lr}"
                           + (f"; laço de espera ativa em {t.spin_at:#x} ({t.spin} voltas)" if t.spin else ""))
                if t.chain:
                    out.append(f"    chamada por: {t.chain}")
                hint = a64_hint(t.lr) or a64_hint(t.pc)
                if hint:
                    out.append(f"    desmontar: {hint}")
        if tb["moved"] is not None:
            out.append(f"  migrações para núcleo livre até aqui: {tb['moved']} (core_rebalance; 0 = a migração não agiu)")
    elif waiters:
        out.append(f"{len(waiters)} thread(s) esperando núcleo com os três ocupados: {tb['waiters']}")

    if main:
        if main.core >= 0:
            st = "rodando código do jogo" if main.host == 0 else f"dentro de uma chamada de host (profundidade {main.host})"
            out.append(f"Thread principal: com o núcleo {main.core}, {st}; pc {main.where()}, lr {main.lr}")
        elif main.kind == "run" and not any(int(h, 16) == main.handle for h, _ in waiters):
            out.append(f"Thread principal: fora dos núcleos numa chamada de host (dormindo ou esperando o host; "
                       f"profundidade {main.host}); lr {main.lr}")
        elif main.kind == "run":
            out.append(f"Thread principal: pronta para rodar, SEM núcleo virtual (máscara {main.mask if main.mask is None else hex(main.mask)}); lr {main.lr}")
        else:
            out.append(f"Thread principal: {WAIT_PT.get(main.kind, main.kind)} em {main.addr:#x}; pc {main.where()}, lr {main.lr}")
            if main.kind == "lock":
                o = lock_owner(main.word, threads)
                if o:
                    out.append(f"  dono do lock: thread {o.name()} — {WAIT_PT.get(o.kind, o.kind)}"
                               + (f" em {o.addr:#x}" if o.kind != "run" else f", núcleo {o.core}") + f"; pc {o.where()}, lr {o.lr}")
                    if o.chain:
                        out.append(f"    chamada por: {o.chain}")
                    if o.kind == "lock" and lock_owner(o.word, threads) is main:
                        out.append("  DEADLOCK: o dono espera um lock que a principal segura.")
        if main.chain:
            out.append(f"  chamada por: {main.chain}")

    runners = [t for t in threads if t.core >= 0 and not t.main]
    for t in runners:
        if not (waiters and free):
            out.append(f"Com núcleo: thread {t.name()} prio {t.prio}, " + ("código do jogo" if t.host == 0 else "chamada de host")
                       + f", pc {t.where()}, lr {t.lr}" + (f"; espera ativa em {t.spin_at:#x}" if t.spin else ""))

    if len(rep.tables) > 1:
        second = {t.handle: t for t in rep.tables[1]["threads"]}
        moved = [t for t in threads if t.handle in second and (second[t.handle].pc != t.pc or second[t.handle].spin != t.spin
                                                                 or second[t.handle].kind != t.kind)]
        same = [t for t in threads if t.core >= 0 and t not in moved]
        out.append("Segunda tabela (travada continuou): " + (f"{len(moved)} thread(s) mudaram de lugar: "
                   + ", ".join(f"{t.handle:#x}" for t in moved[:8]) if moved else "nenhuma thread mudou de lugar")
                   + ("; paradas no mesmo ponto com núcleo: " + ", ".join(f"{t.handle:#x}" for t in same) if same else ""))

    if rep.rows:
        last = rep.rows[-8:]
        presents = sum(r[2] for r in last) / len(last)
        draws = sum(r[5] for r in last) / len(last)
        audio = max(r[6] for r in last)
        read = sum(r[7] for r in last)
        lumas = [r[3] for r in rep.rows if r[3] >= 0]
        went = None
        for a, r in zip(rep.rows, rep.rows[1:]):   # a última passagem de imagem acesa para preta
            if a[4] >= 2 > r[4] >= 0:
                went = r
        out.append(f"Últimos {len(last)} s: {presents:.0f} presents/s, {draws:.0f} draws por frame, pico de áudio {audio:.3f}, "
                   f"{read} KiB lidos do RomFS, vídeos ativos {last[-1][11]}.")
        if went:
            out.append(f"A imagem ficou preta aos {went[0]:.0f} s (frame {went[1]}); luma antes: "
                       f"{', '.join(str(x) for x in lumas[-12:])}.")
        if black:
            if "dark picture" in rep.why:
                out.append("ESCURO COM A CENA SENDO DESENHADA: comparar a imagem em logs/diag/marks/ e o despejo do "
                           "frame (passes.txt: exposição, tonemap, fade) com um frame normal.")
            elif draws < 30:
                out.append("PRETO COM POUCOS DRAWS: o jogo apresenta mas quase não desenha — ele mesmo está numa tela "
                           "preta (fade ou espera); ver o que a principal e as workers esperam acima.")
            else:
                out.append("PRETO COM A CENA SENDO DESENHADA: o jogo desenha e a imagem sai preta — suspeita no "
                           "caminho gráfico (um passe final, exposição ou fade lendo zero), não numa espera do jogo.")
            if presents and audio == 0:
                out.append("Sem áudio nesses segundos: o som também parou.")
    return out


def show(rep, args):
    print(f"\n=== Relatório (linha {rep.line_no} do log): {rep.why} ===")
    if rep.rows:
        rows = rep.rows[-args.rows:]
        print("   t(s)   frame  pres luma  lit draws/f áudio  KiB-lidos pulados zero vídeos principal núcleos golpes")
        for r in rows:
            print(f" {r[0]:7.1f} {r[1]:7d} {r[2]:4d} {r[3]:4d} {r[4]:4d} {r[5]:6d} {r[6]:6.3f} {r[7]:9d} {r[8]:4d}/{r[9]:<3d}"
                  f" {r[10]:3d} {r[11]:5d}  {r[12]:<9s} {r[13]:4d} {r[14]:6d}")
    for e in rep.extra:
        print("  " + e)
    print("Leitura:")
    for v in verdict(rep):
        print("  " + v)
    if args.threads and rep.tables:
        print("Threads (fora as paradas em condvar sem laço de espera):")
        for t in rep.tables[0]["threads"]:
            if t.kind == "condvar" and not t.main and t.core < 0:
                continue
            print(f"  {t.name()} prio {t.prio} núcleo {t.core} host {t.host} {t.kind} addr {t.addr:#x} pc {t.where()} lr {t.lr}")
            if t.chain:
                print(f"      {t.chain}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("log", nargs="?", default=str(DEFAULT))
    ap.add_argument("--threads", action="store_true", help="lista as threads que não estão ociosas")
    ap.add_argument("--rows", type=int, default=20, help="linhas da linha do tempo (padrão 20)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = Path(args.log)
    if not p.is_file():
        sys.exit(f"não achei {p}")
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    reports, image, events = parse(lines)
    on = any("diag: state recorder on" in x for x in lines)
    print(f"{p}: {len(lines)} linhas; gravador de estado {'ligado' if on else 'ausente (binário antigo)'}; "
          f"{len(reports)} relatório(s)")
    for rep in reports:
        show(rep, args)
    print(f"\n=== Golpes, marcas e despejos de frame ({len(events)}) ===")
    for t in events[:60]:
        print("  " + t)
    if not events:
        print("  nenhum (golpes só são capturados com AOC_HIT_SHOTS; ver tools/windows/monitor.bat)")
    print("\n=== Imagem: conteúdo perdido ===")
    if image:
        for t in image[-12:]:
            print("  " + t)
    else:
        print("  nenhuma linha de draws pulados ou de listas lidas como zero")
    return 0


if __name__ == "__main__":
    sys.exit(main())

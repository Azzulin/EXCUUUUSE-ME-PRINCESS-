#!/usr/bin/env python3
"""Lê o registro de desempenho de uma sessão jogada (runtime/diag.c: logs/desempenho/<início>.csv, uma linha por
segundo) e diz onde o jogo perde tempo, em português.

Uso:
    python tools/perf_view.py                       # a sessão mais nova de dist/aoc-windows ou dist/aoc-deck
    python tools/perf_view.py <arquivo.csv | pasta logs/desempenho> [--linhas] [--todas N]

Mostra: duração, fps médio, quanto tempo ficou abaixo de 28 e de 25 fps, o 1 % mais lento, as engasgadas (segundos
com um frame acima de 50 ms) agrupadas e com a causa de cada uma, o que pesa nos segundos lentos (tradução de shader,
montagem de pipeline, upload de textura, replay, espera da GPU, CPU do jogo), consumo e temperaturas, e o que
aconteceu em volta de cada marca ("Marcar este momento" no menu rápido ou F8). Só a biblioteca padrão.
"""
import argparse
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CAUSES = [("worst_xlate", "tradução de shader"), ("worst_pipe", "montagem de pipeline"),
          ("worst_tex", "upload de textura"), ("worst_replay", "replay NVN→Vulkan"),
          ("worst_fence", "espera da GPU"), ("worst_pace", "ritmo (espera de vsync)")]


def newest_csv(arg):
    if arg:
        p = Path(arg)
        if p.is_dir():
            files = sorted(p.glob("*.csv"))
            return files[-1] if files else None
        return p
    files = []
    for d in ("aoc-windows", "aoc-deck"):
        files += (ROOT / "dist" / d / "logs" / "desempenho").glob("*.csv")
    here = Path("logs/desempenho")
    if here.is_dir():
        files += here.glob("*.csv")
    return max(files, key=lambda f: f.stat().st_mtime) if files else None


def num(r, k, default=0.0):
    try:
        return float(r.get(k, "") or default)
    except ValueError:
        return default


def load(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [l for l in f if not l.startswith("#")]
    return list(csv.DictReader(lines))


def cause_of(r):
    """The biggest measured part of the slowest frame of that second; what is left over is the game's own CPU."""
    worst = num(r, "worst_ms")
    parts = [(num(r, k), name) for k, name in CAUSES]
    known = sum(v for v, _ in parts)
    parts.append((max(worst - known, 0.0), "CPU do jogo / outra thread"))
    v, name = max(parts)
    return name, v


def fmt_t(s):
    s = int(s)
    return f"{s // 60:3d}:{s % 60:02d}"


def bound(r):
    """What held a slow second back: GPU (busy near 100 %), waiting on the GPU (fences), or CPU."""
    busy, fence = num(r, "gpu_busy", -1), num(r, "fence_ms")
    if busy >= 90:
        return "GPU"
    if fence >= 8:
        return "espera GPU"
    return "CPU"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv", nargs="?", help="arquivo .csv ou a pasta logs/desempenho")
    ap.add_argument("--linhas", action="store_true", help="lista todos os segundos abaixo de 28 fps")
    ap.add_argument("--todas", type=int, default=15, help="quantas engasgadas listar (padrão 15)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path = newest_csv(args.csv)
    if not path or not path.is_file():
        sys.exit("nenhum registro de desempenho encontrado (logs/desempenho/*.csv); jogue uma sessão com a versão 0.1.3+")
    rows = load(path)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("# settings:"):
                print("configurações:" + line[len("# settings:"):].rstrip())
            if not line.startswith("#"):
                break
    play =[r for r in rows if num(r, "game_s", -1) >= 0 and num(r, "fps") > 0]
    print(f"{path}: {len(rows)} segundos gravados, {len(play)} de jogo (relógio do jogo rodando)")
    if not play:
        return 0

    fps = [num(r, "fps") for r in play]
    worst = sorted((num(r, "worst_ms") for r in play), reverse=True)
    low28 = sum(1 for v in fps if v < 28)
    low25 = sum(1 for v in fps if v < 25)
    p95 = worst[len(worst) // 20]   # 95 % of the seconds have their slowest frame at or under this
    print(f"\n== Resumo ==")
    print(f"  duração de jogo {fmt_t(len(play)).strip()} min:s; fps médio {statistics.mean(fps):.1f}; "
          f"{low28} s abaixo de 28 fps ({100 * low28 / len(play):.1f} %), {low25} s abaixo de 25 ({100 * low25 / len(play):.1f} %)")
    print(f"  pior frame {worst[0]:.0f} ms; em 95 % dos segundos o frame mais lento fica em até {p95:.0f} ms; "
          f"frames acima de 50 ms: {int(sum(num(r, 'over50') for r in play))}")

    # what the slow seconds cost, by cause and by side
    slow = [r for r in play if num(r, "fps") < 28 or num(r, "worst_ms") > 50]
    if slow:
        by_cause, by_side = {}, {}
        for r in slow:
            c, _ = cause_of(r)
            by_cause[c] = by_cause.get(c, 0) + 1
            b = bound(r)
            by_side[b] = by_side.get(b, 0) + 1
        print(f"\n== O que segura os {len(slow)} segundos lentos ==")
        for c, n in sorted(by_cause.items(), key=lambda x: -x[1]):
            print(f"  {n:5d} s  {c}")
        print("  lado: " + ", ".join(f"{k} {v} s" for k, v in sorted(by_side.items(), key=lambda x: -x[1]))
              + "  (GPU: carga ≥ 90 %; espera GPU: frames esperando a GPU; CPU: o resto)")
        xl = sum(num(r, "xlated") for r in play)
        pipes = sum(num(r, "pipes") for r in play)
        skips = sum(num(r, "skip_pipe") + num(r, "skip_shader") for r in play)
        print(f"  na sessão: {xl:.0f} shaders traduzidos, {pipes:.0f} pipelines montados, {skips:.0f} draws pulados "
              f"esperando shader/pipeline, {sum(num(r, 'tex_up') for r in play):.0f} texturas enviadas")
        avg = lambda k: statistics.mean(num(r, k) for r in slow)
        print(f"  média nos segundos lentos, por frame: replay {avg('replay_ms'):.1f} ms, espera da GPU "
              f"{avg('fence_ms'):.1f} ms, textura {avg('tex_ms'):.1f} ms, draws {avg('draws'):.0f}, "
              f"núcleos do jogo {avg('game_cores'):.2f}, GPU {avg('gpu_busy'):.0f} %")
        normal = [r for r in play if r not in slow]
        if normal:
            n_avg = lambda k: statistics.mean(num(r, k) for r in normal)
            print(f"  nos segundos normais: replay {n_avg('replay_ms'):.1f} ms, espera da GPU {n_avg('fence_ms'):.1f} ms, "
                  f"draws {n_avg('draws'):.0f}, núcleos do jogo {n_avg('game_cores'):.2f}, GPU {n_avg('gpu_busy'):.0f} %")

    # stutters: seconds with a frame over 50 ms, merged when consecutive
    events, cur = [], None
    for r in play:
        if num(r, "worst_ms") > 50:
            t = num(r, "t_s")
            if cur and t - cur[-1][0] <= 2:
                cur.append((t, r))
            else:
                cur = [(t, r)]
                events.append(cur)
    print(f"\n== Engasgadas (frame acima de 50 ms): {len(events)} ==")
    events.sort(key=lambda e: -max(num(r, "worst_ms") for _, r in e))
    for e in events[:args.todas]:
        r = max((r for _, r in e), key=lambda r: num(r, "worst_ms"))
        c, v = cause_of(r)
        extra = []
        if num(r, "xlated"): extra.append(f"{num(r, 'xlated'):.0f} shaders novos")
        if num(r, "pipes"): extra.append(f"{num(r, 'pipes'):.0f} pipelines")
        if num(r, "tex_up"): extra.append(f"{num(r, 'tex_up'):.0f} texturas")
        if num(r, "read_kib") > 1024: extra.append(f"{num(r, 'read_kib') / 1024:.0f} MiB lidos")
        print(f"  {fmt_t(e[0][0])}  {len(e)} s, pior {num(r, 'worst_ms'):.0f} ms, fps {num(r, 'fps'):.0f}: {c} {v:.0f} ms"
              + (f" ({', '.join(extra)})" if extra else ""))

    # power and temperatures (Linux / Deck)
    apu = [num(r, "apu_w") for r in play if num(r, "apu_w") > 0]
    if apu:
        cpu = [num(r, "cpu_c") for r in play if num(r, "cpu_c") > 0]
        gpu = [num(r, "gpu_c") for r in play if num(r, "gpu_c") > 0]
        bat = [num(r, "bat_pct") for r in play if num(r, "bat_pct") > 0]
        print(f"\n== Consumo ==")
        print(f"  APU {statistics.mean(apu):.1f} W de média, pico {max(apu):.1f} W; CPU até {max(cpu, default=0):.0f} °C, "
              f"GPU até {max(gpu, default=0):.0f} °C" + (f"; bateria {bat[0]:.0f} % → {bat[-1]:.0f} %" if bat else ""))
        print(f"  clock médio: CPU {statistics.mean(num(r, 'cpu_mhz') for r in play):.0f} MHz, GPU "
              f"{statistics.mean(num(r, 'gpu_mhz') for r in play):.0f} MHz; núcleos do jogo "
              f"{statistics.mean(num(r, 'game_cores') for r in play):.2f}")

    # marks
    marks = [i for i, r in enumerate(rows) if num(r, "mark") > 0]
    if marks:
        print(f"\n== Marcas ({len(marks)}) ==")
        for i in marks:
            print(f"  marca {num(rows[i], 'mark'):.0f} em {fmt_t(num(rows[i], 't_s'))}: os 10 s antes e os 3 depois")
            for r in rows[max(i - 10, 0):i + 4]:
                c, v = cause_of(r)
                print(f"    {fmt_t(num(r, 't_s'))} fps {num(r, 'fps'):3.0f} pior {num(r, 'worst_ms'):5.0f} ms ({c} {v:.0f}) "
                      f"draws {num(r, 'draws'):5.0f} GPU {num(r, 'gpu_busy'):3.0f} % luma {num(r, 'luma'):4.0f}")
    else:
        print("\n(nenhuma marca nesta sessão: use \"Marcar este momento\" no menu rápido, L3+R3, ou F8 no PC)")

    if args.linhas:
        print("\n== Segundos abaixo de 28 fps ==")
        for r in play:
            if num(r, "fps") < 28:
                c, v = cause_of(r)
                print(f"  {fmt_t(num(r, 't_s'))} fps {num(r, 'fps'):3.0f} pior {num(r, 'worst_ms'):5.0f} ms {c} {v:.0f}; "
                      f"replay {num(r, 'replay_ms'):.1f} fence {num(r, 'fence_ms'):.1f} GPU {num(r, 'gpu_busy'):.0f} % "
                      f"núcleos {num(r, 'game_cores'):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

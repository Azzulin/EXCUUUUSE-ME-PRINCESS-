"""Makes aoc-report.zip for asking for help: the logs and this PC's details, nothing of the game.

The launcher's "Report..." button runs it (Windows: the launcher's Python; Linux: python3). Only the standard library.

  python tools/make_report.py   ->   <repository>/aoc-report.zip

Inside: system.txt (system, processor, memory, graphics cards and driver, free disk, launcher version), the last forge
logs (build/logs/), and each game folder's logs/ (texts, and the picture copies of the newest state-recorder reports)
and aoc.ini (dist/aoc-windows, dist/aoc-deck). No game files, no
keys, no saves. The logs carry paths of this PC (the user name may be in them); the README says so.
"""
import os
import platform
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "aoc-report.zip"
MAX_FILE = 8 << 20   # a log above 8 MiB keeps only its last 8 MiB


def cmd(args) -> str:
    try:
        p = subprocess.run(args, capture_output=True, timeout=20, stdin=subprocess.DEVNULL,
                           env=dict(os.environ, WSL_UTF8="1"))   # wsl.exe prints UTF-16 otherwise
        return p.stdout.decode("utf-8", "replace").replace("\x00", "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def system_txt() -> str:
    lines = [f"AoC Recomp {(ROOT / 'VERSION').read_text().strip() if (ROOT / 'VERSION').is_file() else '?'}",
             f"report made {time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"system: {platform.platform()} ({platform.machine()})",
             f"processor: {platform.processor() or '?'}, {os.cpu_count()} threads",
             f"python: {sys.version.split()[0]}"]
    if os.name == "nt":
        ps = ["powershell", "-NoProfile", "-Command"]
        lines.append("memory: " + cmd(ps + ["[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)"]) + " GB")
        lines.append("cpu: " + cmd(ps + ["(Get-CimInstance Win32_Processor).Name"]))
        lines.append("gpu:\n" + cmd(ps + ["Get-CimInstance Win32_VideoController | ForEach-Object { '  ' + $_.Name + ', driver ' + $_.DriverVersion }"]))
        lines.append("wsl:\n" + cmd(["wsl", "--version"]))
    else:
        try:
            mem = next(l for l in Path("/proc/meminfo").read_text().splitlines() if l.startswith("MemTotal"))
            lines.append(f"memory: {int(mem.split()[1]) / 2**20:.1f} GB")
        except (OSError, StopIteration, ValueError):
            pass
        try:
            cpu = next(l for l in Path("/proc/cpuinfo").read_text().splitlines() if l.startswith("model name"))
            lines.append("cpu: " + cpu.split(":", 1)[1].strip())
        except (OSError, StopIteration):
            pass
        lines.append("os-release:\n" + (Path("/etc/os-release").read_text() if Path("/etc/os-release").is_file() else "?"))
        lines.append("gpu:\n" + (cmd(["sh", "-c", "lspci 2>/dev/null | grep -Ei 'vga|3d|display'"]) or "?"))
    free = shutil.disk_usage(ROOT).free / 1e9
    lines.append(f"free disk where the package is: {free:.0f} GB")
    for d in ("dist/aoc-windows", "dist/aoc-deck"):
        p = ROOT / d
        lines.append(f"{d}: {'present' if p.is_dir() else 'missing'}")
    return "\n".join(lines) + "\n"


def add_file(z: zipfile.ZipFile, path: Path, arc: str) -> None:
    data = path.read_bytes()
    if len(data) > MAX_FILE:
        data = b"[... beginning cut, the file had %d bytes ...]\n" % len(data) + data[-MAX_FILE:]
    z.writestr(arc, data)


def main() -> int:
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("system.txt", system_txt())
        logs = ROOT / "build" / "logs"
        if logs.is_dir():
            for f in sorted(logs.glob("*.log"))[-5:]:
                add_file(z, f, f"forge/{f.name}")
        for d in ("aoc-windows", "aoc-deck"):
            game = ROOT / "dist" / d
            if (game / "aoc.ini").is_file():
                add_file(z, game / "aoc.ini", f"{d}/aoc.ini")
            logs_dir = game / "logs"
            if logs_dir.is_dir():
                # The logs and the recorded inputs, newest 6; logs/diag holds full-size captures and frame dumps (8 to
                # 60 MB each) that would push the logs out: only the small picture copies of its two newest reports.
                big = ("diag/hits/", "diag/marks/", "diag/dump/")
                text = [p for p in logs_dir.rglob("*") if p.is_file() and p.suffix in (".log", ".txt", ".gz")
                        and not p.relative_to(logs_dir).as_posix().startswith(big)]
                files = sorted(text, key=lambda p: p.stat().st_mtime)[-6:]
                reports = sorted((p for p in (logs_dir / "diag").glob("2*-*") if p.is_dir()), reverse=True)[:2] \
                    if (logs_dir / "diag").is_dir() else []
                files += [p for r in reports for p in sorted(r.glob("*.png"))]
                for f in files:
                    add_file(z, f, f"{d}/logs/{f.relative_to(logs_dir).as_posix()}")
    print(f"{OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

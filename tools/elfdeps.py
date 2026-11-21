"""The shared libraries an x86-64 ELF needs (DT_NEEDED), and their closure inside a sysroot.

Used for the Linux folders' fallback libraries (tools/build.py dist, tools/build_launcher.py --linux): the sniper
sysroot's libSDL3.so.0 links X11, Wayland, PulseAudio, ALSA and libdecor directly, so a Linux without one of them could
not even load the game or the launcher. The closure of those libraries, copied from the same sysroot, goes into a
fallback folder, one subfolder per library (<folder>/<soname>/<soname>). The start scripts (FALLBACK_SH) put on
LD_LIBRARY_PATH only the subfolders of the libraries ldd reports missing: a library the system has stays the system's,
because an older copy would shadow it for the system's own (Mesa's libEGL needs a newer libwayland-client than the
sniper's, measured on Ubuntu 24.04).

Only the standard library: the ELF dynamic section is read directly (no readelf needed on the player's system).
"""
import shutil
import struct
from pathlib import Path

# Never copied: glibc (the host's must be used) and what belongs to the GPU driver or the session (the host's own).
SYSTEM = ("libc.so", "libm.so", "libdl.so", "libpthread.so", "librt.so", "libresolv.so", "libutil.so", "ld-linux",
          "libGL", "libEGL", "libGLX", "libGLdispatch", "libOpenGL", "libvulkan", "libdrm", "libgbm", "libnvidia",
          "libgcc_s.so", "libstdc++.so")
LIB_DIRS = ("usr/lib/x86_64-linux-gnu", "lib/x86_64-linux-gnu", "usr/lib/x86_64-linux-gnu/pulseaudio", "usr/lib", "lib")


def needed(path: Path) -> list:
    """DT_NEEDED names of an ELF64 little-endian file; [] for anything else."""
    data = path.read_bytes()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        return []
    phoff, = struct.unpack_from("<Q", data, 0x20)
    phentsize, phnum = struct.unpack_from("<HH", data, 0x36)
    loads, dyn = [], None
    for i in range(phnum):
        p_type, _, p_offset, p_vaddr, _, p_filesz, _, _ = struct.unpack_from("<IIQQQQQQ", data, phoff + i * phentsize)
        if p_type == 1:
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == 2:
            dyn = (p_offset, p_filesz)
    if not dyn:
        return []
    entries, strtab = [], None
    for off in range(dyn[0], dyn[0] + dyn[1], 16):
        tag, val = struct.unpack_from("<qQ", data, off)
        if tag == 0:
            break
        if tag == 1:
            entries.append(val)
        elif tag == 5:
            strtab = val
    if strtab is None:
        return []
    base = next((o + strtab - v for v, o, n in loads if v <= strtab < v + n), None)
    if base is None:
        return []
    return [data[base + e:data.index(b"\0", base + e)].decode() for e in entries]


def is_system(name: str) -> bool:
    return name.startswith(SYSTEM)


def find(sysroot: Path, name: str):
    for d in LIB_DIRS:
        p = sysroot / d / name
        if p.exists():
            return p
    return None


def closure(sysroot: Path, roots: list) -> dict:
    """{soname: file in the sysroot} of everything the roots need, transitively, except glibc and driver libraries."""
    found, todo = {}, [n for r in roots for n in needed(r)]
    while todo:
        name = todo.pop()
        if name in found or is_system(name):
            continue
        p = find(sysroot, name)
        if p is None:
            continue
        found[name] = p.resolve()
        todo += needed(p.resolve())
    return found


def copy_fallback(sysroot: Path, roots: list, out: Path, skip=()) -> int:
    """Copies the closure into out, as out/<soname>/<soname>, except the names in skip (shipped beside the program
    already). Returns the number of libraries."""
    out.mkdir(parents=True, exist_ok=True)
    libs = {n: p for n, p in closure(sysroot, roots).items() if n not in skip}
    for name, src in sorted(libs.items()):
        dst = out / name / name
        dst.parent.mkdir(exist_ok=True)
        if not (dst.exists() and dst.stat().st_size == src.stat().st_size):
            shutil.copy2(src, dst)
    return len(libs)


# POSIX sh for a start script, with fb_bin (the program) and fb_dir (its fallback folder) set before: adds to
# LD_LIBRARY_PATH the subfolder of each library ldd cannot find, again until nothing more is missing (a fallback
# library may need others the system lacks too). Sets fb_used=1 when it added any.
FALLBACK_SH = r"""fb_add=""; fb_used=""
if command -v ldd >/dev/null; then
    for fb_round in 1 2 3 4 5 6 7 8; do
        fb_miss=$(LD_LIBRARY_PATH="$fb_add${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ldd "$fb_bin" 2>/dev/null)
        fb_miss=$(echo "$fb_miss" | awk '/not found/ { print $1 }')
        fb_new=""
        for fb_lib in $fb_miss; do
            [ -f "$fb_dir/$fb_lib/$fb_lib" ] || continue
            case ":$fb_add:" in *":$fb_dir/$fb_lib:"*) ;; *) fb_new="$fb_new:$fb_dir/$fb_lib" ;; esac
        done
        [ -n "$fb_new" ] || break
        fb_add="${fb_add}${fb_new}"; fb_add="${fb_add#:}"
    done
fi
if [ -n "$fb_add" ]; then
    fb_used=1
    export LD_LIBRARY_PATH="$fb_add${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
"""

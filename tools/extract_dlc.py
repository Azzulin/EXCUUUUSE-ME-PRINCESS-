#!/usr/bin/env python3
"""Extrai o RomFS de cada DLC de Age of Calamity dos NSPs para build/v130/ (ignorado pelo git).

Cada DLC (title id 01002B00111A3001 a ...3004) tem um NCA PublicData com uma seção RomFS. A saída é a imagem RomFS
simples dessa seção (o nível de dados do IVFC, o mesmo formato do build/v130/romfs.bin), uma por DLC:

    build/v130/dlc-<title id>.bin
    build/v130/dlc.json                título, índice (title id - 01002B00111A3000), tamanho, SHA-256 e arquivos

O runtime (runtime/dlc.c) procura esses arquivos na pasta romfs/ ao lado do executável; os que existem são os DLCs
que o jogo enxerga (nn::aoc::ListAddOnContent) e monta (nn::fs::MountAddOnContent).

A árvore de hashes IVFC inteira é conferida durante a cópia: cada bloco do nível de dados contra o nível acima, e
assim até o hash mestre do cabeçalho da seção (que o cabeçalho do NCA cobre; nx.read_nca_header confere). Uma imagem
que já está no disco com o tamanho e a data do dlc.json não é extraída de novo (--force refaz).

    python3 tools/extract_dlc.py --game-dir "Game Files" --keys "Game Files/prod.keys"

Lê os NSPs no lugar. As chaves ficam só em memória e nunca são impressas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AOC_BASE = 0x01002B00111A3000   # application id + 0x1000: o DLC de índice n tem o title id AOC_BASE + n
CHUNK = 8 << 20


def ivfc_levels(fs: bytes) -> tuple[list[tuple[int, int, int]], bytes]:
    """Os seis níveis (offset na seção, tamanho, tamanho do bloco) e o hash mestre do cabeçalho de uma seção IVFC."""
    nx.require(fs[8:12] == b"IVFC", "Seção sem IVFC")
    master_size, count = struct.unpack_from("<II", fs, 0x10)
    nx.require(count == 7 and master_size == 0x20, "Layout de IVFC não suportado")
    levels = []
    for k in range(6):
        off, size, log2, _ = struct.unpack_from("<QQII", fs, 0x18 + 0x18 * k)
        nx.require(12 <= log2 <= 24, "Bloco de IVFC fora do esperado")
        levels.append((off, size, 1 << log2))
    return levels, fs[0xC8:0xE8]


def block_hashes(data: bytes, block: int, out: bytearray) -> None:
    """SHA-256 de cada bloco de data (o último completado com zeros, como o IVFC faz), acrescentados a out."""
    for pos in range(0, len(data), block):
        part = data[pos:pos + block]
        if len(part) < block:
            part += bytes(block - len(part))
        out += hashlib.sha256(part).digest()


def copy_verified(sec: nx.SectionReader, dst: Path) -> tuple[int, str]:
    """Grava o nível de dados em dst conferindo a árvore IVFC inteira. Devolve (tamanho, SHA-256 da imagem)."""
    levels, master = ivfc_levels(sec.fs)
    # níveis 0 a 4 são tabelas de hash pequenas: cada um é conferido contra o de cima, o primeiro contra o hash mestre
    tables = []
    expected = master
    for off, size, block in levels[:5]:
        nx.require(size <= nx.MAX_READ, "Tabela de hash do IVFC grande demais")
        data = sec.read(off, size)
        got = bytearray()
        block_hashes(data, block, got)
        nx.require(bytes(got) == expected[:len(got)], "Tabela de hash do IVFC não bate (NSP corrompido?)")
        tables.append(data)
        expected = data
    off, size, block = levels[5]
    nx.require(CHUNK % block == 0, "Bloco de IVFC maior que o esperado")
    whole = hashlib.sha256()
    part = dst.with_name(dst.name + ".part")
    done = 0
    try:
        with part.open("wb") as out:
            while done < size:
                n = min(CHUNK, size - done)
                data = sec.read(off + done, n)
                got = bytearray()
                block_hashes(data, block, got)
                at = done // block * 32
                nx.require(bytes(got) == expected[at:at + len(got)], f"Bloco de dados em {done:#x} não bate com o IVFC")
                out.write(data)
                whole.update(data)
                done += n
    except BaseException:
        part.unlink(missing_ok=True)   # nunca fica uma imagem pela metade com cara de pronta
        raise
    part.replace(dst)
    return size, whole.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game-dir", type=Path, default=ROOT / "Game Files")
    ap.add_argument("--keys", type=Path, default=None, help="padrão: prod.keys na pasta do jogo")
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "v130")
    ap.add_argument("--force", action="store_true", help="extrai de novo mesmo com a imagem no disco")
    args = ap.parse_args(argv)
    keys = nx.load_keys(args.keys or args.game_dir / "prod.keys")
    args.out.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out / "dlc.json"
    try:
        old = {e["title_id"]: e for e in json.loads(manifest_path.read_text(encoding="utf-8"))["dlc"]}
    except (OSError, ValueError, KeyError):
        old = {}
    found = []
    for path in sorted(p for p in args.game_dir.rglob("*.nsp")):
        with path.open("rb") as f:
            _, entries = nx.container_entries(f, path.stat().st_size)
            tickets = nx.common_tickets(f, entries)
            for nca in nx.nca_inventory(f, entries, keys):
                tid = int(nca.title_id, 16)
                if nca.content_type != 5 or not 0 < tid - AOC_BASE < 0x1000:
                    continue
                key = nx.nca_ctr_key(nca, keys, tickets)
                for i in nca.sections():
                    if nca.section_kind(i) != "romfs":
                        continue
                    sec = nx.SectionReader(f, nca, i, key)
                    dst = args.out / f"dlc-{nca.title_id}.bin"
                    prev = old.get(nca.title_id)
                    if (not args.force and prev and dst.is_file() and dst.stat().st_size == prev["size"]
                            and dst.stat().st_mtime_ns == prev["mtime_ns"]):
                        print(f"DLC {tid - AOC_BASE} ({nca.title_id}): já extraído, {prev['size'] / 2**20:.1f} MiB")
                        found.append(prev)
                        continue
                    t0 = time.monotonic()
                    size, sha = copy_verified(sec, dst)
                    with dst.open("rb") as image:
                        files = nx.romfs_image_files(image)
                    nx.require(all(o + s <= size for _p, o, s in files), "Arquivo do RomFS fora da imagem")
                    found.append({"title_id": nca.title_id, "index": tid - AOC_BASE, "file": dst.name, "size": size,
                                  "mtime_ns": dst.stat().st_mtime_ns, "sha256": sha, "files": len(files),
                                  "source": path.name})
                    print(f"DLC {tid - AOC_BASE} ({nca.title_id}): {len(files)} arquivos, {size / 2**20:.1f} MiB, "
                          f"IVFC conferido, {time.monotonic() - t0:.1f} s  → {dst.name}")
    found.sort(key=lambda e: e["index"])
    manifest_path.write_text(json.dumps({"dlc": found}, indent=1) + "\n", encoding="utf-8")
    if not found:
        print(f"Nenhum DLC em {args.game_dir} (o jogo roda sem eles)")
    else:
        print(f"{len(found)} DLCs em {args.out} ({sum(e['size'] for e in found) / 2**30:.2f} GiB)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as e:
        print("ERRO:", e)
        sys.exit(1)

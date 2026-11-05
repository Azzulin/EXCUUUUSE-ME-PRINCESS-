#!/usr/bin/env python3
"""Índice do RomFS mesclado que o runtime busca por bisseção (runtime/romfs.c) e o romfs_config.h dele.

Adaptado de astral-chain-pc-recomp tools/romfs_index.py @ 3bbaf259ac099a321c78b81f5402f6070a77874a (MIT), que por sua
vez adapta MacNativeGames games/totk/scripts/prepare_romfs_backend.py @ b75be8cf (MIT, Copyright (c) 2026
MacNativeGames contributors). Mudança para o AoC: a lista de arquivos sai direto das tabelas do próprio romfs.bin
(tools/nx.py romfs_image_files), sem o index.json do extrator do TotK.

Entrada: build/v130/romfs.bin (RomFS 1.3.0 mesclado por tools/windows/merge_romfs.bat). Saída, no diretório de build
(nunca no repositório):

    romfs-index.bin   layout ACRFS1: cabeçalho <8sQQ (magic, contagem, offset das strings), linhas de 24 bytes <QQII
                      (offset no romfs.bin, tamanho, offset do nome, tamanho do nome com o NUL), depois os nomes
                      terminados em NUL; linhas em ordem dos bytes UTF-8 do caminho (a ordem do strcmp)
    romfs_config.h    ROMFS_IMAGE_SIZE, ROMFS_IMAGE_SHA256, ROMFS_INDEX_SHA256, ROMFS_FILE_COUNT

O SHA-256 dos 10,9 GiB da imagem é calculado uma vez e guardado em build/v130/romfs.bin.sha256 junto com o tamanho e
a data de modificação; só é refeito se a imagem mudar. Os dois arquivos de saída só são reescritos quando os bytes
mudam, para o ninja não recompilar romfs.c à toa.

    python3 tools/romfs_index.py --image build/v130/romfs.bin --out ~/aoc-build/host
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
from check_content import GENERATED_MARKER  # noqa: E402

MAGIC = b'ACRFS1'   # o formato que runtime/romfs.c confere
HEADER = struct.Struct('<8sQQ')
ROW = struct.Struct('<QQII')


def build_index(files, image_size):
    """Bytes do índice para [(caminho, offset, tamanho)]; para com erro se a lista estiver malformada."""
    files = sorted(files, key=lambda e: e[0].encode())
    strings, rows, previous = bytearray(), bytearray(), None
    for path, offset, size in files:
        name = path.encode()
        if not name or name.startswith(b'/') or b'\\' in name or b'\0' in name:
            sys.exit(f'romfs_index: caminho malformado no RomFS (entrada {len(rows) // ROW.size})')
        if name == previous:
            sys.exit(f'romfs_index: caminho repetido no RomFS: {path}')
        previous = name
        if offset < 0 or size < 0 or offset + size > image_size:
            sys.exit(f'romfs_index: {path} fica fora da imagem')
        rows += ROW.pack(offset, size, len(strings), len(name) + 1)
        strings += name + b'\0'
    return HEADER.pack(MAGIC, len(files), HEADER.size + len(rows)) + bytes(rows) + bytes(strings)


def image_sha256(image: Path) -> str:
    """SHA-256 da imagem, do cache ao lado dela quando tamanho e data batem."""
    st = image.stat()
    cache = image.with_name(image.name + '.sha256')
    try:
        c = json.loads(cache.read_text())
        if c['size'] == st.st_size and c['mtime_ns'] == st.st_mtime_ns:
            return c['sha256']
    except (OSError, ValueError, KeyError):
        pass
    print(f'romfs_index: calculando o SHA-256 de {image} ({st.st_size / 2**30:.1f} GiB, uma vez só)', flush=True)
    h = hashlib.sha256()
    with image.open('rb') as f:
        while chunk := f.read(16 << 20):
            h.update(chunk)
    digest = h.hexdigest()
    cache.write_text(json.dumps({'size': st.st_size, 'mtime_ns': st.st_mtime_ns, 'sha256': digest}) + '\n')
    return digest


def write_if_changed(path: Path, data: bytes) -> None:
    if path.exists() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write(image: Path, out: Path):
    """Grava romfs-index.bin e romfs_config.h em out. Devolve (arquivos, bytes do índice, segundos)."""
    t0 = time.monotonic()
    size = image.stat().st_size
    with image.open('rb') as f:
        files = nx.romfs_image_files(f)
    index = build_index(files, size)
    write_if_changed(out / 'romfs-index.bin', index)
    config = (f'// Identidade da imagem RomFS e do índice, escrita por tools/romfs_index.py; não editar. {GENERATED_MARKER}\n'
              '#pragma once\n'
              f'#define ROMFS_IMAGE_SIZE {size}ull\n'
              f'#define ROMFS_IMAGE_SHA256 "{image_sha256(image)}"\n'
              f'#define ROMFS_INDEX_SHA256 "{hashlib.sha256(index).hexdigest()}"\n'
              f'#define ROMFS_FILE_COUNT {len(files)}ull\n')
    write_if_changed(out / 'romfs_config.h', config.encode())
    return len(files), len(index), time.monotonic() - t0


def write_placeholder(out: Path) -> None:
    """romfs_config.h sem RomFS (máquina sem o jogo extraído): o executável compila e fs_init para com um erro claro."""
    (out / 'romfs-index.bin').unlink(missing_ok=True)
    config = (f'// Nenhum RomFS encontrado por tools/romfs_index.py; não editar. {GENERATED_MARKER}\n'
              '#pragma once\n'
              '#define ROMFS_MISSING 1\n'
              '#define ROMFS_IMAGE_SIZE 0ull\n'
              '#define ROMFS_IMAGE_SHA256 ""\n'
              '#define ROMFS_INDEX_SHA256 ""\n'
              '#define ROMFS_FILE_COUNT 0ull\n')
    write_if_changed(out / 'romfs_config.h', config.encode())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--image', type=Path, required=True, help='romfs.bin mesclado')
    ap.add_argument('--out', type=Path, required=True, help='diretório de build')
    args = ap.parse_args()
    count, size, dt = write(args.image.resolve(), args.out.expanduser().resolve())
    print(f'romfs index: {count} arquivos, {size:,} bytes, {dt:.1f} s')
    return 0


if __name__ == '__main__':
    sys.exit(main())

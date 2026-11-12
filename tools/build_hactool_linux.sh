#!/bin/bash
# Compila o hactool 1.4.0 (ISC) para Linux contra o sysroot sniper (glibc 2.31), para rodar em qualquer distro atual.
# tools/make_release.py o põe em prebuilt/hactool/linux-x64 do pacote Linux (o tools/merge_romfs.py o usa).
#   bash tools/build_hactool_linux.sh <fonte do hactool 1.4.0> <pasta de saída> [sysroot]
set -euo pipefail
SRC="$1"; OUT="$2"; SNIPER="${3:-$HOME/aoc-build/toolchain/sniper}"
[ -f "$SRC/main.c" ] || { echo "ERRO: $SRC não é a fonte do hactool" >&2; exit 1; }
B="$(mktemp -d)"
cp -r "$SRC/." "$B/"
cd "$B"
cp config.mk.template config.mk
make -s CC="clang --target=x86_64-linux-gnu --sysroot=$SNIPER" AR=llvm-ar \
    LDFLAGS="-fuse-ld=lld -lmbedtls -lmbedx509 -lmbedcrypto" -j"$(nproc)" >/dev/null 2>&1 \
    || { echo "ERRO: o hactool não compilou" >&2; exit 1; }
mkdir -p "$OUT"
cp hactool "$OUT/hactool"
llvm-strip "$OUT/hactool"
cp LICENSE "$OUT/LICENSE"
rm -rf "$B"
echo "hactool: $OUT/hactool ($(stat -c %s "$OUT/hactool") bytes)"

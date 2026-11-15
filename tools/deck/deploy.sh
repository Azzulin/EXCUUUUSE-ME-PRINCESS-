#!/bin/bash
# Builds the Deck folder (dist) and sends the changed small files to the Steam Deck over SSH (never romfs.bin), and
# the DLC images (romfs/dlc-*.bin, 1.4 GiB in all) the Deck lacks or has with another size.
# Usage (Git Bash): bash deploy.sh [--no-build]
set -e
R="$(cd "$(dirname "$0")/../.." && pwd)"
D="$R/dist/aoc-deck"
DECK=${AOC_DECK:-deck@192.168.100.130}             # AOC_DECK=user@host
G=${AOC_DECK_DIR:-/run/media/deck/e3e0373c-4153-46c2-a60c-c5f97dd60eee/Games/aoc-deck}   # the folder on the Deck
SSH="ssh -i $HOME/.ssh/id_ed25519_deck -o BatchMode=yes"
if [ "$1" != "--no-build" ]; then
  wsl.exe -d archlinux -- bash -c 'cd "/mnt/c/Users/gabri/Downloads/Age of Calamity/Age of Calamity" && . ~/.venvs/aoc/bin/activate && python3 -u tools/build.py --work ~/aoc-build --jobs 10 host dist 2>&1 | grep -E "dist:|host: pronto|ERRO|error|FAILED"'
fi
cd "$D"
# the owner plays on the Deck: nothing is sent while the game or the TotK port is open
busy=$($SSH -o ConnectTimeout=10 $DECK "pgrep -a totk; pgrep -ax aoc" 2>&1) || true
if [ -n "$busy" ]; then echo "Deck ocupado ou fora do ar, nada enviado:"; echo "$busy"; exit 2; fi
files="aoc aoc_xlate aoc_xlate.id aoc.sh instalar-atalho.sh LEIA-ME.txt romfs-index.bin lib/libSDL3.so.0 aoc-logs.sh ferramentas/logsum.py ferramentas/diag_view.py ferramentas/perf_view.py"
$SSH $DECK "mkdir -p $G/ferramentas"
# only what differs (size + sha256)
remote=$($SSH $DECK "cd $G && sha256sum $files 2>/dev/null" || true)
send=""
for f in $files; do
  h=$(sha256sum "$f" | cut -d' ' -f1)
  echo "$remote" | grep -q "$h  $f" || send="$send $f"
done
if [ -n "$send" ]; then
  echo "enviando:$send"
  # to a temporary name, then renamed: a connection lost mid-copy (the Deck suspends) never leaves a truncated aoc
  for f in $send; do
    scp -q -i "$HOME/.ssh/id_ed25519_deck" -o BatchMode=yes "$f" "$DECK:$G/$f.envio" && $SSH $DECK "mv -f $G/$f.envio $G/$f" \
      || { echo "falhou: $f (o arquivo antigo do Deck ficou como estava)"; exit 1; }
  done
  $SSH $DECK "cd $G && chmod +x aoc aoc_xlate aoc.sh instalar-atalho.sh aoc-logs.sh"
else
  echo "nada a enviar"
fi
# DLC images: sent once (compared by size; they only change if the dump does)
for f in romfs/dlc-*.bin; do
  [ -f "$f" ] || continue
  sz=$(stat -c %s "$f")
  rsz=$($SSH $DECK "stat -c %s $G/$f 2>/dev/null" || true)
  [ "$sz" = "$rsz" ] && continue
  echo "enviando $f ($((sz / 1048576)) MiB)"
  scp -q -i "$HOME/.ssh/id_ed25519_deck" -o BatchMode=yes "$f" "$DECK:$G/$f.envio" && $SSH $DECK "mv -f $G/$f.envio $G/$f"     || { echo "falhou: $f"; exit 1; }
done

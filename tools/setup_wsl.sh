#!/usr/bin/env bash
# Prepara o WSL2 (Ubuntu 22.04/24.04) para gerar e compilar o AoC Recomp. Rode uma vez:
#   bash "/mnt/d/Decomp/Age of Calamity/tools/setup_wsl.sh"
# Instala clang/lld/ninja pelo apt (pede a senha do sudo) e cria um venv Python em ~/.venvs/aoc.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v clang >/dev/null && command -v ld.lld >/dev/null && command -v ninja >/dev/null \
        && dpkg -s python3-venv >/dev/null 2>&1; then
    echo "clang, lld, ninja e python3-venv já instalados."
else
    sudo apt-get update
    sudo apt-get install -y clang lld llvm ninja-build python3-venv python3-pip git pkg-config
fi

if [ ! -x "$HOME/.venvs/aoc/bin/python" ]; then
    python3 -m venv "$HOME/.venvs/aoc"
    "$HOME/.venvs/aoc/bin/pip" install --upgrade pip
fi
"$HOME/.venvs/aoc/bin/pip" install -q -r "$REPO/tools/requirements.txt"

echo
echo "Pronto. Para usar:"
echo "  source ~/.venvs/aoc/bin/activate"
echo "  cd \"$REPO\""
echo "  python3 tools/build.py --work ~/aoc-build"
clang --version | head -1
ninja --version

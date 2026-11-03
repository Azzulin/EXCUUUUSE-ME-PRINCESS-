#!/usr/bin/env bash
# Prepara o WSL2 (Ubuntu 22.04/24.04) para gerar e compilar o AoC Recomp. Rode uma vez:
#   bash "/mnt/d/Decomp/Age of Calamity/tools/setup_wsl.sh"
# Instala clang/lld/ninja pelo apt (pede a senha do sudo) e cria um venv Python em ~/.venvs/aoc.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo apt-get update
sudo apt-get install -y clang lld llvm ninja-build python3-venv python3-pip git pkg-config

python3 -m venv "$HOME/.venvs/aoc"
"$HOME/.venvs/aoc/bin/pip" install --upgrade pip
"$HOME/.venvs/aoc/bin/pip" install -r "$REPO/tools/requirements.txt"

echo
echo "Pronto. Para usar:"
echo "  source ~/.venvs/aoc/bin/activate"
echo "  cd \"$REPO\""
echo "  python3 tools/build.py --work ~/aoc-build"
clang --version | head -1
ninja --version

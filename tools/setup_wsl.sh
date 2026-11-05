#!/usr/bin/env bash
# Prepara o WSL2 (Ubuntu 22.04/24.04 ou Arch Linux) para gerar e compilar o AoC Recomp. Rode uma vez:
#   bash "<repositório>/tools/setup_wsl.sh"
# Instala clang/lld/ninja pelo apt ou pelo pacman (pede a senha do sudo, se não for root) e cria um venv Python em
# ~/.venvs/aoc.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Root (comum no Arch do WSL) não precisa de sudo, e o Arch do WSL nem traz o sudo.
SUDO=sudo
[ "$(id -u)" = 0 ] && SUDO=

# Além do compilador: bibliotecas do runtime (SDL3, Opus, libvpx, zstd, Vulkan) para o executável de desenvolvimento,
# make e curl para o passo dist (zstd estática e sysroot sniper) e gdb para depurar.
if command -v clang >/dev/null && command -v ld.lld >/dev/null && command -v ninja >/dev/null \
        && python3 -c 'import venv, ensurepip' >/dev/null 2>&1 && pkg-config --exists sdl3 opus vpx libzstd vulkan \
        && command -v make >/dev/null; then
    echo "clang, lld, ninja, python3 (venv) e as bibliotecas do runtime já instalados."
elif command -v apt-get >/dev/null; then
    $SUDO apt-get update
    # SDL3 só existe no Ubuntu 25.04 em diante (libsdl3-dev); no 24.04, compile a SDL 3.4 à mão ou use o Arch.
    $SUDO apt-get install -y clang lld llvm ninja-build python3-venv python3-pip git pkg-config make curl gdb \
        libopus-dev libvpx-dev libzstd-dev libvulkan-dev
    $SUDO apt-get install -y libsdl3-dev || echo "AVISO: sem libsdl3-dev nesta versão do Ubuntu (o passo host precisa dela)"
elif command -v pacman >/dev/null; then
    $SUDO pacman -Syu --noconfirm --needed clang lld llvm ninja python python-pip git pkgconf make curl gdb time \
        sdl3 opus libvpx zstd vulkan-headers vulkan-icd-loader
else
    echo "ERRO: distro sem apt nem pacman; instale clang, lld, llvm, ninja, python3 (venv) e git à mão." >&2
    exit 1
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

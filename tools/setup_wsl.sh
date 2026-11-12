#!/usr/bin/env bash
# Prepara o Linux (WSL2 ou um PC com Linux: Arch, Ubuntu/Debian ou Fedora) para gerar e compilar o AoC Recomp:
#   bash "<repositório>/tools/setup_wsl.sh"            tudo, para desenvolver (bibliotecas do runtime, gdb, testes)
#   bash "<repositório>/tools/setup_wsl.sh" --minimal  só o que a forja do Deck precisa (o launcher usa este)
# Instala os pacotes pelo pacman, apt ou dnf e cria um venv Python em ~/.venvs/aoc. Como root (o Arch do WSL) não pede
# senha; num terminal usa o sudo; sem terminal (o launcher) usa o pkexec, que abre a janela de senha do sistema.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINIMAL=0
[ "${1:-}" = "--minimal" ] && MINIMAL=1

if [ "$(id -u)" = 0 ]; then
    SUDO=()
elif [ -t 0 ] && command -v sudo >/dev/null; then
    SUDO=(sudo)
elif command -v pkexec >/dev/null; then
    SUDO=(pkexec)
else
    SUDO=(sudo)
fi

# O que a forja precisa: clang, lld e llvm-ar (código do jogo e o executável do Deck contra o sysroot sniper), ninja,
# Python com venv, make e curl (passo dist: zstd estática e o sysroot) e os headers do Vulkan (o dist os copia para
# compilar contra o sniper). O modo completo junta as bibliotecas do runtime (SDL3, Opus, libvpx, zstd, o loader do
# Vulkan) para o executável de desenvolvimento, pkg-config, git e gdb.
have_minimal() {
    command -v clang >/dev/null && command -v ld.lld >/dev/null && command -v llvm-ar >/dev/null \
        && command -v ninja >/dev/null && command -v make >/dev/null && command -v curl >/dev/null \
        && [ -f /usr/include/vulkan/vulkan.h ] && python3 -c 'import venv, ensurepip' >/dev/null 2>&1
}
have_full() {
    have_minimal && command -v pkg-config >/dev/null && pkg-config --exists sdl3 opus vpx libzstd vulkan
}

if { [ $MINIMAL = 1 ] && have_minimal; } || have_full; then
    echo "Ferramentas já instaladas."
elif command -v pacman >/dev/null; then
    # A imagem Arch do WSL só gera o chaveiro do pacman na primeira abertura interativa (/usr/lib/wsl/first-setup.sh);
    # aberta pelo launcher (wsl -e) isso não roda, e o pacman recusa todo pacote ("required key missing").
    # A chave-mestra local ("pacman@localhost") só existe depois do --init; um pacman que falhou antes deixa um
    # pubring.kbx vazio, que não serve de sinal.
    if ! "${SUDO[@]}" pacman-key --list-secret-keys 2>/dev/null | grep -q 'pacman@localhost'; then
        echo "Gerando o chaveiro do pacman (primeira vez)..."
        "${SUDO[@]}" sh -c 'pacman-key --init >/dev/null 2>&1 && pacman-key --populate archlinux >/dev/null 2>&1'
    fi
    pkgs=(clang lld llvm ninja python make curl tar vulkan-headers)
    [ $MINIMAL = 0 ] && pkgs+=(python-pip git pkgconf gdb time sdl3 opus libvpx zstd vulkan-icd-loader)
    "${SUDO[@]}" pacman -Syu --noconfirm --needed "${pkgs[@]}"
elif command -v apt-get >/dev/null; then
    pkgs=(clang lld llvm ninja-build python3-venv make curl ca-certificates libvulkan-dev)
    # SDL3 só existe no Ubuntu 25.04 em diante (libsdl3-dev); a forja do Deck não precisa dela (usa a do sniper).
    [ $MINIMAL = 0 ] && pkgs+=(python3-pip git pkg-config gdb libopus-dev libvpx-dev libzstd-dev libsdl3-dev)
    "${SUDO[@]}" sh -c "export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y ${pkgs[*]}"
elif command -v dnf >/dev/null; then
    pkgs=(clang lld llvm ninja-build python3 make curl tar vulkan-headers)
    [ $MINIMAL = 0 ] && pkgs+=(python3-pip git pkgconf gdb opus-devel libvpx-devel libzstd-devel vulkan-loader-devel SDL3-devel)
    "${SUDO[@]}" dnf install -y "${pkgs[@]}"
else
    echo "ERRO: distro sem pacman, apt nem dnf; instale clang, lld, llvm, ninja, make, curl e python3 (com venv) à mão." >&2
    exit 1
fi
# O Ubuntu instala o lld como ld.lld-NN em algumas versões; o passo dist chama ld.lld pelo clang (-fuse-ld=lld).
command -v ld.lld >/dev/null || { echo "ERRO: ld.lld não encontrado depois da instalação" >&2; exit 1; }

if [ ! -x "$HOME/.venvs/aoc/bin/python" ]; then
    python3 -m venv "$HOME/.venvs/aoc"
    "$HOME/.venvs/aoc/bin/python" -m pip install -q --upgrade pip
fi
if [ $MINIMAL = 1 ]; then
    "$HOME/.venvs/aoc/bin/python" -m pip install -q -r "$REPO/tools/requirements-forge.txt"
else
    "$HOME/.venvs/aoc/bin/python" -m pip install -q -r "$REPO/tools/requirements.txt"
fi

echo
echo "Pronto. Para usar:"
echo "  source ~/.venvs/aoc/bin/activate"
echo "  cd \"$REPO\""
echo "  python3 tools/build.py --work ~/aoc-build"
clang --version | head -1
echo "ninja $(ninja --version)"

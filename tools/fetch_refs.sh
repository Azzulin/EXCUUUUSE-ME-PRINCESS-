#!/bin/sh
# Clona os projetos de referência em refs/, nas revisões fixadas em docs/referencias.md.
# refs/ é material de leitura (somente leitura) e é ignorado pelo git.
set -eu

cd "$(dirname "$0")/.."
mkdir -p refs

# fetch <nome> <url> <commit>: checkout raso exatamente daquele commit.
fetch() {
    name=$1 url=$2 commit=$3
    dir=refs/$name
    if [ "$(git -C "$dir" rev-parse HEAD 2>/dev/null)" = "$commit" ]; then
        echo "$name: atualizado"
        return
    fi
    rm -rf "$dir"
    git init -q "$dir"
    git -C "$dir" remote add origin "$url"
    git -C "$dir" fetch -q --depth 1 origin "$commit"
    git -C "$dir" checkout -q FETCH_HEAD
    echo "$name: $commit"
}

fetch astral-chain-pc-recomp https://github.com/captainj-sparrow/astral-chain-pc-recomp.git 3bbaf259ac099a321c78b81f5402f6070a77874a
fetch totk-pc-recomp         https://github.com/valentderah/totk-pc-recomp.git           c38e0ca13d2bceb0590b195f69a010315913850d
fetch nxnative               https://github.com/seedds/nxnative.git                      3ace3df33b81681cdc9d17bfa48eadaccd446b5c
fetch MacNativeGames         https://github.com/ly05010419/MacNativeGames.git            3ac015c3ad1291d529bb086b1342ec5ec7db8eb3
fetch HWDER                  https://github.com/blocker-3/HWDER.git                      444b67c02d4c57ad2e2fdd5d4430c4ac7171fb1f
fetch LASRecomp              https://github.com/peiikai/LASRecomp.git                    a6b4f03844ecfb4012f18deff96da8b410aeafcd
fetch SavageWindRecomp       https://github.com/Revivedx/SavageWindRecomp.git            bf6146c14c37fee8781a601e5a544b93dff6d75e

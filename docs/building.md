# Como gerar e compilar

Decisão do projeto: **tudo é compilado no PC** (WSL2 no Windows, i7-12700) e o resultado é **uma pasta única**
(`dist/aoc-deck/`) que é só copiar para o Steam Deck — por FTP, armazenamento na nuvem ou cabo. O Deck não compila
nada.

## 1. Preparar o WSL (uma vez)

Atalho: clique duas vezes em `build.bat` na raiz (chama `tools\windows\build_wsl.bat`) — confere o WSL, faz este
passo, extrai o ExeFS de `Game Files/` se faltar e roda o passo 3, gravando o log em `build\build-wsl.log`. Funciona em
qualquer máquina com o repositório clonado e o dump em `Game Files/`. Ou, no terminal do WSL:

```sh
bash "/mnt/d/Decomp/Age of Calamity/tools/setup_wsl.sh"
source ~/.venvs/aoc/bin/activate
cd "/mnt/d/Decomp/Age of Calamity"
git config core.hooksPath .githooks
```

Instala clang, lld, llvm, ninja e um venv Python com `tools/requirements.txt`.

## 2. Extrair o jogo (Fase 0, já feito uma vez)

```sh
python3 tools/extract.py inventory          # confere base, update 1.3.0 e DLCs em "Game Files/"
python3 tools/extract.py exefs              # build/v130/exefs/ (código do jogo)
# RomFS mesclado: no Windows, tools\windows\merge_romfs.bat → build\v130\romfs.bin
python3 tools/inspect_dump.py --exefs build/v130/exefs
```

## 3. Gerar o C e compilar o código do jogo

```sh
python3 tools/build.py --work ~/aoc-build
```

- `gen`: `recomp/gen.py` gera ~600 MB de C em `~/aoc-build/generated/` (~3 min em 2 núcleos; bem menos no i7).
- `guest`: compila os 377 arquivos com clang e junta em `~/aoc-build/lib/libaoc_guest.a`.
- O diretório de trabalho fica **no disco do Linux** (`~/aoc-build`), não em `/mnt/d`: compilar pelo WSL sobre o
  disco do Windows é muito mais lento. Só a pasta final volta para o D.
- As ~35 funções gigantes do `main` dominam o tempo (cada uma de 1 a 7 MB de C, 15–20 min a maior delas num núcleo,
  até ~2–4 GB de RAM cada). O build as começa primeiro e usa flags que cortam ~40 % do tempo delas. Se faltar
  memória, use `--jobs 8`.
- Recompilar é incremental: o gerador só reescreve os arquivos cujo C mudou, e o ninja só recompila esses.

## 4. Pasta para o Deck (a partir da Fase 2)

Quando houver runtime, `tools/build.py ... dist` vai linkar o executável e montar `dist/aoc-deck/` no disco D
(layout em [steam-deck.md](steam-deck.md)). Basta copiar essa pasta inteira para o cartão SD do Deck.

## Testes do lifter (sem compilar o jogo inteiro)

```sh
python3 tests/flags_check.py
python3 tests/diff/lift.py --modules main,subsdk0,sdk --jobs 16
python3 tests/diff/func.py --modules main,subsdk0,sdk --functions 300 --jobs 16
python3 tests/jumptables_check.py --modules main,subsdk0,sdk
python3 tests/diff/simd.py && python3 tests/diff/atomic.py     # não usam arquivos do jogo
```

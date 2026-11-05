# Como gerar e compilar

Decisão do projeto: **tudo é compilado no PC** (WSL2 no Windows, i7-12700) e o resultado é **uma pasta única**
(`dist/aoc-deck/`) que é só copiar para o Steam Deck — por FTP, armazenamento na nuvem ou cabo. O Deck não compila
nada.

## 1. Preparar o WSL (uma vez)

Atalho: clique duas vezes em `build.bat` na raiz (chama `tools\windows\build_wsl.bat`) — confere o WSL, faz este
passo, extrai o ExeFS de `Game Files/` se faltar e roda o passo 3, gravando o log em `build\build-wsl.log`. Funciona em
qualquer máquina com o repositório clonado e o dump em `Game Files/`. Ou, no terminal do WSL:

```sh
bash "<repositório>/tools/setup_wsl.sh"
source ~/.venvs/aoc/bin/activate
cd "<repositório>"
git config core.hooksPath .githooks
```

Funciona com **Ubuntu** (apt) ou **Arch Linux** (pacman; o Arch do WSL roda como root e nem tem sudo). Instala clang,
lld, llvm, ninja, make, curl, gdb, as bibliotecas do runtime (SDL3, Opus, libvpx, zstd, Vulkan) e um venv Python com
`tools/requirements.txt`. No Ubuntu 24.04 não há pacote da SDL3 (só do 25.04 em diante); o Arch tem tudo.

As referências (`refs/`) vêm de `sh tools/fetch_refs.sh` — no Windows, pelo Git Bash, que é mais rápido no NTFS.

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

- `gen`: `recomp/gen.py --patches recomp/patches-v130.txt` gera ~600 MB de C em `~/aoc-build/generated/` (~3 min).
  Roda de novo sozinho quando `recomp/*.py` ou a tabela de patches ficam mais novos que o C gerado.
- `guest`: compila os 377 arquivos com clang e junta em `~/aoc-build/lib/libaoc_guest.a`.
- O diretório de trabalho fica **no disco do Linux** (`~/aoc-build`), não em `/mnt/d`: compilar pelo WSL sobre o
  disco do Windows é muito mais lento. Só a pasta final volta para o D.
- As 40 funções gigantes do `main` dominam o tempo (cada uma de 1 a 7 MB de C, 15–20 min a maior delas num núcleo,
  até ~1,6 GB de RAM medidos). O build as começa primeiro e usa flags que cortam ~40 % do tempo delas. O número delas
  rodando juntas sai da RAM livre (4 GB cada) e é conservador: com 11 GB, `--big-jobs 4` coube com folga. No notebook
  (i5-11400H, 12 threads) o build inteiro levou ~48 min com `--jobs 10`.
- Recompilar é incremental: o gerador só reescreve os arquivos cujo C mudou, e o ninja só recompila esses.

## 4. Executável de desenvolvimento (`host`)

```sh
python3 tools/build.py --work ~/aoc-build host     # runtime + link → ~/aoc-build/host/aoc (o padrão já inclui host)
~/aoc-build/host/aoc --selftest
AOC_GPU=null ~/aoc-build/host/aoc --boot           # até o primeiro nvnBootstrapLoader
AOC_GPU=null AOC_TRACE=perf ~/aoc-build/host/aoc   # o jogo inteiro sem GPU (Ctrl+C ou pkill -9 -x aoc)
```

- `host` escreve `modules.c` (layout, tabelas de funções, SHA-256 do ExeFS, caminhos padrão) e, de
  `build/v130/romfs.bin`, o `romfs-index.bin` e o `romfs_config.h` (`tools/romfs_index.py`; o SHA-256 dos 10,9 GiB é
  calculado uma vez e fica em `build/v130/romfs.bin.sha256`).
- Esse executável usa a glibc do WSL (2.44 no Arch) e **não roda no Deck**; para o Deck é o passo `dist`.
- Vulkan no WSL é só o Dozen (Vulkan 1.2 sobre D3D12), sem `VK_EXT_external_memory_host`: o back end Vulkan não abre
  aqui. Testes com gráfico: no Deck, em Linux nativo ou num build Windows.
- Depurar: `gdb -p $(pgrep -x aoc) -batch -ex "handle SIGSEGV nostop noprint pass" -ex "thread apply all bt 15"`. As
  funções traduzidas se chamam `f_<endereço guest>`; a pilha guest sai da cadeia de `x29` do `Cpu` (o `c` do frame
  `rt_svc`), lida em `/proc/<pid>/mem`.

## 5. Pasta para o Deck (`dist`)

```sh
python3 tools/build.py --work ~/aoc-build dist                 # → <repositório>/dist/aoc-deck/
python3 tools/build.py --work ~/aoc-build dist --with-romfs    # põe também o romfs.bin (hardlink; cópia se não der)
```

- Compila o runtime e linka contra o sysroot **sniper** do Steam Runtime 3 (glibc 2.31; snapshot e SHA-256 fixados
  como no TotK Recomp), com Opus e libvpx estáticos do sysroot, zstd 1.5.7 estática compilada aqui e headers Vulkan
  1.4.363. O build confere que o executável não pede GLIBC acima de 2.31 (hoje pede no máximo 2.29).
- Na primeira vez baixa 1,2 GB (sysroot) e 2,5 MB (zstd) para `~/aoc-build/dl/`.
- A pasta: `aoc`, `aoc.sh` (lançador: `MESA_SHADER_CACHE_DIR` ao lado do jogo), `lib/libSDL3.so.0`, `exefs/`,
  `romfs-index.bin` e `romfs/romfs.bin`. O runtime acha `exefs/`, `romfs/` e `profile/` ao lado do executável
  (`main.c portable_paths`). Atualizar = rodar `dist` de novo e copiar `aoc` (o resto só muda com o jogo).
- Layout e passo a passo no Deck em [steam-deck.md](steam-deck.md).

## Testes do lifter (sem compilar o jogo inteiro)

```sh
python3 tests/flags_check.py
python3 tests/diff/lift.py --modules main,subsdk0,sdk --jobs 16
python3 tests/diff/func.py --modules main,subsdk0,sdk --functions 300 --jobs 16
python3 tests/jumptables_check.py --modules main,subsdk0,sdk
python3 tests/diff/simd.py && python3 tests/diff/atomic.py     # não usam arquivos do jogo
python3 tests/spin_waits_test.py && python3 tests/test_tools.py
```

## Windows nativo (testes numa GPU de PC)

O Deck usa sempre o `dist` do WSL. Para depurar gráficos numa GPU de PC, o mesmo `tools/build.py` compila no Windows
com o MSYS2 (UCRT64):

```sh
pacman -S mingw-w64-ucrt-x86_64-{clang,lld,llvm,ninja,sdl3,opus,libvpx,zstd,vulkan-headers,vulkan-loader,vulkan-memory-allocator,python,python-cryptography,python-lz4}
# o C gerado vem do WSL (\wsl.localhost\archlinux\root\aoc-build\generated -> C:\aoc-win\generated)
python3 tools/build.py --work /c/aoc-win --big-jobs 2 guest host   # aoc.exe em C:\aoc-win\host
```

Ao lado do `aoc.exe`: `SDL3.dll`, `libopus-0.dll` (de `C:\msys64\ucrt64\bin`), `aoc_xlate.exe` e `aoc_xlate.id`. O
tradutor sai do WSL com `dotnet publish <csproj> -c Release -r win-x64 --self-contained -p:PublishAot=false
-p:PublishSingleFile=true -p:InvariantGlobalization=true -p:RyuSrc=<árvore com os patches>` (NativeAOT só compila
para o sistema em que roda; o modo `--serve` mantém o processo vivo, então o JIT não pesa).

# Handover — estado do projeto para o próximo agente

Leia isto primeiro, depois `AGENTS.md` (regras) e `docs/plano.md` (fases). Atualizado em 2026-11-04 (sessão 2, no
notebook). Tudo aqui foi medido no dump do próprio dono do projeto; nada é estimativa salvo onde está dito.

## 0. Em uma frase

Port nativo (recompilação estática ARM64 → C → x86-64, Vulkan) de *Hyrule Warriors: Age of Calamity* 1.3.0 para o
**Steam Deck** (e PC). A metade CPU/host/Vulkan/Linux vem do pipeline **Astral Chain Recomp / TotK Recomp**; a metade
"jogo" vem do perfil de AoC do **nxnative** (que roda o AoC nativo em Mac/iPhone, mas executando o ARM64 original —
por isso não serve direto para x86).

## 1. Onde estamos

| Fase | Estado |
|---|---|
| 0 — inventário | **Quase fechada.** Falta: teste de tradução dos shaders (Ryujinx + `spirv-val`, precisa .NET 10). |
| 1 — lifter | **Fechada na prática.** Build completo rodou (~48 min no notebook, 0 falhas), `aoc --selftest` passa, tabela de 1 112 spin waits (`recomp/patches-v130.txt`). Pendentes menores: 1 jump table superconjunto no `subsdk0`, funções gigantes no gerador. |
| 2 — host/boot | **Portão B2 cumprido.** Runtime do Astral Chain + porta Linux do TotK em `runtime/`. Com `AOC_GPU=null`: laço principal a 30 fps (relógio 1×), 8 756 programas NVN, RomFS e save, **som não-silencioso** depois das telas do primeiro boot (A por `AOC_INPUT_SCRIPT`) e **vídeo de abertura decodificado** (VP9, ~1,3 ms/frame). |
| 3 — gráficos | Não começada. Não dá para testar Vulkan no WSL (só Dozen, Vulkan 1.2): precisa do Deck, Linux nativo ou build Windows. |
| 5 — Deck | `tools/build.py dist --with-romfs` monta a pasta única `dist/aoc-deck/` (sysroot sniper, GLIBC_2.29, romfs por hardlink, LEIA-ME, `aoc.ini`, saves em `profile/` ao lado do executável), testada de ponta a ponta no WSL. **Menu rápido** (L3+R3 segurado): 30 fps, resolução interna portátil/TV ao vivo, overlay. Falta rodar no Deck. |

Números-chave (detalhes em `docs/aoc.md`):

- Dump: base 1.0.0 (10,65 GiB), update 1.3.0 v327680, 4 DLCs (3001 licença, 3002, 3003 *Pulse of the Ancients*,
  3004 *Guardian of Remembrance*). Geração de chave 0x0B, SDK 9.6.0.
- Build IDs 1.3.0 (`tools/data/known-builds.json`) **batem** com o nxnative → os endereços `main+0x...` dele valem
  (conferir os bytes originais antes de usar cada um).
- Módulos: `main` 43,7 MiB, `subsdk0` 7,1 MiB (biblioteca de vídeo da Nintendo, base Android), `sdk` 12,6 MiB;
  66,5 MB no total → o host tem de reportar `mem_used` = 72 MB (senão `SetHeapSize` falha e `nnMain` retorna).
- NPDM: prioridade 44, core 0, pilha 1 MiB, **system resource 0**.
- RomFS 1.3.0 mesclado: 1 101 arquivos, 10,91 GiB, tudo em arquivos RDB da Koei Tecmo (entradas IDRK, zlib em
  blocos de 16 KB).
- Texturas: 40 198 G1T, **só BC1–BC7, nenhum ASTC** → o RDNA2 do Deck lê nativo.
- Shaders: **40 729 únicos** (37 045 pixel, 3 441 vertex, 241 compute, 2 geometry), ~602 MiB de código Maxwell;
  as chaves batem 1:1 com `nxnative/dm/games/01002B00111A2000/shader_map.tsv`. DLCs não trazem shaders.
- Imports do `main`: 383; 65 já têm override no Astral Chain/TotK. Sem exceções C++ nem `longjmp`.
- C gerado: ~600 MB em 377 arquivos; 35 **funções gigantes** no `main` (1–7 MB de C cada) levam 15–20 min cada
  para compilar a -O1 e até ~2–4 GB de RAM.

## 2. Decisões já tomadas (não reabrir sem motivo)

1. **Arquitetura A** (lifter + NVN HLE + Vulkan, linha Astral Chain). Plano B documentado: GPU LLE como o HWDER.
2. **Versão única 1.3.0** (+ DLCs). Outros builds são recusados.
3. **Compila-se no Windows pelo WSL2** (hoje no notebook, seção 3); o Deck **não compila nada**. O resultado é **uma
   pasta única** `dist/aoc-deck/` (`tools/build.py dist`, contra o sysroot sniper) que o dono copia para o cartão SD
   de **1 TB** do Deck (FTP, nuvem ou cabo). Layout em `docs/steam-deck.md`.
7. **Runtime = Astral Chain + porta Linux do TotK** (2026-11-04): o `recomp/` é o do Astral Chain e o runtime dele casa
   com o gerador; o TotK traz `platform/linux.c` e a SDL3. Variáveis `AOC_*`, arquivo `aoc.ini`.
4. Ritmo padrão "Original 30"; 60 fps é opcional e vem depois (três stubs de frame-step do nxnative).
5. Documentação em pt-BR.
6. O dump fica em `Game Files/` na raiz do repositório (ignorado pelo git). Saídas em `build/`, `generated/`,
   `dist/`, ferramentas externas em `toolchain/` — tudo ignorado.

## 3. Máquinas e lugares

Há duas máquinas Windows. **Desde 2026-11-04 o trabalho é no notebook** (decisão do dono).

| O quê | Notebook (atual) | PC principal (sessão 1) |
|---|---|---|
| Repositório | `C:\Users\gabri\Downloads\Age of Calamity\Age of Calamity` | `D:\Decomp\Age of Calamity` |
| CPU / RAM | i5-11400H 6c/12t, 15,7 GB (WSL limitado a 11 GB + 12 GB swap por `%USERPROFILE%\.wslconfig`) | i7-12700 |
| GPU | RTX 3050 Laptop + Intel UHD (no WSL só Dozen, Vulkan 1.2) | — |
| WSL | **Arch Linux** (`archlinux`, root, sem sudo); `~/aoc-build` com tudo gerado | Ubuntu quebrado (`ext4.vhdx` sumiu) |
| Referências | `refs/` (via `tools/fetch_refs.sh`) | `D:\Gits para projetos\switch-recomp\` |

Comum às duas:

| O quê | Onde |
|---|---|
| Repositório remoto (privado) | https://github.com/Azzulin/Blonde-Z-and-her-friends |
| Dump do jogo | `<repo>\Game Files\` (NSPs + `prod.keys` + `title.keys`) — nunca no git |
| RomFS mesclado e ExeFS extraído | `<repo>\build\v130\` (`romfs.bin` + `romfs.bin.sha256`, `exefs\`, relatórios dos censos) |
| hactool | `<repo>\toolchain\hactool-1.4.0-win\hactool.exe` |
| Trabalho do build (no WSL) | `~/aoc-build/`: `generated/`, `obj/`, `lib/libaoc_guest.a`, `host/aoc` (dev), `dist/aoc` (Deck), `toolchain/sniper`, `deps/`, `dl/` |
| Pasta do Deck | `<repo>\dist\aoc-deck\` (ignorada pelo git) |
| Alvo | Steam Deck, SteamOS 3.8 (kernel 6.16), cartão SD de 1 TB |

## 4. Como reproduzir tudo

```sh
# Windows: clique em build.bat (setup do WSL + extração do ExeFS + gen + guest + host; log em build\build-wsl.log)
# ou, dentro do WSL (Ubuntu ou Arch):
bash tools/setup_wsl.sh && source ~/.venvs/aoc/bin/activate
python3 tools/extract.py inventory && python3 tools/extract.py exefs
# RomFS mesclado (Windows): python tools/extract.py hactool-home && tools\windows\merge_romfs.bat
python3 tools/build.py --work ~/aoc-build --jobs 10 --big-jobs 4    # gen + guest + host (~50 min na 1ª vez)
~/aoc-build/host/aoc --selftest
AOC_GPU=null AOC_TRACE=perf ~/aoc-build/host/aoc                     # jogo sem GPU; matar com pkill -9 -x aoc
python3 tools/build.py --work ~/aoc-build dist                       # dist/aoc-deck/ (sysroot sniper)
```

Detalhes em `docs/building.md`, incluindo os testes do lifter.

## 5. Mapa do repositório

| Pasta | Conteúdo |
|---|---|
| `docs/` | `levantamento.md` (o jogo e as referências), `arquitetura.md`, `plano.md` (fases e portões), `aoc.md` (fatos medidos), `steam-deck.md`, `building.md`, `referencias.md`, este `handover.md`, `historico.md` |
| `recomp/` | lifter e gerador vindos do Astral Chain (MIT); só `layout.py` mudou; `jumptables.py` tem uma correção nossa em `_bounds` |
| `runtime/` | runtime do Astral Chain + porta Linux do TotK, adaptado ao AoC (ver `runtime/README.md`) |
| `tests/` | `test_tools.py` (sintético, roda no CI) e os testes diferenciais do Astral Chain (precisam do ExeFS) |
| `tools/` | `nx.py` (NSP/NCA/ticket/ExeFS/RomFS em Python), `extract.py`, `inspect_dump.py`, `census_*.py`, `build.py` (gen/guest/host/dist), `romfs_index.py`, `spin_waits.py`, `setup_wsl.sh`, `check_content.py`, `fetch_refs.sh`, `windows/*.bat/.ps1` |

## 6. Próximos passos (em ordem)

1. **Tradutor de shaders (Fase 3) — é o que impede jogar.** No Deck (2026-11-05) o jogo roda a 29,9 fps com o
   Vulkan do RADV, mas a tela fica preta: nenhum shader é traduzido. Trazer o tradutor Ryujinx 1.3.2 do Astral Chain
   (`tools/build_xlate.py`, `tools/xlate/`, `tools/vendor/ryujinx`, .NET 10 com NativeAOT) para Linux, empacotá-lo em
   `dist/aoc-deck/` e montar a extração KTGL. O Deck é acessível por SSH (`deck@192.168.100.130`, nome `steamdeck`,
   chave `~/.ssh/id_ed25519_deck` no notebook): ler `logs/aoc.log` lá.
2. **Som do vídeo de abertura** (silêncio enquanto o VP9 toca): a faixa de áudio do `.webm` passa pela biblioteca
   `movie` do `subsdk0`; o `ov_movie.c` só troca o decodificador de vídeo. Ver qual decodificador de áudio ela abre
   (`AOC_TRACE=ipc,audio`) e se cai no caminho Android/NvMM que não existe aqui. Roteiro de entrada usado:
   A em @6000, @8000, @10000, @12000, @14000, @16000 ms (`AOC_INPUT_SCRIPT`, formato em `runtime/input.c`).
   Sem entrada o jogo fica parado nas telas do primeiro boot, em silêncio — não é travamento.
3. **Fase 3 — shaders**: .NET 10 no WSL, tradutor Ryujinx 1.3.2 do Astral Chain (`tools/build_xlate.py`,
   `tools/xlate/`, `tools/vendor/ryujinx`) e extração KTGL (`nxnative dm/gfx/tools/shader_split.py`); `spirv-val`.
4. Correções de NVN do AoC (lista em `docs/plano.md`, Fase 3) quando houver imagem.
5. Jump table do `subsdk0+0x5da14` (superconjunto seguro) e funções gigantes no gerador (`musttail`), se o tempo de
   build incomodar (hoje ~48 min do zero; incremental leva 1–2 min).
6. DLC: `nn::aoc` hoje responde "nenhum DLC" (`ov_system.c`); montar os RomFS dos DLCs fica para a Fase 6.

## 7. Armadilhas já encontradas

- **Caminhos com espaço** ("Age of Calamity"): valores de variável do ninja vão ao shell como texto; usar
  `shell_arg` (aspas do shell) em `tools/build.py`, nunca o escape `$ ` do ninja (corrigido: o 1º build falhava todo).
- **glibc**: o executável do WSL (glibc 2.44 no Arch) não roda no Deck; só o do `dist` (sniper, no máx. 2.29). A SDL3
  do sniper liga direto em ALSA, PulseAudio, X11, Wayland, xkbcommon e libdecor — o SteamOS tem; para testar o binário
  do `dist` no WSL foi preciso instalar `alsa-lib libpulse libxi libxrandr libxss libxtst fribidi libxkbcommon libdecor`.
- **Log do runtime**: `logs/aoc.log` só é gravado quando a saída do processo **não** é um arquivo (rodando pelo
  Steam); com `> arquivo` tudo vai para o arquivo redirecionado.
- **Ambiente vence `cfg_set`**: uma variável `AOC_*` no ambiente, mesmo vazia, ganha das mudanças do menu.
- **`timeout` não mata o `aoc`** (SIGTERM não encerra o jogo): usar `pkill -9 -x aoc`.
- **gdb no `aoc`**: `handle SIGSEGV nostop noprint pass` (o write-watch usa SIGSEGV). Pilha guest: `c->x[29]`/`x[30]`
  no frame `rt_svc` e a cadeia de frames lida de `/proc/<pid>/mem` (endereço guest = endereço host).
- **curl e o repositório da Valve**: o download de 1,2 GB do sniper cai por HTTP/2 (erro 92); usar `--http1.1 -C -`.
- **Git Bash → wsl**: aspas e `$` se perdem em `wsl.exe ... bash -c '...'` com scripts longos; gravar o script num
  arquivo e rodar com `wsl -d archlinux -- bash /mnt/c/...` pelo PowerShell. Caminhos `/tmp/...` passados pelo Git
  Bash viram `C:/.../Temp` (usar `MSYS_NO_PATHCONV=1`).
- **Escapes em heredoc**: `\b` num literal Python dentro de heredoc vira backspace; conferir com `grep -P '\x08'`.

- **hactool e BKTR**: para a seção BKTR do update, `--romfs=` é ignorado; só `--section1=` grava (o nível RomFS
  final). E o hactool só abre NCAs soltos, não dentro do NSP.
- **PowerShell**: `New-Item -Target` trata `[` `]` dos nomes dos NSPs como curinga (usar `mklink`); `.ps1` sem BOM é
  lido como ANSI no PowerShell 5.1 (manter os scripts só em ASCII); os nomes dos NSPs têm `꞉` (U+A789), que o
  hactool do Windows não abre (usar hardlinks com nomes ASCII).
- **Ambiente Linux do Cowork no PC** (o shell que o agente usa no dono): 2 núcleos, 3 GB, sem `sudo`; ler do disco
  D é rápido (~150 MB/s), **escrever é lento (~11 MB/s)** — nada de gravar GBs por ele; processos em segundo plano
  morrem ao fim de cada comando; comandos têm limite de 3 min. Compilar código C de terceiros lá foi bloqueado pelo
  classificador de segurança; ferramentas próprias em Python rodam.
- **git nas pastas montadas**: use `git -c safe.directory=$PWD ...` (não mexer no `safe.directory` global).
- **Token do GitHub**: nunca gravar em arquivo nem em `.git/config`; usar `-c http.extraHeader=...` só no comando e
  filtrar o valor da saída. O dono foi orientado a gerar um token novo, porque o atual apareceu na conversa.
- **Chaves**: `prod.keys`/`title.keys` são lidos pelas ferramentas; valores nunca aparecem em saída, log ou commit.
  `tools/extract.py hactool-home` grava cópias só em `build/v130/tmp/` (ignorado) e o merge apaga ao terminar.
- **WSL e `/mnt/d`**: compilar sobre o disco do Windows é lento; o build usa `~/aoc-build`.
- **Funções gigantes**: a -O0 a de 3 MB passou de 7 GB de RAM e morreu — não é saída; as flags em
  `tools/build.py` (`BIG_EXTRA`) cortam ~40 % do tempo a -O1. O ninja limita quantas rodam juntas pela RAM.
- **Endereços do nxnative** só valem para estes build IDs; o nxnative é ARM64 nativo, então os patches dele
  (`patches.py`) precisam virar patches do lifter (`recomp/patches.py`), não cópia.

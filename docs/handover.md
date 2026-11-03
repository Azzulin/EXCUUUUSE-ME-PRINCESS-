# Handover — estado do projeto para o próximo agente

Leia isto primeiro, depois `AGENTS.md` (regras) e `docs/plano.md` (fases). Escrito em 2026-11-03, no commit seguinte
a `dacaabf`. Tudo aqui foi medido no dump do próprio dono do projeto; nada é estimativa salvo onde está dito.

## 0. Em uma frase

Port nativo (recompilação estática ARM64 → C → x86-64, Vulkan) de *Hyrule Warriors: Age of Calamity* 1.3.0 para o
**Steam Deck** (e PC). A metade CPU/host/Vulkan/Linux vem do pipeline **Astral Chain Recomp / TotK Recomp**; a metade
"jogo" vem do perfil de AoC do **nxnative** (que roda o AoC nativo em Mac/iPhone, mas executando o ARM64 original —
por isso não serve direto para x86).

## 1. Onde estamos

| Fase | Estado |
|---|---|
| 0 — inventário | **Quase fechada.** Falta: teste de tradução dos shaders (Ryujinx + `spirv-val`, precisa .NET 10). A lista de nomes NVN só sai com o jogo rodando (Fase 2). |
| 1 — lifter | **Geração e testes OK; build completo ainda não rodou.** 101 212 funções, 0 instruções não suportadas, testes Unicorn sem falha. Falta: build completo no WSL (`build.bat`), 1 jump table superconjunto no `subsdk0`, `simd.py`/`atomic.py`, funções gigantes. |
| 2 — host/boot | Não começada. Próximo grande bloco. |
| 3+ | Não começadas. |

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
3. **Compila-se no PC** (Windows + WSL2, i7-12700); o Deck **não compila nada**. O resultado será **uma pasta única**
   `dist/aoc-deck/` que o dono copia para o cartão SD de **1 TB** do Deck (FTP, nuvem ou cabo). Layout em
   `docs/steam-deck.md`.
4. Ritmo padrão "Original 30"; 60 fps é opcional e vem depois (três stubs de frame-step do nxnative).
5. Documentação em pt-BR.
6. O dump fica em `Game Files/` na raiz do repositório (ignorado pelo git). Saídas em `build/`, `generated/`,
   `dist/`, ferramentas externas em `toolchain/` — tudo ignorado.

## 3. Máquinas e lugares

| O quê | Onde |
|---|---|
| Repositório (privado) | https://github.com/Azzulin/Blonde-Z-and-her-friends — clone local principal em `D:\Decomp\Age of Calamity` |
| Dump do jogo | `<repo>\Game Files\` (NSPs + `prod.keys` + `title.keys`) — nunca no git |
| RomFS mesclado e ExeFS extraído | `<repo>\build\v130\` (`romfs.bin`, `exefs\`, relatórios dos censos) |
| hactool | `<repo>\toolchain\hactool-1.4.0-win\hactool.exe` (baixado à mão; fonte em `toolchain\hactool-1.4.0\`) |
| Repositórios de referência | `D:\Gits para projetos\switch-recomp\` (7 repos, tag `aoc-ref-2026-11-03`) e `aoc-dados\` (dados/formatos do AoC); `atualizar.sh` atualiza todos |
| Build | WSL2 Ubuntu, diretório `~/aoc-build` (no disco do Linux, não em `/mnt/d`) |
| Alvo | Steam Deck, SteamOS 3.8 (kernel 6.16), cartão SD de 1 TB |

**Estado do WSL no PC principal (2026-11-03):** a distro padrão `Ubuntu` está **quebrada** — o `ext4.vhdx` dela
sumiu (`Wsl/Service/CreateInstance/MountDisk/HCS/ERROR_PATH_NOT_FOUND`). O dono foi orientado a procurar o disco
(`Get-ChildItem C:\, D:\ -Recurse -Filter ext4.vhdx`) e, se não achar, `wsl --unregister Ubuntu` +
`wsl --install -d Ubuntu-24.04 --location D:\WSL\Ubuntu`. Por isso o build completo ainda não rodou.

## 4. Como reproduzir tudo

```sh
# Windows: clique em build.bat (setup do WSL + extração do ExeFS + geração + compilação; log em build\build-wsl.log)
# ou, dentro do WSL:
bash tools/setup_wsl.sh && source ~/.venvs/aoc/bin/activate
python3 tools/extract.py inventory                 # identifica base/update/DLCs pelo conteúdo dos NCAs
python3 tools/extract.py exefs                     # build/v130/exefs/ (lê o NSP no lugar, verifica hashes)
python3 tools/inspect_dump.py --exefs build/v130/exefs
python3 tools/census_imports.py --exefs build/v130/exefs --out build/v130/imports.json
# RomFS mesclado (Windows): python tools/extract.py hactool-home && tools\windows\merge_romfs.bat
python3 tools/extract.py romfs-index               # lista build/v130/romfs.bin e compara com a base
python3 tools/census_rdb.py --dlc                  # tipos nos RDB, formatos de textura
python3 tools/census_shaders.py --dlc              # inventário de shaders
python3 tools/build.py --work ~/aoc-build          # gera o C e compila (libaoc_guest.a)
```

Testes do lifter: ver o fim de `docs/building.md`.

## 5. Mapa do repositório

| Pasta | Conteúdo |
|---|---|
| `docs/` | `levantamento.md` (o jogo e as referências), `arquitetura.md`, `plano.md` (fases e portões), `aoc.md` (fatos medidos), `steam-deck.md`, `building.md`, `referencias.md`, este `handover.md`, `historico.md` |
| `recomp/` | lifter e gerador vindos do Astral Chain (MIT); só `layout.py` mudou; `jumptables.py` tem uma correção nossa em `_bounds` |
| `runtime/` | por enquanto só os cabeçalhos de CPU do código gerado (`cpu.h`, `simd.h`, `simd_fp.h`, `fma.c`) |
| `tests/` | `test_tools.py` (sintético, roda no CI) e os testes diferenciais do Astral Chain (precisam do ExeFS) |
| `tools/` | `nx.py` (NSP/NCA/ticket/ExeFS/RomFS em Python), `extract.py`, `inspect_dump.py`, `census_*.py`, `build.py`, `setup_wsl.sh`, `check_content.py`, `fetch_refs.sh`, `windows/*.bat/.ps1` |

## 6. Próximos passos (em ordem)

1. **Fazer o build completo rodar** no WSL do PC (`build.bat`) e registrar tempo e memória em `docs/aoc.md`.
2. **Funções gigantes**: medir quais dominam; atacar no gerador (quebrar em partes encadeadas por `musttail`) ou
   aceitar com as flags atuais se o tempo total no i7 for razoável.
3. **Jump table do `subsdk0+0x5da14`** (superconjunto seguro: 7 alvos contra 6): os "facts" de entrada de bloco em
   `recomp/jumptables.py` não usam a condição da aresta (`cmp w16,#5` nos predecessores).
4. Rodar `tests/diff/simd.py` e `tests/diff/atomic.py` (não usam dados do jogo).
5. **Fase 2**: trazer o runtime do Astral Chain/TotK (loader, kernel de 3 cores, SVCs, IPC, `nn::*`), com a porta
   Linux do TotK (`runtime/platform/linux.c`), até `nnMain` chegar ao laço principal com `gfx_null`. Aplicar as
   correções do AoC do nxnative: `mem_used` 72 MB, work buffer do áudio = tamanho do serviço (0x61d000),
   copyright framebuffer no-op, Opus multistream, "save do BotW existe?" → não.
6. **Teste de tradução dos shaders** (precisa .NET 10 no WSL): tradutor Ryujinx 1.3.2 do Astral Chain
   (`tools/vendor/ryujinx`, `tools/xlate/`) sobre o inventário + `spirv-val`. Usar `shader_facts.tsv` e
   `shader_pairs.tsv` do nxnative.

## 7. Armadilhas já encontradas

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

# Handover — estado do projeto para o próximo agente

Leia isto primeiro, depois `AGENTS.md` (regras) e `docs/plano.md` (fases). O plano de ação imediato e um prompt pronto
para uma sessão nova estão em `docs/proxima-sessao.md`. Atualizado em 2026-11-09 (sessão 5, no
notebook, build nativo do Windows na RTX 3050). Tudo aqui foi medido no dump do próprio dono do projeto; nada é
estimativa salvo onde está dito.

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
| 3 — gráficos | **Em andamento.** Deck (SSH) e, desde a sessão 3, **build nativo do Windows** (RTX 3050). A primeira batalha roda **175 s inteiros a 30 fps sem travar** no notebook (antes: travada de CPU ~frame 570 e perda do dispositivo na entrada da batalha; as duas corrigidas, seção 6). Sessão 4: a janela mostra os bytes do jogo como estão, os efeitos de partículas não têm mais rastros e a **imagem da batalha deixou de sair lavada** (views sRGB respeitadas na amostragem: luma 233 → 175). Aberto: um retângulo branco no centro da tela (na imagem do jogo). |
| 5 — Deck | `tools/build.py dist --with-romfs` monta a pasta única `dist/aoc-deck/` (sysroot sniper, GLIBC_2.29, romfs por hardlink, LEIA-ME, `aoc.ini`, saves em `profile/` ao lado do executável), testada de ponta a ponta no WSL. **Menu rápido** (L3+R3 segurado): 30 fps, resolução interna portátil/TV ao vivo, overlay. **Roda no Deck** (SteamOS 3.9.5, RADV): imagem igual à do PC, 30 fps até a batalha; na batalha **24,6 fps** (limitado pela CPU; a sombra dos pools custa ~30 ms por frame na thread que submete — próximo alvo). |

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
| Build nativo do Windows (notebook) | `C:\aoc-win\`: `generated/` (cópia do WSL), `lib/`, `host/aoc.exe` + `aoc_xlate.exe` + `SDL3.dll` + `libopus-0.dll`; scripts `build.sh`, `host.sh`, `battle.sh`, `hang.sh`. MSYS2 em `C:\msys64` (UCRT64: clang, lld, ninja, sdl3, opus, libvpx, zstd, vulkan, VMA, python + cryptography/lz4, gdb, spirv-tools, spirv-cross) |
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

Windows nativo (para testar numa GPU de PC; o Deck continua usando o `dist` do WSL): copiar `~/aoc-build/generated`
para `C:\aoc-win\generated` e, no shell UCRT64 do MSYS2,
`python3 tools/build.py --work /c/aoc-win --big-jobs 2 guest host` (~30 min do zero com 12 threads; o host sozinho
leva segundos). O tradutor sai do WSL: `dotnet publish ... -r win-x64 --self-contained -p:PublishAot=false
-p:PublishSingleFile=true` sobre `~/aoc-build/xlate` (script `C:\aoc-win\xlate_win.sh`), mais o `aoc_xlate.id`.
Rota até a batalha: `bash /c/aoc-win/battle.sh [VAR=valor ...]` (175 s, `tools/deck/input-route1.txt`, capturas a
partir de 100 s, `AOC_TRACE=perf`, vigia de travada).

## 5. Mapa do repositório

| Pasta | Conteúdo |
|---|---|
| `docs/` | `levantamento.md` (o jogo e as referências), `arquitetura.md`, `plano.md` (fases e portões), `aoc.md` (fatos medidos), `steam-deck.md`, `building.md`, `referencias.md`, este `handover.md`, `historico.md` |
| `recomp/` | lifter e gerador vindos do Astral Chain (MIT); só `layout.py` mudou; `jumptables.py` tem uma correção nossa em `_bounds` |
| `runtime/` | runtime do Astral Chain + porta Linux do TotK, adaptado ao AoC (ver `runtime/README.md`) |
| `tests/` | `test_tools.py` (sintético, roda no CI) e os testes diferenciais do Astral Chain (precisam do ExeFS) |
| `tools/` | `nx.py` (NSP/NCA/ticket/ExeFS/RomFS em Python), `extract.py`, `inspect_dump.py`, `census_*.py`, `build.py` (gen/guest/host/dist), `romfs_index.py`, `spin_waits.py`, `setup_wsl.sh`, `check_content.py`, `fetch_refs.sh`, `windows/*.bat/.ps1` |

## 6. Próximos passos (em ordem)

**Sessão 5 (2026-11-09) — ler primeiro; o plano passo a passo está em `docs/proxima-sessao.md`.**

- **Música e som das cinemáticas: corrigidos e medidos no notebook** (`audio_mixer.c` `mix_depth`: submixes que saem
  por splitter eram somados fora de ordem). 21 de 37 janelas de 5 s mudas → 1. O item 4 abaixo (som do vídeo de
  abertura) era o mesmo defeito. Falta ouvir no Deck.
- **Escrito e compilado, SEM medição:** (a) resolução nativa — patch sets `output`/`scene` em
  `recomp/patches-v130.txt`, `resolution.c` do AoC, perfil do Deck 1280×720 com cena 960×540; o C novo só existe no
  WSL (`~/aoc-build`), o guest do Windows em `C:oc-win` está atrasado; (b) sombra dos pools — `shadow_sync_pool`
  indica regiões paradas para congelar (substitui a ideia do `sgen` por região do item 0); (c) telemetria — linhas
  `sys:` a cada 10 s (`runtime/sysmon.c`: watts da APU, bateria, temperaturas, ventoinha, GPU, CPU) e
  `tools/deck/logsum.py`.
- **O Deck ainda roda o binário da sessão 4.** Atalho "Hyrule Warriors: Age of Calamity" criado no Modo Jogo
  (`shortcuts.vdf`; iniciar o `aoc` por SSH não serve: a janela fecha sem foco do gamescope).
- **Resolução "estranha" explicada:** o jogo renderiza sempre 1920×1080 (cena 1440×810), fixos em `nnMain`; o modo
  portátil não muda isso, e a janela do Deck mostra a redução bilinear de 1,5×.
- **Retângulo branco:** 45 partículas de UI (quads aditivos idênticos) empilhadas no centro porque as 45 matrizes da
  paleta do VS são iguais; o shader está certo. Falta achar por que não se movem nem somem (`aoc.md`, "Partículas de
  UI do retângulo branco").
- **Meta do dono:** consumo perto de 12 W no Deck, sem esquentar. Ainda não há medição de potência.
- Ferramentas novas: censo de vozes e mixes em `AOC_TRACE=audio`; `AOC_DUMP_UBO` lista índices e vértices de cada
  draw; no notebook `C:oc-win64.py`, `plt.py`, `dref.py`, `immscan.py`, `diag1.sh`, `wsl_gen.sh`, `wsl_build.sh`.

0. **Deck: a sombra dos pools custa ~30 ms por frame na batalha** (primeiro item da próxima rodada; plano em
   `docs/proxima-sessao.md`, Fase B). O runtime da sessão 4 está no Deck (enviado às 21h24 de 2026-11-06); imagem igual
   à do PC (luma 173–176, sem rastros). Medição limpa (sem o censo de páginas sujas, que o `AOC_TRACE=perf` ligava
   sozinho e custava 63 ms por frame; agora só com `AOC_DIRTY_CENSUS=1`): batalha **24,3–24,6 fps** (antes 12,8),
   GPU 24,6–26,8 ms por frame e 16,5 ms ociosa (9,8 ms à espera da próxima submissão); thread principal 68 % no
   código do jogo (~27,6 ms), 20 % esperando núcleo virtual, 12 % em `nvnSyncWait`. O write-watch ainda leva 28 ms
   por frame (~440 consultas sobre 17,7 GB): é a **sombra** (`vk_memory.c` `shadow_sync_pool`, padrão no Linux), que
   consulta o pool inteiro em cada uma das ~35 sincronizações por frame. Correção pensada: consultar só as regiões que
   o replay resolveu, com `sgen` por região (detalhes e a armadilha no `historico.md`, sessão 4, "Deck sem o censo").
   Números em `docs/aoc.md` ("Steam Deck na batalha"). `journalctl -b -1` de 2026-11-06: desligamento normal.
1. **Cor da janela — CORRIGIDA na sessão 4.** O jogo termina num alvo `RGBA8_SRGB` (NVN 0x38, pass 91/94) e codifica
   uma vez só (o tonemap sai linear: `c5[1].y = 0` pula o `pow(1/2,2)` dele, `c5[7].x = 1`, `c5[8].z = 1`); o Switch
   mostra esses bytes como estão. A apresentação agora lê a imagem do jogo por uma **view UNORM**
   (`gfx_present.c` `unorm_view_format`) num draw de tela cheia que substituiu o `vkCmdBlitImage` (`vk_blit.c`,
   `shaders/present_blit.frag`: bilinear no mapeamento do blit, texel a texel quando os tamanhos batem, barras pelo
   clear do passe); o FSR devolve a imagem dele para esse draw e o ajuste de cor lê pela mesma view. Conferido no mesmo
   frame (`AOC_SHOTS` + `AOC_SHOTS_FULL` × `AOC_PRESENT_SHOT`, script `C:\aoc-win\cmp\cmp.py`): janela = imagem do jogo
   com diferença média 0,08–0,16 e máxima ≤ 1 (arredondamento da bilinear) na redução com barras (o caso do Deck) e
   dos lados; ajuste de cor e FSR também conferidos (tabela em `historico.md`, sessão 4). A janela fica clara/lavada:
   é a imagem verdadeira; o véu (item 2) é o que sobra. Atenção: a saída do jogo é sempre 1920×1080 (o gerador não
   tem os patches de resolução; `AOC_OUTPUT_RES` e o modo portátil não a mudam), então no Deck e no notebook o caminho
   é a redução bilinear; o FSR só entra numa janela maior que 1920×1080.
   **Manifesto do Windows (sessão 4):** o `aoc.exe` agora leva `runtime/aoc.manifest` (DPI por monitor v2 e página de
   código UTF-8, via `runtime/aoc.rc` e `llvm-windres` no `tools/build.py`); `--probe-dpi` passa. No notebook não muda a
   imagem: a área de trabalho é 1600×900 físicos a 100 % (a janela pedida de 1920×1080 fica em 1604×881; tela cheia,
   1600×900).
2. **Imagem lavada na batalha — CORRIGIDA na sessão 4.** Causa: a view de amostragem usava sempre o formato da
   imagem (`vk_exec_draw.c` `get_view`) e ignorava o formato da view NVN. O jogo cria os mapas de cor BC7, BC3 e BC1
   como UNORM e os amostra por views sRGB (186 vínculos num frame da batalha: 105 BC7, 58 BC3, 23 BC1); lidos sem a
   decodificação sRGB, todo albedo saía claro demais e a cena passava muito da faixa do medidor de exposição do jogo
   (9,85–16), que travava no mínimo (0,0103). Agora a view usa o par sRGB/UNORM da imagem quando a view NVN pede
   exatamente ele (`sampled_view_format`, par em `vk_formats.c` `tex_srgb_twin`). Luma média no mesmo ponto da
   batalha: **233 → 175** (o nxnative, o mesmo código no Mac, mede 163 no começo da batalha); a rota inteira
   (configurações, abertura, cinemáticas, batalha) com cores certas. A investigação antiga (cubo de ambiente, céu
   procedural, exposição, denormais) está no `historico.md`, sessão 3; descartado também na sessão 4: o otimizador da
   AST do tradutor (traduzir tudo em modo debug não mudou o véu: luma 233 nos dois).
   **Retângulo branco fixo no centro (relato do dono):** com a cor certa ele aparece **na imagem do jogo**: branco
   puro, ~20×38 px em 1920×1080, no centro exato da tela. Localizado: é o **programa 720** do pass do HUD (VS
   `bc173f45`, FS `a57f4e05`, blend aditivo), material de UI no modo 12 (distorção) cujo alfa sai 1 (o da máscara
   RGBA8, 255 em todo texel) sobre o fundo transparente de um ícone BC3 que guarda RGB branco. O FS escolhe o modo
   por um `BRX` com tabela na c1 (`[1240, 2352, 1792, ...]`, entrada do cache `in/6575db294819747a`); o modo 12 cai no
   destino 1792, onde o alfa final é `_167.z` = o **alfa** da máscara (`_167` é o `.xyw` da textura C empacotado num
   `vec3`). Conferido: a tradução desse ramo e o mapeamento do `BRX` estão certos, então com esses dados o shader do
   Switch também pintaria o quad opaco. No Deck aparece igual (não é GPU nem driver). O defeito está no que chega ao
   draw: posição/escala do elemento (matriz `c3[6..8]` do VS; o `c3[8]` não saiu no dump), um uniforme que o jogo
   reescreve e nós lemos velho, ou um elemento que o jogo esconde por outro caminho — detalhes no `historico.md`,
   sessão 4, e em `docs/aoc.md` ("Material de UI do retângulo branco").
   - Ferramentas de diagnóstico de imagem: `AOC_CRUMB_DRAWS=1` + `AOC_VK_RECORDER=0` (breadcrumb por draw),
     `AOC_TEXEL_ZERO=<slots>` com `AOC_TEXEL_ZERO_FS=<prefixos de chave>` (zera buffer textures só nesses fragment
     shaders; o log diz quais casaram), `AOC_TEXEL_LOG_FS=<prefixo>` (endereço, formato, 16 palavras e o c3 do
     shader, com o frame), `AOC_TEXEL_TWIN=0`, `AOC_DUMP_LOG=<de>` para pegar frames de carga, `AOC_DUMP_TEX=WxH`,
     `AOC_TRACE=gfx` registra leituras de textura pequena. Hash do dump (FNV-1a do SPIR-V) → arquivo do cache: mesma
     conta sobre `shader-cache/*.spv`. GLSL com `spirv-cross --vulkan-semantics`. No `passes.txt` do dump,
     `vk145(145) ... view-nvn-fmt 0x4e` = imagem BC7_UNORM amostrada por view BC7_SRGB (foi assim que o véu apareceu).
   - **Perda de dispositivo residual:** aparece com o gravador (`vk_rec.c`, padrão na NVIDIA) **e** cópias de imagem
     para leitura (dumps, `AOC_SHOTS` a cada 1 s); nenhuma em mais de dez corridas normais e nenhuma com
     `AOC_VK_RECORDER=0` (inclusive com captura a cada 1 s). Suspeita: corrida entre o gravador e as cópias de
     leitura (as mesmas do print do menu e das miniaturas do flight recorder). No Deck (RADV) o gravador vem desligado.
   - **Gravador × chamadas diretas (corrigido):** `vk_quad_ind.c` chamava `vkCmdPushDescriptorSetKHR` por ponteiro direto
     no buffer do replay; com o gravador ligado o push entrava fora de ordem enquanto a thread do gravador ainda
     gravava → perdas de dispositivo na entrada da batalha. Agora vai por `rec_push`; 3 de 3 corridas limpas com o
     gravador ligado. `rec_records(cb)` (vk_rec.h) diz se o gravador grava aquele buffer; os breadcrumbs por draw
     (`AOC_CRUMB_DRAWS`) se recusam a rodar com ele.
   - **Rastros (linhas brancas) — CORRIGIDOS na sessão 4.** Causa no tradutor de shaders: o otimizador da AST do
     Ryujinx (`StructuredIr/AstOptimizer.cs`) propagava um `Ballot(true)` (operação unária de operando constante) para
     todos os usos, e um deles fica dentro de `if (lane == líder)`. Os computes de partículas que montam os quads
     indiretos (`0a66de99`, `d6c20785` no dump) fazem um append atômico agregado por warp: dentro do `if` só o líder
     está ativo, o voto contava 1, o contador avançava 4 vértices por warp em vez de 4×N e warps escreviam por cima dos
     quads uns dos outros (quads com vértices de partículas diferentes). Patch `tools/xlate/patches/0013`: ballot, voto e
     shuffle ficam onde o shader os calcula. Medido (capturas a cada 0,1 s entre 140 e 160 s, `C:\aoc-win\streaks.py`):
     20–28 frames com rastro em 201 → **0 em 201**; com o SPIR-V remendado à mão no cache, também 0. Tradutor novo:
     identidade `d10880c4…` (o cache de shaders esfria uma vez; o Deck precisa do `aoc_xlate` novo).
   - **Devolução precisa do mirror (sessão 4):** no modo mirror (GPU dedicada) a devolução VRAM → memória do jogo
     copiava cada faixa escrita inteira; agora grava só as palavras que a GPU mudou (pré-imagem num anel de 64 MiB,
     `shaders/wb_merge.comp`). Não era a causa dos rastros; ficou porque segue a semântica do Switch (a CPU pode
     escrever no resto da faixa com a submissão em voo) e tira GPU: batalha 4,28 ms × 5,97 ms por frame. Coerência
     conferida com `AOC_MEMORY=verify`: 0 divergências em ~30 milhões de páginas. `AOC_MIRROR_WB=whole` volta à cópia
     inteira. Descartados no caminho: buffer textures lendo memória velha (usam o mirror), escrita por storage texel
     buffer sem devolução (nenhum `imageStore` nesses shaders), escrita da GPU por DMA acendendo o write-watch (teste
     isolado: não acende).
   - **Denormais:** a RTX 3050 informa `shaderDenormPreserveFloat32 = false`; o SPIR-V do Ryujinx carrega inteiros
     em variáveis float (ex.: o índice do laço do filtro do cubo começa como a constante float 2,8e-45). Não explicou
     o véu, mas é um risco real; no Deck (RADV) dá para pedir `DenormPreserve`.
3. **Desempenho na batalha.** No notebook (i5-11400H) a batalha fica em 30 fps com folga: `AOC_TRACE=sched` mostra a
   thread principal 51% dormindo (`SleepThread(1 ms)` à espera do próximo frame) e os núcleos virtuais ocupados 1,09
   de 3; o maior custo dela era o replay (`nvnQueueSubmitCommands`, 21%). O perfil do Deck agora liga
   `REPLAY_ASYNC` (host 21% → 1%, mesma imagem). **No Deck** (sessão 4, medição limpa; item 0): 24,3–24,6 fps,
   limitado pela CPU. Frentes, em ordem: (a) a sombra dos pools (~30 ms por frame na thread que submete; item 0);
   (b) os 20 % (~8 ms) da thread principal à espera de um núcleo virtual — ela só pode rodar no núcleo 0 (máscara 1):
   quem o ocupa e se o `rt_spin_gate` (cede depois de 50 µs, `AOC_SPIN_HANDOFF_US`; o spin de `main+0x17496a0` já
   passa por ele) e as preempções servem para 4 núcleos do host; (c) o `nvnSyncWait` (11,6 %, `exe+0x96ac0e`,
   `nvn_api_core.c:488`): o que ele espera (replay atrasado ou GPU); (d) o código do jogo em si (~27,6 ms por frame,
   1,7× o do notebook). E **shaders antecipados**: a entrada da batalha ainda
   trava 20 s com o cache frio (pipeline 13,6 s, tradução 4 s; 13,5 s no Deck). O repositório do dono `Deck Zelda/totk-recomp-main` (TotK no Deck) resolve
   isso com um pacote de todos os programas VS+FS dos arquivos do jogo (`tools/shader_pack.py`) e um warm-up uma vez
   (`tools/linux/warmup.sh`, todos os núcleos menos um, retomável) — fazer o equivalente com o `census_shaders.py` e
   o `shader_pairs.tsv` do nxnative, no formato de semente do runtime (`--prepare-shaders`). Lá também: memory guard
   do GTT (o Deck deles congelou duas vezes com o GTT cheio) e pools de imagens.
4. **Som do vídeo de abertura** (silêncio enquanto o VP9 toca; medido com `AOC_TRACE=audio`: rms 0,0000 durante os
   ~80 s do `movie/Movie001.webm`, música normal antes). O `.webm` **não tem faixa de áudio** (só `V_VP9`; os 97
   vídeos estão em `movie/` e `movie_logo/`) e o jogo não cria `movie::Decoder` de áudio; o som vem de um stream do
   motor de som do KTGL dentro dos RDB. Saída exatamente zero (nem efeitos) sugere que o motor espera um sinal de
   sincronia do player de vídeo (relógio/timestamps do nosso decodificador VP9 do host) — começar por aí.
5. **Fase 3 — shaders**: .NET 10 no WSL, tradutor Ryujinx 1.3.2 do Astral Chain (`tools/build_xlate.py`,
   `tools/xlate/`, `tools/vendor/ryujinx`) e extração KTGL (`nxnative dm/gfx/tools/shader_split.py`); `spirv-val`.
6. Correções de NVN do AoC (lista em `docs/plano.md`, Fase 3) quando houver imagem.
7. Jump table do `subsdk0+0x5da14` (superconjunto seguro) e funções gigantes no gerador (`musttail`), se o tempo de
   build incomodar (hoje ~48 min do zero; incremental leva 1–2 min).
8. DLC: `nn::aoc` hoje responde "nenhum DLC" (`ov_system.c`); montar os RomFS dos DLCs fica para a Fase 6.

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
- **Uma instância só**: um `aoc.exe` esquecido faz o próximo sair com código 1 logo depois de carregar os shaders.
  `TaskStop` de um comando em segundo plano mata o shell pai, mas um `bash script.sh` filho continua relançando o
  jogo — procurar com `ps -ef | grep <script>` e matar.
- **MSYS2 pelo PowerShell**: `$env:MSYSTEM="UCRT64"; $env:CHERE_INVOKING="1"; & C:\msys64\usr\bin\bash.exe -lc "..."`.
  O `ninja` do Windows não usa shell: `tools/build.py` escreve aspas duplas e não usa `rm` quando `os.name == "nt"`.
- **RAM no notebook**: o WSL segura memória; `wsl --shutdown` antes do build do guest no Windows.
- **Travada intermitente**: o vigia (`AOC_HANG_SECS`, padrão 10 s) registra o estado de cada thread; a entrada da
  batalha com cache frio passa de 6 s sem present e aparece no log sem ser travada (só tradução/pipelines).
- **Endereços de pool mudam entre execuções** (às vezes): conferir em `passes.txt` antes de usar `AOC_DUMP_BUF`.
- **Símbolos do SDK**: `sdk+0x...` vira nome pela tabela de exports do NSO (`recomp/nso.py`), e uma chamada de PLT do
  `main` (adrp/ldr x16/x17) pelo `JUMP_SLOT` do GOT — script de uma página, ver o histórico da sessão 3.

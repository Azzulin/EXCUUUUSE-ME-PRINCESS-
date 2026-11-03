# Levantamento — port nativo de *Hyrule Warriors: Age of Calamity* para PC / Steam Deck

Data: 2026-11-03. Tudo abaixo vem de leitura direta dos repositórios de referência nas revisões fixadas em
[referencias.md](referencias.md). Números marcados **(a medir)** ainda precisam ser confirmados no nosso próprio dump
na Fase 0.

---

## 1. O que é o jogo, do ponto de vista técnico

| Item | Valor | Fonte |
|---|---|---|
| Title ID | `01002B00111A2000` | perfil nxnative |
| Versão-alvo | **1.3.0** (v327680), base + update + DLCs | perfil nxnative / MacNativeGames |
| Engine | Koei Tecmo **KTGL** sobre **NVN** (não é engine da Nintendo) | perfil nxnative |
| SDK Nintendo | **9.6.0** | perfil nxnative |
| Módulos ExeFS | `main`, `subsdk0` (biblioteca de vídeo da Nintendo, *NintendoSDK_movie*), `sdk` (+ `rtld`, descartado) | perfil nxnative |
| Build IDs 1.3.0 (prefixo) | `main c3cf52bf2b05d7310884971b50bcccb8` · `subsdk0 3ab92c3444d4ece2f52417b5d8ee86eb` · `sdk 95832210b36121e88b4f9b7b66239dad` | perfil nxnative |
| Tamanho dos módulos | 66,6 MB somados (maior que os 64 MB que o host costuma reportar como "memória usada") | README nxnative AoC |
| NPDM | sem *system resource* (META +0x14 = 0) → o jogo usa `SetHeapSize` | README nxnative AoC |
| Heap | ~3,2 GB (`0xc8c00000`), 15 sub-heaps somando 3098 MB; heap gráfico de 866 MB | README nxnative AoC |
| RomFS | arquivos **RDB** da Koei Tecmo: `asset/*.rdb` (índice `_DRK0000`), `asset/*.rdb.bin*` e `asset/data/*.file` (entradas `IDRK`, zlib em blocos de 16 KB). DLC adiciona `.rdb.bin3_0` | README nxnative AoC |
| Shaders | **40 726** saídas GLSLC (37 043 pixel, 3 440 vertex, 241 compute, 2 geometry) em containers G2S (`_S2G3000`), um `_DOK0000` com 151 shaders de sistema, e ~117 embutidos no `main`. `asset/system.rdb.bin*` sozinho tem 2,3 GB descomprimido | README nxnative AoC |
| Áudio | KTSL (motor de som da Koei Tecmo) sobre `audren` REV8, 48 kHz; Opus multistream "por hardware" | README nxnative AoC |
| Vídeos | VP9 (WebM) decodificado para NV12 e copiado pelo jogo para texturas R8 1280×720 + RG8 640×360 | README nxnative AoC |
| Ritmo | 30 fps no Switch, passo fixo por update (3 relógios: tarefa KIDS, bloco de frame-rate da batalha, frame-rate do device KTGL) | patches.py nxnative |
| Config do device KTGL | `{1920, 1080, 3, 9, 5, interval 2, 9, …}` montada no `nnMain` | patches.py nxnative |
| Tamanho em disco do dump | **(a medir)** base + 1.3.0 + DLCs | — |
| Formatos de textura (ASTC × BCn) | **(a medir)** — decide o custo no Steam Deck, que não tem ASTC nativo | — |

### Peculiaridades que já derrubaram outros ports deste jogo

Cada item abaixo foi **descoberto e resolvido** no nxnative (iPhone/Mac). Para nós são conhecimento pronto — só muda a
forma de implementar (lifter x86 + Vulkan em vez de ARM64 nativo + Metal).

1. **`nnMain` retorna em silêncio logo após `nv::InitializeGraphics`** se o host reportar 64 MB de memória usada: os
   módulos têm 66,6 MB, `SetHeapSize` falha, o malloc do jogo nunca é montado. Correção: reportar 72 MB
   (`mem_used 0x4800000`).
2. **Thread principal fica girando num `YieldThread` após `OpenAudioRenderer`**: o tamanho de work buffer do
   renderer de áudio tem que ser o do *serviço* (0x61d000), não o do renderer local do SDK 9.6 (0x760000).
   Senão o 4º player do KTSL não aloca e o primeiro arquivo de som (ASRS) nunca carrega.
3. **`oe::InitializeCopyrightFrameBuffer`** lê ponteiro nulo — as três funções de copyright viram no-op.
4. **`HardwareOpusMultiStreamDecoder`**: o construtor importado precisa construir o decoder de software do SDK no lugar.
5. **Vídeo de abertura preto**: binding de programa *compute* tem que ser separado do de gráficos; e as texturas do
   vídeo são escritas pela CPU e publicadas com `nvnMemoryPoolFlushMappedRange` (precisa fazer upload nesse ponto).
6. **Listas de luz e decal** (slots 16–21, 16 438 shaders) leem *buffer textures* com fetch 1D. Em Vulkan isso é
   um `texelBuffer` nativo — mais simples que o truque de "row wrap" que o Metal exigiu.
7. **Atributos de vértice Half2/Short2 lidos como inteiros** pelos soldados: Maxwell aceita, Vulkan exige que o tipo do
   formato bata com o tipo da entrada do shader → conversão (no shader é o caminho barato).
8. **Batalhas com 1 000–2 800 dispatches de compute por frame** e até 28 000 `RegisterTexture` por frame (anel de IDs):
   precisa de cache de *views* por textura e dispatches baratos, senão a CPU de replay explode.
9. **Constant buffer c1 grande** nos shaders dos soldados (maior que o tamanho fixo antigo).
10. **Jump tables de bytes indexadas por x30** (`main+0x138216c`) — o lifter precisa reconhecer esse padrão.
11. **Desenhos indiretos**: efeitos guiados pela GPU são *quads* indiretos convertidos para indexados por um compute.
12. **8 705 programas montados no primeiro frame** (~10 s no Mac) → shaders precisam ser preparados antes (AOT).
13. **60 fps exige mexer nos três relógios ao mesmo tempo**; mexer só no intervalo de present dobra a velocidade do jogo.
    120 fps está desabilitado no MacNativeGames porque timers de gameplay andam em ticks inteiros de 60 Hz, e a
    cutscene da torre da Impa acelera a 60 fps.
14. Slots 8/9 de três vertex shaders esperam textura **3D** e recebem 2D — em aberto.

---

## 2. Projetos de referência — o que cada um resolve

| Projeto | Arquitetura | Plataforma | O que serve para nós |
|---|---|---|---|
| **astral-chain-pc-recomp** (a referência que você indicou) | ARM64 → C (lifter LAS) + host `nn::*` + NVN HLE + back end **Vulkan 1.3** | Windows (Linux em andamento) | **Esqueleto inteiro do pipeline x86-64**: lifter, kernel com 3 cores virtuais e preempção, IPC, áudio, NVN→Vulkan, ASTC, FSR1, menu ImGui, instalador que compila na máquina do jogador, *content guard*. Mostra como adaptar o pipeline do TotK a outro jogo em poucas semanas. |
| **totk-pc-recomp** | Mesmo pipeline (é a origem do Astral Chain) | **Windows e Linux**, perfil de **Steam Deck** | Tudo que é Linux/Deck já feito: write-watch com `userfaultfd` + `PAGEMAP_SCAN` (kernel ≥ 6.7), pools "sombra" no RADV, AppImage com sysroot do Steam Runtime *sniper* (glibc 2.31), Mesa cache fora do `~/.cache`, temp no cartão SD, perfil `device_profile = deck` (1280×800, 16:10, 40 fps). |
| **nxnative** — `dm/games/01002B00111A2000` | ARM64 **executado nativamente** + host + NVN→Metal | iPhone/Mac | **Todo o conhecimento específico do AoC 1.3.0**: perfil, build IDs, memória, áudio, patches de 60 fps, extração de shaders KTGL (RDB/IDRK/G2S/_DOK), tabelas de shaders (`shader_map`, `shader_pairs`, `shader_facts`). |
| **MacNativeGames** — `games/aoc` | Port do nxnative isolado para macOS | Mac (Apple Silicon) | Jogável na primeira missão com áudio e controle; documenta passo dinâmico de frame, timing ABI v3, problema da cutscene a 60 fps, estatísticas de shader. `ANALYSIS.md` é uma auditoria excelente das lições de 13 ports. |
| **HWDER** (Hyrule Warriors: Definitive Edition) | ARM64 → C de **todos** os módulos, inclusive o driver NVN; processador de comandos Maxwell + tradutor SASS→SPIR-V próprios (abordagem "LLE") | Windows e **Linux**, testado no **ROG Ally (Bazzite)** | Mesmo estúdio/engine (geração anterior). Prova que a abordagem LLE funciona num portátil x86 e é o **plano B** caso o NVN HLE não feche. Boas notas de Linux/handheld (Add to Steam, Game Mode, write-watch). |
| **LAS Recomp** | Lifter original + back end Vulkan próprio | Windows | Origem do lifter, testes diferenciais contra Unicorn. |
| **SavageWindRecomp** | Port de BotW | Windows | Checagem de preempção em chamadas indiretas, menu/overlay. |

> Todos os projetos acima são **MIT** (ou zlib/BSD nas partes de terceiros). Código GPL (yuzu, suyu, Ryujinx fora do
> tradutor de shader 1.3.2 já usado) é só leitura de comportamento — nunca copiar.

### A peça que falta

Ninguém ainda juntou as duas metades:

- **nxnative/MacNativeGames** sabem tudo do AoC, mas executam o código ARM64 diretamente → **não rodam em x86-64**
  (Steam Deck, PC).
- **Astral Chain/TotK Recomp** rodam em x86-64 e Linux/Deck, mas não conhecem o AoC.

O projeto é exatamente essa união: **CPU + host + Vulkan + Linux do lado TotK/Astral Chain, e conhecimento de jogo do
lado nxnative.** O próprio Astral Chain foi feito assim (CPU da LAS + jogo do MacNativeGames).

---

## 3. Abordagens possíveis

| | A. Lifter + NVN HLE (linha TotK/Astral Chain) | B. Recompilar tudo + GPU LLE (linha HWDER) | C. ARM64 nativo (nxnative) | D. Emulador |
|---|---|---|---|---|
| CPU | ARM64 → C → x86-64 | ARM64 → C → x86-64 | roda o ARM64 original | JIT |
| Fronteira com o SO | funções `nn::*` + poucos serviços IPC | SVCs + todos os serviços IPC reais | `nn::*` | SVCs + IPC |
| GPU | API NVN reimplementada → Vulkan | driver NVN original recompilado; nós emulamos o Maxwell (pushbuffer, macros) | NVN → Metal | Maxwell |
| Shaders | Tradutor Ryujinx 1.3.2 (MIT) → SPIR-V, AOT | tradutor próprio | Ryujinx → MSL | Ryujinx |
| Roda no Deck? | **Sim** | **Sim** | Não (ARM) | Sim, mas não é o objetivo |
| Reaproveita o conhecimento AoC do nxnative | **Quase todo** (mesma família de front end NVN: d2r-mobile → nxnative) | Parcial (CPU/serviços sim; GPU não) | — | — |
| Custo no Deck | Menor: sem decodificar pushbuffer | Maior: processador de comandos na CPU, 4 núcleos Zen 2 | — | Maior |
| Risco | Semântica NVN não documentada (mas o AoC já foi mapeado) | Muito trabalho de GPU do zero | — | — |

**Decisão recomendada: A**, com B como contingência documentada. Detalhes em [arquitetura.md](arquitetura.md).

---

## 4. Alvo de hardware

| | Nintendo Switch (docked) | **Steam Deck** | PC mid-end (referência) |
|---|---|---|---|
| CPU | 4× Cortex-A57 @ 1,02 GHz (3 para o jogo) | Zen 2, 4C/8T, até 3,5 GHz, AVX2/FMA (x86-64-v3) | 6C/12T moderno |
| GPU | Maxwell 256 núcleos @ 768 MHz (~0,4 TFLOPS) | RDNA2 8 CU @ até 1,6 GHz (~1,6 TFLOPS), driver **RADV** | RX 6600 / RTX 3060 |
| Memória | 4 GB | **16 GB LPDDR5 compartilhada** CPU/GPU | 16 GB + VRAM |
| Tela | TV 1080p / 720p portátil | **1280×800 (16:10)**, LCD 60 Hz / OLED 90 Hz | 1080p 16:9 |
| Energia | — | 4–15 W de APU | — |
| SO | Horizon | SteamOS 3.8 (kernel 6.16 → atende o requisito ≥ 6.7 do write-watch) | Windows 10/11 ou Linux |

Pontos que pesam no Deck:

- **Sem ASTC nativo no RDNA2** → decodificador em compute (já existe no Astral Chain) ou recodificar para BC uma vez
  na instalação e guardar em cache. Depende do censo de texturas da Fase 0.
- **Só 4 núcleos**: o custo vai estar no *replay* NVN→Vulkan na CPU (dispatches, binds de textura, uploads de pool),
  não no código do jogo — o código do AoC foi feito para 3 A57 a 1 GHz.
- **Memória unificada**: a cópia "sombra" dos pools que o TotK usa no Linux custa ~1,1 GB extra; com 16 GB e heap de
  3,2 GB do jogo, cabe com folga.
- **Cartão SD**: leitura aleatória lenta → evitar descomprimir o RomFS inteiro; caches de shader/pipeline no SD.

Orçamento de disco (32 GB no SD) em [steam-deck.md](steam-deck.md).

---

## 5. Questões em aberto para a Fase 0

1. Tamanho real do RomFS mesclado (base + 1.3.0 + DLCs) — cabe nos 32 GB junto com caches?
2. Proporção ASTC × BCn nas texturas G1T do KTGL.
3. Tamanho do `main` e número de funções/jump tables que o lifter vai gerar → tempo de compilação no PC e no Deck.
4. Lista de imports `nn::*` do SDK 9.6.0 que não estão nos ~178 overrides herdados do TotK.
5. Lista de nomes NVN pedidos via `nvnBootstrapLoader` (o nxnative registra 523) contra os 537 do Astral Chain.
6. Se o `main` usa `__cxa_throw`/`_Unwind_*`/`longjmp` (afeta a otimização de registradores *callee-saved* do lifter).
7. Como os DLCs montam (AddOnContent `aoc:u`, arquivos `.rdb.bin3_0`).

# Arquitetura

Como o build de Switch de *Age of Calamity* 1.3.0 vira um programa nativo x86-64 para Linux (Steam Deck) e Windows.
A justificativa da escolha está em [levantamento.md](levantamento.md), seção 3.

Resumo: **a metade CPU/host/Vulkan/Linux vem do pipeline TotK Recomp → Astral Chain Recomp; a metade "jogo" vem do
perfil AoC do nxnative/MacNativeGames.**

```
 dump do usuário (base + 1.3.0 + DLC, prod.keys)       ← nunca entra no git
        │  tools/extract.py (hactool + BKTR)
        ▼
 ExeFS (main, subsdk0, sdk, main.npdm)   RomFS (RDB/IDRK)
        │                                   │
        │ recomp/ (lifter ARM64 → C)        │ tools/shader_census.py (G2S/_DOK/main)
        ▼                                   ▼
 generated/*.c  ──clang/lld──►  aocrecomp (binário)   shaders/*.spv (AOT, tradutor Ryujinx 1.3.2)
                                   │
                 runtime/: kernel · IPC · nn::* · áudio · RomFS · NVN front end · Vulkan back end · SDL3
```

## 1. Entrada

- Base 1.0.0 + update 1.3.0 (v327680) + DLCs, NSP/XCI, com as chaves do console do próprio usuário.
- Extração e mescla do update (BKTR) com hactool, como `tools/extract.py` do Astral Chain/TotK.
- Verificação: build IDs dos três módulos contra `tools/data/known-builds.json` e SHA-256 do ExeFS/RomFS gravados
  localmente em `build/` (nunca no git). `tools/inspect_dump.py` faz a primeira parte já na Fase 0.
- Versão única: **1.3.0**. Qualquer outro build é recusado antes de gerar código.

## 2. CPU: ARM64 → C

- Base: `recomp/` do Astral Chain (lifter LAS reescrito para escala TotK): uma função C por função guest, `BL` vira
  chamada direta, saltos indiretos passam por `rt_dispatch` (tabela por endereço, `musttail`).
- Módulos: `main`, `subsdk0`, `sdk`. O `rtld` é descartado; o host faz a ligação dinâmica.
- Adaptações já sabidas para o AoC:
  - jump tables de bytes indexadas por `x30` (padrão em `main+0x138216c`, documentado pelo nxnative);
  - `recomp/layout.py` com o layout de memória do AoC (sem região fixa de RomFS como no Astral Chain — o AoC usa
    `MountRom` e RDB; confirmar na Fase 2);
  - checar *exceptions* C++ / `longjmp` antes de confiar nos registradores *callee-saved* (`--no-callee-saved-trust`).
- Patches de jogo (60 fps, etc.) entram como **patches do lifter** num arquivo `recomp/patches-v130.txt`, com os
  bytes originais conferidos — não como edição do C gerado. Os três stubs de frame-step do nxnative
  (`main+0x166dab4`, `main+0x166dc60`, `main+0x8d94b0`) precisam ser reescritos nesse formato.
- Testes: diferencial contra Unicorn (só em teste, nunca linkado) para cada classe de instrução, funções inteiras e
  jump tables (0 divergências).
- Memória: endereço guest = endereço host, abaixo de 2^39. Heap ~3,2 GB, `mem_used` reportado = 72 MB.

## 3. Host (Horizon OS de mentira)

- Kernel do Astral Chain: cada thread guest é uma thread do host; **3 cores virtuais** com afinidade e preempção por
  prioridade (o KTGL tem `KIDSTaskScheduler` com threads por core), portão de *spin-wait*, preempção assíncrona
  (no Linux: sinal em vez de `SuspendThread`).
- Fronteira do SDK nas funções `nn::*` importadas (censo na Fase 0). Serviços IPC reais só onde o SDK chama por
  dentro (`audren:u`, `sm:`, e o que o censo mostrar).
- Específico do AoC (vindo do nxnative):
  - `mem_used 0x4800000`, `sys_resource 0` lido do NPDM;
  - work buffer do renderer de áudio = tamanho do **serviço** (0x61d000 para os parâmetros do jogo), backend local
    dimensionado à parte;
  - `oe::InitializeCopyrightFrameBuffer` / `SetCopyrightImage` / `SetCopyrightVisibility` → no-op;
  - `HardwareOpusMultiStreamDecoder` → decoder multistream de software (libopus);
  - "existe save de BotW?" → não.
- Vídeo: `subsdk0` (NintendoSDK_movie) é código guest; se ele chamar decodificação por hardware, substituir por libvpx
  (VP9), como o `ov_movie.c` do TotK.
- Plataforma: `runtime/platform/` com `linux.c` e `win32.c`; janela, entrada e áudio por **SDL3**.

## 4. Gráficos: NVN → Vulkan 1.3

- Front end NVN do Astral Chain (linha d2r-mobile → MacNativeGames). O nxnative é sucessor do mesmo front end, então
  as correções do AoC são portáveis por conceito:
  - binding próprio para programa de compute;
  - `nvnTexturePoolRegisterImage`;
  - draws/dispatches indiretos lidos pela GPU (quads indiretos → indexados por compute);
  - cache de *views* de textura por serial de textura (o KTGL registra num anel de IDs antes de cada bind);
  - `tex_flush_upload`: upload ao `FlushMappedRange` para as texturas de vídeo;
  - c1 grande / alocado dinamicamente;
  - texturas 3D nos slots 8/9 (em aberto).
- Back end Vulkan do Astral Chain: replay no `QueueSubmitCommands`, VMA, `VK_EXT_graphics_pipeline_library`,
  snapshot de uniforms, thread de gravação, FSR1, ASTC por compute.
- No Vulkan, duas coisas ficam **mais simples** que no Metal:
  - buffer textures com fetch 1D → `VkBufferView` (texel buffer), sem "row wrap";
  - sem limitação de tile/TBDR do Apple.
- E uma fica **mais difícil**: entradas inteiras lidas de atributos Half2/Short2 — Vulkan exige tipo igual. Caminho
  preferido: na tradução do shader, declarar a entrada como float/uint conforme o formato real e converter dentro do
  SPIR-V (equivalente às *shadow vertex inputs* do nxnative), em vez de converter vértices na CPU.
- Shaders: tradutor Ryujinx 1.3.2 (MIT) compilado como processo separado; extração KTGL portada do
  `shader_split.py` (RDB → IDRK → zlib em blocos → G2S/`_DOK`/GLSLC, controles de 0x850 bytes, compute sem
  cabeçalho). **Tudo AOT na instalação** (40 726 shaders) e pipelines pré-montados a partir de uma lista de chaves
  gravada em jogo.

## 5. Ritmo de frame

- Padrão: **"Original 30"** — o jogo como no Switch (intervalo 2, relógios intactos).
- Opcional: 60 fps via os três stubs de frame-step (tarefa KIDS, bloco de frame-rate da batalha em `main+0x269e150`,
  config do device KTGL), apresentando cada frame assim que pronto (`fps_hold off`).
- 40 fps (modo 40 Hz do Deck) **não é trivial**: os stubs calculam "vsyncs por update" = 60 / cap como inteiro.
  Fica como pesquisa da Fase 6; o limitador de 40 fps sobre a lógica a 30 não ajuda.
- 120 fps: fora do escopo (timers de 60 Hz em ticks inteiros).

## 6. Toolchain

- Clang + LLD (o C gerado usa `__int128`, `musttail`, tipos vetoriais), Ninja, Python (uv), .NET 10 (tradutor),
  Vulkan SDK/headers, SDL3, libopus, libvpx, zstd, VMA.
- **Build no PC, jogo no Deck**: compilar no WSL2/Ubuntu do PC contra o sysroot *sniper* do Steam Runtime
  (glibc 2.31) e copiar só a pasta final para o cartão SD. Compilar o C gerado no Deck é possível, mas lento e pede
  dezenas de GB temporários.
- Testes em tempo de execução: no Deck ou em Linux nativo (o kernel do WSL2 não garante `PAGEMAP_SCAN` e a GPU no WSL
  não é RADV). Windows nativo também serve para depuração.

## 7. Regras de conteúdo

- Nada do jogo entra no git: dump, chaves, ExeFS/RomFS extraídos, C gerado, shaders traduzidos, caches, prints,
  saves. Tudo isso vive em `build/` e `generated/` (ignorados).
- Todo arquivo emitido pelo gerador leva o marcador `GENERATED_MARKER` (`tools/check_content.py`).
- `tools/check_content.py --staged` roda antes de cada commit (hook em `.githooks/`) e no CI.
- Código copiado só de MIT/BSD/ISC/zlib/Apache-2.0, com cabeçalho preservado e linha no `THIRD_PARTY_NOTICES.md`.

# Plano de trabalho

Fases com **portões de aceitação**: uma fase só fecha quando a evidência do portão existe (log, captura, teste). Um
processo que não trava, FPS alto ou tela preta **não** contam como sucesso.

Prioridade em todas as fases: **Steam Deck primeiro**, PC mid-end como segundo alvo (vem quase de graça do mesmo
código Linux/Vulkan; Windows é útil para depurar).

As estimativas são de esforço de uma pessoa com ajuda de agentes, baseadas no ritmo do Astral Chain (que chegou à tela
de título em poucas semanas partindo de um pipeline pronto). São ordens de grandeza, não compromissos.

---

## Fase 0 — Fundação e inventário · ~1 semana

Objetivo: saber exatamente com o que estamos lidando, sem escrever nada de runtime.

- [x] Repositório git com regras de conteúdo, hook e CI (`tools/check_content.py`).
- [x] `tools/fetch_refs.sh` clona as referências em `refs/` nas revisões fixadas.
- [ ] Ambiente no WSL2/Ubuntu: clang/lld 18+, ninja, uv, .NET 10, Vulkan headers, SDL3, opus, libvpx, zstd.
- [x] `tools/extract.py`: inventário dos pacotes, ExeFS do 1.3.0 e listagem do RomFS da base e dos DLCs, direto do NSP.
- [x] Mesclar o RomFS da base com o patch BKTR do 1.3.0 (`tools/windows/merge_romfs.bat` + hactool.exe) → `build/v130/romfs.bin`.
- [x] `tools/inspect_dump.py` confere build IDs, NPDM e tamanhos — **build IDs 1.3.0 conferidos**.
- [ ] Censos (resultados em `docs/aoc.md`, sem dados do jogo, só números):
  - [x] imports dos módulos (`tools/census_imports.py`) — falta cruzar com os overrides herdados;
  - [ ] nomes NVN pedidos pelo jogo × `nvn_procs.inc`;
  - [ ] instruções/funções/jump tables por módulo (dry-run do lifter);
  - [ ] shaders (contagem por estágio, tamanhos de controle) — portar `shader_split.py`;
  - [x] formatos de textura nas G1T — só BCn, nenhum ASTC (`tools/census_rdb.py`);
  - [x] tamanho do RomFS da base, do 1.3.0 mesclado e dos DLCs;
  - [x] tipos de dados nos RDB (`tools/census_rdb.py`);

**Portão A:** build IDs batem com 1.3.0; censos registrados; formatos de textura conhecidos (resultado: só BCn).

## Fase 1 — CPU: lifter para os três módulos · ~2 semanas

- [ ] Trazer `recomp/` do Astral Chain (MIT) com atribuição; gerador com marcador.
- [ ] `layout.py` do AoC (bases dos módulos, heap 3,2 GB, alias, pilhas).
- [ ] Padrão de jump table de bytes indexada por `x30`.
- [ ] Decidir `--no-callee-saved-trust` a partir do censo de exceções.
- [ ] Testes diferenciais (Unicorn) passando: instruções, SIMD, atômicos, funções inteiras, jump tables = 0 divergências.
- [ ] `aocrecomp --selftest` (layout, tabela de dispatch, registro de funções host) sem arquivos do jogo.

**Portão B1:** 100 % das instruções dos três módulos geradas sem trap não suportado; C compila e linka no Linux.

## Fase 2 — Host e boot · ~2–3 semanas

- [ ] Loader, ligação dinâmica, TLS, construtores, `nnMain`.
- [ ] Kernel de 3 cores (porta Linux: preempção por sinal) e SVCs.
- [ ] Overrides `nn::*` que faltarem para o SDK 9.6.0 (do censo).
- [ ] Correções conhecidas do AoC: `mem_used` 72 MB, `sys_resource` do NPDM, work buffer de áudio do serviço,
      copyright framebuffer no-op, Opus multistream, saves de outros jogos = não.
- [ ] RomFS via `MountRom` com cache montado pelo host; leitura dos RDB direto do arquivo mesclado (sem descomprimir).
- [ ] Back end gráfico nulo (`gfx_null`) para rodar sem GPU.

**Portão B2:** `nnMain` chega ao laço principal sem fatal; renderer de áudio produz PCM não-silencioso; o jogo pede
os primeiros shaders/programas NVN.

## Fase 3 — Gráficos · ~4–6 semanas (a fase mais longa)

- [ ] Front end NVN do Astral Chain + nomes faltantes do censo.
- [ ] Correções do AoC: compute com binding próprio, `RegisterImage`, indiretos, cache de views por textura,
      `tex_flush_upload`, c1 dinâmico, texel buffers para listas de luz/decal, entradas inteiras de Half2/Short2.
- [ ] Extração KTGL (G2S, `_DOK`, GLSLC do `main`) + tradução AOT de todos os shaders + `spirv-val`.
- [ ] Vídeos VP9 (intro, cutscenes pré-renderizadas).
- [ ] Pipelines: lista de chaves gravada em jogo, pré-montagem com graphics pipeline library.

**Portão C:** vídeo de abertura, título e menus corretos; **primeira batalha (Hyrule Field) com soldados, skinning,
luzes, decals e efeitos** — comparada com captura de referência do Switch/emulador; zero falhas de shader não
classificadas.

## Fase 4 — Jogável · ~2 semanas

- [ ] Entrada SDL3: controles do Deck, Xbox/PlayStation/Pro, teclado; layout de botões Nintendo/Xbox; gyro.
- [ ] Áudio SDL3 contínuo (música, vozes, vídeos).
- [ ] Save/load em pasta do host, recarga em processo novo.
- [ ] Script de entrada que vai do boot à primeira batalha (regressão automática).
- [ ] Menu ImGui (F1 / botão segurado) e overlay de desempenho (F10 / L3+R3).

**Portão D:** primeira missão inteira jogável com controle, som, save e reload.

## Fase 5 — Steam Deck · ~2–3 semanas

- [ ] Build Linux contra o sysroot *sniper*; binário roda no SteamOS 3.8 em Desktop e Game Mode.
- [ ] Write-watch por `userfaultfd` + `PAGEMAP_SCAN`; pools sombra.
- [ ] Texturas: BC1–BC7 direto no RDNA2 (o AoC não usa ASTC); conferir deswizzle block-linear e sRGB.
- [ ] Perfil `deck`: 1280×800, render scale + FSR1, limitador 30 fps, vsync.
- [ ] Layout de instalação no cartão SD; Mesa cache ao lado do jogo; "Add to Steam".
- [ ] Medições: FPS médio/1 % low, frame time, W da APU, temperatura, em rota fixa (Hyrule Field + uma batalha cheia).

**Portão F (Deck):** 30 fps estáveis na primeira batalha em 1280×800 (render scale a definir) com ≤ 15 W; sem stutter
de shader após a instalação; 1 h de sessão sem crash.

## Fase 6 — Melhorias · contínuo

- [ ] 60 fps opcional (portar os três stubs de frame-step para patches do lifter; validar cutscenes — a da torre da
      Impa é o caso conhecido de falha).
- [ ] 40 fps para o modo 40 Hz do Deck (pesquisa: passo não-inteiro de vsync).
- [ ] 16:10 de verdade (câmera + HUD) em vez de letterbox.
- [ ] DLCs: *Pulse of the Ancients* e *Guardian of Remembrance* (montagem, enumeração, conteúdo).
- [ ] Co-op local (tela dividida é carga extra no Deck).

## Fase 7 — Instalador · ~1–2 semanas

- [ ] AppImage (Linux/Deck) e zip (Windows) que **compilam o jogo na máquina do jogador** a partir do dump dele —
      nenhum código derivado do jogo é distribuído.
- [ ] Atualização preservando saves e configurações.

---

## Riscos principais

| Risco | Impacto | Mitigação |
|---|---|---|
| Replay NVN→Vulkan pesado demais para os 4 núcleos do Deck nas batalhas (milhares de dispatches e binds) | 30 fps não fecha | Medir cedo (Fase 3); cache de views, dispatches agrupados, thread de gravação, uniform snapshot; render scale |
| ~~ASTC em massa sem suporte no RDNA2~~ | — | Eliminado na Fase 0: o jogo só usa BCn |
| Leitura aleatória lenta do cartão SD | Travadas ao carregar áreas | Ler RDB em blocos grandes, pré-carregar por área, cache de leitura; medir no Deck |
| Semântica NVN não documentada que o AoC usa e o nxnative não cobriu | Bugs visuais longos | Comparação com emulador; plano B = GPU LLE (HWDER) |
| Timers em ticks de 60 Hz quebrando 40/60 fps | Gameplay acelerado | "Original 30" como padrão; 60/40 só após teste de cutscene e batalha contra relógio real |
| Kernel do WSL2 sem `PAGEMAP_SCAN` | Testes locais limitados | Testar no Deck / Linux nativo; build no WSL só compila |
| Mudança nas referências (projetos ativos, commits diários) | Referência some ou muda | Revisões fixadas em `tools/fetch_refs.sh`; cópia só com atribuição |

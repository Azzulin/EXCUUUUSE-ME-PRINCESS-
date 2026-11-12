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
- [x] Script de ambiente do WSL2 (`tools/setup_wsl.sh`: Ubuntu ou Arch; clang, lld, ninja, venv Python, SDL3, opus, libvpx, zstd, Vulkan). Falta: .NET 10 (tradutor de shaders).
- [x] `tools/extract.py`: inventário dos pacotes, ExeFS do 1.3.0 e listagem do RomFS da base e dos DLCs, direto do NSP.
- [x] Mesclar o RomFS da base com o patch BKTR do 1.3.0 (`tools/windows/merge_romfs.bat` + hactool.exe) → `build/v130/romfs.bin`.
- [x] `tools/inspect_dump.py` confere build IDs, NPDM e tamanhos — **build IDs 1.3.0 conferidos**.
- [ ] Censos (resultados em `docs/aoc.md`, sem dados do jogo, só números):
  - [x] imports dos módulos (`tools/census_imports.py`) — falta cruzar com os overrides herdados;
  - [ ] nomes NVN pedidos pelo jogo × `nvn_procs.inc`;
  - [x] instruções/funções/jump tables por módulo (geração completa na Fase 1);
  - [x] shaders por estágio (`tools/census_shaders.py`): 40 729 únicos, mesmas chaves do nxnative;
  - [ ] teste de tradução dos shaders (tradutor Ryujinx + `spirv-val`);
  - [x] formatos de textura nas G1T — só BCn, nenhum ASTC (`tools/census_rdb.py`);
  - [x] tamanho do RomFS da base, do 1.3.0 mesclado e dos DLCs;
  - [x] tipos de dados nos RDB (`tools/census_rdb.py`);

**Portão A:** build IDs batem com 1.3.0; censos registrados; formatos de textura conhecidos (resultado: só BCn).

## Fase 1 — CPU: lifter para os três módulos · ~2 semanas

- [x] Trazer `recomp/` do Astral Chain (MIT) com atribuição; gerador com marcador.
- [x] `layout.py` do AoC: bases dos módulos sem região fixa de RomFS (heap/alias/pilhas ficam com o runtime, Fase 2).
- [x] Padrão de jump table de bytes indexada por `x30` — `main+0x138216c` já resolve e bate com o oráculo (11 alvos).
- [x] Decidir `--no-callee-saved-trust` a partir do censo de exceções — não precisa (sem exceções C++ nem longjmp).
- [x] Testes diferenciais (Unicorn): instruções ✔, funções inteiras ✔, flags ✔, **SIMD ✔ (159 976 casos) e atômicos ✔ (12 672 casos), 0 falhas**; jump tables: `main` corrigido, 1 superconjunto seguro no `subsdk0` (pendente).
- [x] `tools/build.py`: gera o C e compila com ninja (`libaoc_guest.a`), funções gigantes primeiro e com flags próprias.
- [x] Build completo no WSL (notebook i5-11400H, 2026-11-04): ~48 min, 40 gigantes, nenhuma falha — `docs/aoc.md`.
- [x] `aoc --selftest` (layout, tabela de dispatch, registro de funções host): passa, 0 falhas.

**Portão B1:** 100 % das instruções dos três módulos geradas sem trap não suportado; C compila e linka no Linux.

## Fase 2 — Host e boot · ~2–3 semanas

- [x] Loader, ligação dinâmica, TLS, construtores, `nnMain` (runtime do Astral Chain + porta Linux do TotK, `runtime/`).
- [x] Kernel de 3 cores (porta Linux: preempção por sinal) e SVCs — 64 threads guest no laço principal, sem fatal.
- [ ] Overrides `nn::*` que faltarem para o SDK 9.6.0 (do censo).
- [ ] Correções conhecidas do AoC: ~~`mem_used` 72 MB~~ (não se aplica: o runtime mede os módulos), `sys_resource`
      do NPDM, work buffer de áudio do serviço, Opus multistream (serviço `hwopus` feito, falta ver o jogo usar),
      copyright framebuffer no-op ✔, domínios CMIF no `fsp-srv` ✔, toque `GetTouchScreenState<1>` ✔, saves de outros
      jogos = não (conferir quando o jogo perguntar).
- [x] RomFS via `MountRom` com cache montado pelo host; leitura dos RDB direto do arquivo mesclado (`tools/romfs_index.py`).
- [x] Back end gráfico nulo (`AOC_GPU=null`): o jogo roda a 30 fps no WSL sem GPU.

**Portão B2:** `nnMain` chega ao laço principal sem fatal; renderer de áudio produz PCM não-silencioso; o jogo pede
os primeiros shaders/programas NVN.

> **Portão B2 cumprido em 2026-11-04** (WSL, `AOC_GPU=null`): laço principal a 30 fps com relógio 1×; 8 756
> `ProgramSetShaders`; **PCM não-silencioso** (rms 0,12, pico 0,71) depois de passar as telas do primeiro boot com A
> (`AOC_INPUT_SCRIPT`); o vídeo de abertura (`movie/Movie001.webm`, VP9 1280×720) toca inteiro pelo libvpx do host.
> Sem entrada o jogo fica parado nessas telas, em silêncio, o que parecia um travamento.

## Fase 3 — Gráficos · ~4–6 semanas (a fase mais longa)

- [ ] Front end NVN do Astral Chain + nomes faltantes do censo.
- [ ] Correções do AoC: compute com binding próprio, `RegisterImage`, indiretos, cache de views por textura,
      `tex_flush_upload`, c1 dinâmico, texel buffers para listas de luz/decal, entradas inteiras de Half2/Short2.
- [ ] Extração KTGL (G2S, `_DOK`, GLSLC do `main`) + tradução AOT de todos os shaders + `spirv-val`.
- [ ] Vídeos VP9 (intro, cutscenes pré-renderizadas): decodificação ✔ (`ov_movie.c`, ~1,3 ms/frame); falta imagem (Vulkan) e o **som dos vídeos** (silêncio durante o vídeo de abertura).
- [ ] Pipelines: lista de chaves gravada em jogo, pré-montagem com graphics pipeline library.
- [x] Memória compartilhada dos compute shaders com o tamanho do NVN (controle +0x754): sem isso a primeira batalha
      perdia o dispositivo (sessão 3).
- [x] Build nativo do Windows para testar em GPU de PC (`tools/build.py` no MSYS2 UCRT64).
- [x] Janela com os bytes do jogo (view UNORM da textura sRGB; antes, cor decodificada e supersaturada) — sessão 4.
- [x] Efeitos de partículas sem rastros: o tradutor mantém ballot, voto e shuffle no lugar (patch 0013) — sessão 4.
- [x] Imagem da batalha lavada: as views sRGB dos mapas de cor eram ignoradas na amostragem (luma 233 → 175) —
      sessão 4.
- [x] Retângulo branco no centro da tela: efeito de recuperação de coração opaco porque o tradutor perdia a condição
      de um `SYNC` condicional; patch 0014 (`BranchElimination` respeita os phis do destino) — sessão 7.

**Portão C:** vídeo de abertura, título e menus corretos; **primeira batalha (Hyrule Field) com soldados, skinning,
luzes, decals e efeitos** — comparada com captura de referência do Switch/emulador; zero falhas de shader não
classificadas.

## Fase 4 — Jogável · ~2 semanas

- [ ] Entrada SDL3: controles do Deck, Xbox/PlayStation/Pro, teclado; layout de botões Nintendo/Xbox; gyro.
- [x] Áudio SDL3 contínuo (música, vozes, vídeos): música e cinemáticas voltaram na sessão 5 (ordem dos submixes com splitter); falta ouvir no Deck.
- [ ] Save/load em pasta do host, recarga em processo novo.
- [ ] Script de entrada que vai do boot à primeira batalha (regressão automática).
- [ ] Menu ImGui (F1 / botão segurado) e overlay de desempenho (F10 / L3+R3).

**Portão D:** primeira missão inteira jogável com controle, som, save e reload.

## Fase 5 — Steam Deck · ~2–3 semanas

- [x] Build Linux contra o sysroot *sniper* (`tools/build.py dist`, pede no máximo GLIBC_2.29); roda no SteamOS 3.9.5
      (sessões 3 e 4: pelo Steam e por SSH, imagem igual à do PC).
- [ ] Write-watch por `userfaultfd` + `PAGEMAP_SCAN`; pools sombra.
- [ ] Texturas: BC1–BC7 direto no RDNA2 (o AoC não usa ASTC); conferir deswizzle block-linear e sRGB (as views
      sRGB dos mapas de cor já são respeitadas, sessão 4).
- [ ] Perfil `deck`: saída 1280×720 nativa com cena 960×540 — funciona, mas o minimapa perde os marcadores
      (sessão 7); o perfil usa a resolução do jogo até isso ser resolvido. 30 fps e vsync: feitos.
- [ ] Layout de instalação no cartão SD; Mesa cache ao lado do jogo; "Add to Steam".
- [x] Medições: FPS, frame time, W da APU, temperatura, em rota fixa (primeira batalha): 27–30 fps a 7,6–8,7 W —
      sessão 7. Registros de cada sessão jogada: `aoc-logs.sh` na pasta do Deck.
- [x] Trace de perf que não pesa no Deck: o censo de páginas sujas (63 ms por frame na batalha) só com
      `AOC_DIRTY_CENSUS=1` — sessão 4. Batalha medida sem ele: 24,6 fps (com ele, 12,8).
- [x] Sombra dos pools: regiões paradas indicadas para congelar (~30 → 2 ms por frame na batalha do Deck) — sessão 7.
- [x] Rastros no modo import: não existem (eram bandeiras ao vento no detector) — sessão 8.
- [x] Cache de shaders estável entre corridas (hash do programa sem a contabilidade do KTGL) — sessão 8, medido no
      notebook; falta o Deck.

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
| 35 funções gigantes no `main` (1–7 MB de C cada) levam 15–20 min cada para compilar | Build longo (só no PC; o Deck não compila) | Flags próprias (−40 %), começam primeiro no ninja; depois, quebrar as funções no gerador |
| Kernel do WSL2 sem `PAGEMAP_SCAN` | Testes locais limitados | Testar no Deck / Linux nativo; build no WSL só compila |
| Mudança nas referências (projetos ativos, commits diários) | Referência some ou muda | Revisões fixadas em `tools/fetch_refs.sh`; cópia só com atribuição |

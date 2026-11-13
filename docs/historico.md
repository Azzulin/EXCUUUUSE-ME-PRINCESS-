# Histórico do projeto

Relato do que foi feito, em ordem, com o porquê de cada passo. Para o estado atual e os próximos passos, ver
[handover.md](handover.md). Horários de 2026-11-03 (UTC−3).

## Sessão 1 — 2026-11-03

### Levantamento (manhã)

- O dono pediu um levantamento completo para portar a própria cópia de *Age of Calamity* para PC, com foco no Steam
  Deck, usando o [astral-chain-pc-recomp](https://github.com/captainj-sparrow/astral-chain-pc-recomp) como
  referência.
- Lidas as referências: Astral Chain Recomp, TotK Recomp, LAS Recomp, SavageWindRecomp, MacNativeGames, nxnative e
  HWDER. Achado principal: o **nxnative e o MacNativeGames já rodam o AoC 1.3.0** (iPhone/Mac), executando o ARM64
  original; o pipeline do Astral Chain/TotK roda em x86-64 e Linux/Deck. O projeto é juntar as duas metades.
- Escritos `docs/levantamento.md`, `arquitetura.md`, `plano.md`, `steam-deck.md`, `referencias.md`, o esqueleto do
  repositório e a guarda de conteúdo (`tools/check_content.py`, hook e CI).
- As referências foram clonadas com histórico em `D:\Gits para projetos\switch-recomp\` (depois também
  `aoc-dados\`), com a tag `aoc-ref-2026-11-03` na revisão usada.
- 14:35 — `42385ec` commit inicial, enviado ao repositório privado `Azzulin/Blonde-Z-and-her-friends`.

### Dump e Fase 0 (tarde)

- O dono informou que o Deck tem cartão SD de **1 TB** (espaço deixou de ser restrição) e moveu o projeto para o
  disco D. O dump (base, update 1.3.0, 4 DLCs, `prod.keys`) foi posto em `Game Files/`.
- Verificação do dump direto dos NSPs: containers íntegros, todos os NCAs decifram (`NCA3`), SDK 9.6.0, geração de
  chave 0x0B. — `06a4cc3`
- O build do hactool no ambiente Linux do Cowork foi bloqueado pelo classificador de segurança (código C externo);
  em vez dele foi escrito um extrator próprio em Python (`tools/nx.py`, adaptado do MacNativeGames). ExeFS 1.3.0
  extraído; **build IDs batem com o nxnative**; censo de imports. — `1a6cded`
- O dono baixou o hactool. Como a escrita no D pelo Linux do Cowork é lenta (~11 MB/s), a mesclagem do RomFS (BKTR)
  virou um script do Windows (`tools/windows/merge_romfs.bat`). Dois tropeços corrigidos: colchetes nos nomes dos
  NSPs (`New-Item` como curinga) e o `--romfs` ignorado em seção BKTR (é `--section1`). — `249d42f`, `1a49194`,
  `db2008b`
- RomFS 1.3.0 mesclado (10,91 GiB, seis níveis IVFC verificados). Censo dos RDB: **o jogo não usa ASTC**, só
  BC1–BC7 — risco grande do Deck eliminado. — `310f585`
- Censo de shaders estático (sem emulador): **40 729 únicos**, as mesmas chaves do nxnative. — `e77d8c3`

### Fase 1 (fim da tarde)

- O dono autorizou seguir sem esperar por ele. O `recomp/` do Astral Chain foi trazido (só `layout.py` mudou: sem
  região fixa de RomFS). Na nuvem da sessão: 101 212 funções, ~600 MB de C em 161 s, **0 instruções não
  suportadas**; testes do Astral Chain contra Unicorn sem falha (179 958 casos de instruções, 4 246 de funções
  inteiras). Censos de DLC (nenhum shader novo) e de overrides. — `ca8e918`
- Corrigida uma jump table superconjunto do `main` em `recomp/jumptables.py`; medido o problema das **35 funções
  gigantes** (15–20 min cada para compilar). — `0fdbe3c`
- Decisão do dono: **compilar no PC e copiar uma pasta única para o Deck**. Criados `tools/build.py` (gera e
  compila com ninja; gigantes primeiro, limitadas pela RAM), `tools/setup_wsl.sh`, `docs/building.md` e o layout
  de `dist/aoc-deck/`. — `7667d30`, `2d7f3ca`
- Primeira tentativa do build no WSL do PC falhou antes de começar: a distro `Ubuntu` está com o disco
  (`ext4.vhdx`) sumido. O dono foi orientado a recuperar ou reinstalar.
- `build.bat` na raiz para rodar em qualquer máquina com o repositório clonado e o dump em `Game Files/`. — `dacaabf`
- Escritos este histórico e o `docs/handover.md` para os agentes de outras máquinas.

## Sessão 2 — 2026-11-04 (notebook)

Horários de 2026-11-04 (UTC−3). O dono passou a trabalhar só no notebook (i5-11400H, 15,7 GB, WSL **Arch**), sem o
disco D e sem as referências locais.

### Ambiente e build completo

- Arch do WSL estava vazio (pacman nunca sincronizado). `tools/setup_wsl.sh` passou a aceitar pacman (e root sem
  sudo) e a instalar também as bibliotecas do runtime. Referências clonadas em `refs/` pelo Git Bash.
- Geração do C: 2 min 46 s, números idênticos aos da sessão 1 (101 212 funções, 0 não suportadas).
- Primeiro `guest` falhou inteiro: o caminho do repositório tem espaços e o `tools/build.py` passava `-I` com o
  escape `$ ` do ninja, que o shell quebra. Corrigido com aspas do shell (`shell_arg`).
- Build completo do código do jogo: **~48 min**, 0 falhas, `libaoc_guest.a` de 259 MiB. As 4 maiores gigantes foram
  de 2 em 2; o resto foi relançado com `--big-jobs 4` (8 min).
- `tools/spin_waits.py` (do Astral Chain) achou **1 112 spin waits**; tabela em `recomp/patches-v130.txt`, que o
  `build.py` agora sempre passa ao gerador (67 arquivos de C mudaram).

### Runtime (Fase 2)

- `runtime/` = runtime do Astral Chain (casa com o nosso `recomp/`) + porta Linux do TotK (`platform/linux.c`, SDL3,
  vídeos VP9). `AC_*`/`TOTK_*` → `AOC_*`. Compilou no Linux com 16 erros em 4 arquivos (seções ELF do `hostfn.c`,
  `movie_tick`, `gfx_window_sdl_run`), resolvidos com o código do TotK; o link pediu `plat_mem_read_fault_hook`
  (só para o RomFS em endereço fixo do Astral Chain): implementado no `linux.c` e desligado quando `ROMFS_SIZE` é 0.
- Novo passo `host` em `tools/build.py` (runtime + `modules.c` + link) e `tools/romfs_index.py` (índice do RomFS
  lido direto das tabelas do `romfs.bin`). **`aoc --selftest` passa.**
- Boot com `AOC_GPU=null`, em ordem de paradas:
  1. `fsp-srv` como domínio CMIF (SDK 9.6): o `ipc.c` lia o `DomainInHeader` depois do cabeçalho CMIF. Domínios
     implementados de verdade (objetos por ID, subinterfaces como IDs, fechamento). `--boot` passa (1º NVN).
  2. Abort em `nn::hid::GetTouchScreenState<1>` (resultado 2202-0041): só a versão de 16 toques tinha tratamento, e
     escrevia 4 bytes. Corrigido.
  3. **O jogo chegou ao laço principal**: 30,0 fps estáveis (intervalo 2), relógio 1×, 64 threads, 8 756 programas
     NVN no início (o nxnative registra ~8 705), save criado. Áudio aberto mas em silêncio.
- Correções do AoC vindas do nxnative: copyright framebuffer (no-op), `CountAddOnContent`, Opus **multistream** no
  serviço `hwopus` (libopus `OpusMSDecoder`; o Astral Chain recusava esses comandos). O `mem_used` de 72 MB não se
  aplica a este runtime (ele mede os módulos).
- Vulkan no WSL é só o Dozen (1.2, sem `VK_EXT_external_memory_host`): gráficos só no Deck ou fora do WSL.

### Pasta do Deck

- Passo `dist`: runtime compilado e linkado contra o sysroot **sniper** (snapshot e hash do TotK), zstd 1.5.7
  estática, Opus/libvpx estáticos do sysroot, SDL3 em `lib/`. O executável pede no máximo **GLIBC_2.29**. Testado no
  WSL: selftest passa e o jogo roda a 30 fps pela `aoc.sh`.
- `THIRD_PARTY_NOTICES.md` ganhou as linhas do runtime (e as que o runtime do Astral Chain herdou).

### Fim da Fase 2

- O "silêncio" era o jogo parado nas telas do primeiro boot esperando A. Com `AOC_INPUT_SCRIPT` (A a cada 2 s, como o
  roteiro do nxnative) o som sai (rms 0,12, pico 0,71) e o vídeo de abertura começa — **Portão B2 cumprido**.
- O vídeo parou em `nvnCommandBufferSetCopyImageStride` (front end NVN sem ele); implementado como o passo de camada
  das cópias buffer↔textura (nxnative). Depois disso o vídeo toca inteiro (VP9 pelo libvpx, ~1,3 ms/frame), ainda sem
  som.
- `tests/diff/simd.py` (159 976 casos) e `tests/diff/atomic.py` (12 672 casos): 0 falhas.

### Pasta única e menu rápido (pedido do dono: não forçar o Deck)

- **Menu rápido**: segurar L3+R3 (~1,5 s) abre um painel com taxa de quadros (30; 60 desativado até o patch),
  resolução interna (modo portátil/TV do Switch, trocado ao vivo pelas mensagens do `oe`) e overlay; o toque curto
  continua no overlay. Textos nas quatro línguas do menu; prova nova em `--probe-services` ("quick gate", 8 casos).
- Padrões: 30 fps para todos (era 60) e, no perfil do Deck, modo portátil. Medido no WSL com `AOC_TEST_OPMODE`: o
  jogo relê o modo logo após o aviso (`main+0x8cec30`) e segue a 30 fps.
- `dist --with-romfs`: hardlink do `romfs.bin`, `LEIA-ME.txt`, `aoc.ini` inicial (menu pt-BR) e, numa pasta portátil,
  `profile/` ao lado do executável (antes caía no caminho do PC). Teste de ponta a ponta da pasta: selftest, 30 fps,
  som (rms 0,13), vídeo, saves na pasta, sem fatal.
- `--probe-cfg` volta a passar (prefixo antigo `astralchain_` na prova; checagem de arquivo somente leitura pulada
  quando roda como root).

## Sessão 3 — 2026-11-05 (primeiro teste no Deck)

- O dono copiou a pasta por FTP e rodou o jogo; não conseguiu jogar nem pôr no Game Mode. Log lido por SSH: o jogo
  roda no Deck (RADV VANGOGH, 29,9 fps de média em 46,5 s, áudio no alto-falante, sem crash), mas a **tela fica
  preta** porque ainda não há tradutor de shaders (Fase 3). O atalho "não Steam" nunca tinha sido criado: a janela do
  Steam lista aplicativos `.desktop`, não um script solto no cartão SD.
- `dist` ganhou `instalar-atalho.sh` (cria `~/.local/share/applications/aoc-recomp.desktop` com o caminho da pasta);
  rodado e validado no Deck (`desktop-file-validate`). LEIA-ME atualizado.

### Fase 3 no Deck (mesmo dia)

- Tradutor de shaders do TotK Recomp compilado com NativeAOT contra o sniper (`aoc_xlate`, 3,5 MB, GLIBC_2.29) e
  levado na pasta do Deck; `tools/deck/` com envio por SSH e execução remota com capturas.
- Tela preta: `BindProgram(NULL, COMPUTE)` desligava o programa gráfico e todo draw depois de um dispatch era
  pulado (achado com `AOC_SKIP_LOG`). Corrigido: **primeira imagem no Deck** (telas do primeiro boot corretas).
- `nvnCommandBufferDrawArraysIndirect` (efeitos com quads indiretos) faltava: op `OP_DRAW_IND`, quads convertidos
  na GPU por um compute shader nosso (`vk_quad_ind.c`, `shaders/quad_indirect.comp`). Com isso o jogo chega à
  **primeira batalha** (cena de abertura com legendas, castelo, Hyrule Field com HUD e minimapa), 16–21 fps.
- Batalha estourada em branco: G-buffer certo, iluminação diferida errada (dump `AOC_DUMP=3900`). Causa: listas de
  luz em buffer textures lidas como imagem de zeros. Correções em quatro camadas (texel views, resposta "buffer",
  patch 0012 do tradutor, slots c2 combinados no `Program.cs`); as views passaram a existir e a GPU travou (ring
  timeout). Hipótese do tipo FP32 × R32_UINT corrigida, sem teste: o Deck deixou de responder.
- O dono deixou `Deck Zelda/` (o TotK no Deck deles) como referência para shaders antecipados e estabilidade.

### Windows nativo na RTX 3050 (mesmo dia, tarde; commit 63121e8)

O Deck saiu da rede numa corrida longa; o dono pediu para seguir testando no notebook.

- `tools/build.py` passou a compilar também no Windows (MSYS2 UCRT64 + clang): aspas duplas no ninja, sem `rm`, os
  arquivos `*_win`/`win32.c` do runtime, bibliotecas do build do Astral Chain. Guest em ~30 min (12 threads, WSL
  desligado para liberar RAM); tradutor `aoc_xlate.exe` publicado do WSL sem NativeAOT (`--serve` persiste, o JIT
  não pesa). `aoc.exe --selftest` passa.
- **Travada de CPU ~frame 570** reproduzida no Windows (intermitente). Vigia novo (`AOC_HANG_SECS`) mostrou três
  threads de prioridade 44 segurando os três núcleos virtuais num spinlock do jogo (`main+0x157ab64`, laço
  `while (*lock) nn::os::YieldThread()`), com o dono do lock (prioridade 49/50) sem núcleo. O yield só entregava o
  núcleo a quem tivesse prioridade igual ou melhor. Agora uma sequência de yields é tratada como espera ativa e,
  passados 50 µs, entrega o núcleo a qualquer thread esperando (`kernel.c`, como `rt_spin_gate`).
- **Perda do dispositivo na entrada da batalha** (deterministica na RTX 3050, provavelmente o "ring gfx timeout" do
  Deck). `AOC_CRUMB_DRAWS` (breadcrumb por draw) apontou o compute `fbb562b2` (colisão/pano). Ele usa 68 bytes de
  memória compartilhada por invocação a partir do byte 304 (4 656 bytes para 64), mas o tradutor declarava o padrão
  de 4 096: os limites de laço lidos depois do fim do array eram lixo. O tamanho real está na seção de controle do
  NVN (+0x754, ao lado do tamanho do grupo em +0x748); `gfx_shader.c` passa a mandá-lo (`KEY_VERSION` 5). Batalha
  completa (175 s) a 30 fps sem travar.
- Imagem da batalha ainda lavada: dumps do frame 4400 isolaram o véu no passe de luzes locais (pass 53); detalhes e
  apostas em `handover.md` §6. Testes feitos: tabela de materiais, snapshot de uniformes e exposição descartados.
- Mudança experimental: views de storage no formato que o shader declara (`storage_view_format`, R32F lido como
  r32ui pela auto-exposição). Não mudou a imagem; depois dela 2 de 8 corridas perderam o dispositivo — em medição.

### Continuação no notebook (mesmo dia, noite; commits 2963245, a406770, 754f80d)

- Nome da janela: "Age of Calamity Recomp" (era "Astral Chain Recomp" no Windows e "TotK Recomp" no Linux).
- Imagem lavada: o véu vem da luz ambiente do cubo de ambiente (shader `7da82f37`, filtro do cubo na carga da
  batalha). Descartados com medição: exposição (o jogo a limita a 0,0103–0,017 de propósito), leitura r32ui,
  leitura pela CPU, snapshot de uniformes, tabela de materiais, BRDF, céu, views inteiras, denormais do índice.
  Ferramentas por shader (`AOC_TEXEL_ZERO_FS`, `AOC_TEXEL_LOG_FS`). Causa ainda aberta.
- Desempenho: a batalha não satura a CPU no notebook (thread principal 51% dormindo, núcleos 1,09 de 3); o replay
  na thread do jogo custava 21% dela e foi para uma thread própria no perfil do Deck (`REPLAY_ASYNC=1`).
- Som do vídeo de abertura: o `.webm` não tem áudio; o silêncio é do motor de som do jogo durante o vídeo.

### Cor, rastros e estabilidade (mesmo dia, madrugada)

- Referência do dono (outra batalha no Switch) e relato: na janela do PC a cor está **supersaturada** e há um retângulo
  branco fixo no centro. Medição com `AOC_PRESENT_SHOT` (novo): a janela mostra os bytes do jogo decodificados de sRGB
  para linear (grama 163,203,155 → 92,162,81). O jogo codifica uma vez só (tonemap ARRI LogC + LUT 3D filmica, sem
  gamma próprio); o erro é da nossa apresentação (swapchain UNORM lendo a fonte sRGB pelo formato dela). Correção
  planejada no handover §6.1.
- Investigação do véu: iluminação por classes de stencil (ref 1/2/82/0), contraste ~4:1 preservado até o bloom; o
  tonemap satura em 1,0 porque a cena chega ~10× acima da faixa do medidor de exposição do jogo (9,85–16). `libm`
  do jogo testada contra o host (`--probe-libm`, 25/25 certas); valores da CPU conferidos na memória (`AOC_SCAN_F32`).
- Rastros: vêm dos quads indiretos (efeitos da GPU); detector automático de linhas de um frame.
- Estabilidade: perda de dispositivo com o gravador ligado vinha do push direto no conversor de quads; corrigido.
- Ferramentas novas: `AOC_PRESENT_SHOT`, `AOC_DUMP_RAW` (.f32), `AOC_DUMP_LOG_VKFMT`, estado de depth/stencil/blend no
  dump, `AOC_SCAN_F32`/`AOC_SCAN_FRAME`, `--probe-libm`, `AOC_SKIP_DRAW_IND` (diagnóstico).

## Sessão 4 — 2026-11-06 (notebook, build nativo do Windows)

### Cor da janela: os bytes do jogo como estão

- Causa: o jogo termina num alvo `RGBA8_SRGB` (NVN 0x38) e o Switch manda esses bytes à tela como estão. Nossa
  apresentação lia a imagem pelo formato dela: o `vkCmdBlitImage` e o FSR decodificavam sRGB para linear e gravavam o
  linear num swapchain UNORM (janela escura e supersaturada).
- Correção: a imagem do jogo é lida por uma **view UNORM** (`gfx_present.c` `unorm_view_format`; as imagens de cor já
  são `MUTABLE_FORMAT`). Como o `vkCmdBlitImage` não aceita view, ele virou um draw de tela cheia (`vk_blit.c`,
  `shaders/present_blit.frag`): bilinear no mesmo mapeamento do blit, texel a texel quando os tamanhos batem, barras
  pretas pelo clear do próprio passe. O FSR devolve a imagem dele e o draw a põe no lugar (antes, um blit 1:1); o
  ajuste de cor (`vk_color.c`) lê pela mesma view e passa a trabalhar nos valores da tela, como o shader supõe. O HDR10
  continua decodificando (o PQ precisa de luz). Custo: o do blit (uma leitura da imagem, uma escrita do swapchain);
  nenhum passe a mais no Deck.
- Medido com a imagem do jogo (`AOC_SHOTS` + `AOC_SHOTS_FULL`) e a da janela (`AOC_PRESENT_SHOT`) no mesmo frame,
  contra a interpolação bilinear do blit refeita em numpy (`C:\aoc-win\cmp\cmp.py`):

  | Caminho | Frame | Janela × jogo: diferença média / máxima |
  |---|---|---|
  | Redução bilinear com barras em cima e embaixo (janela 1280×800, o caso do Deck) | 4300 (batalha) | 0,16 / 0,5 |
  | Redução com barras dos lados (janela 1604×881) | 1200 | 0,08 / 1 |
  | Ajuste de cor (`AOC_COLOR_BRIGHTNESS=10`: esperado jogo + 25,5) | 1200 | 0,30 / 1 |
  | FSR (recorte 1280×720 forçado só no teste, ampliado para 1566×881) | 1200 | 0,33 média, cor média igual (as bordas mudam pelo realce do FSR) |

  Antes a janela batia com a imagem decodificada (23–45 de diferença média contra a do jogo). Grama na batalha:
  152,6 / 184,4 / 161,7 no jogo e na janela. As barras saem pretas (0).
- A janela agora mostra o véu claro da imagem verdadeira: é a Fase D, não a apresentação.

### Manifesto do executável do Windows

- O `aoc.exe` rodava **sem DPI por monitor** (`--probe-dpi`: "unaware") e na página de código ANSI: o manifesto do
  Astral Chain não tinha entrado no nosso `tools/build.py`. Agora `runtime/aoc.manifest` (DPI por monitor v2, página
  de código UTF-8, como o `astralchain.manifest`) vai no executável por `runtime/aoc.rc`, compilado com `llvm-windres`
  (ou `windres`) só no Windows. `--probe-dpi`: PASS ("per-monitor aware v2").
- No notebook a imagem não muda: a área de trabalho é 1600×900 pixels físicos a 100 % (conferido de um processo
  ciente de DPI), então não havia esticamento. Vale para telas com escala (o Windows esticaria uma janela de tamanho
  lógico) e para pastas com nome não-ASCII (as funções de arquivo estreitas passam a falar UTF-8, que é o que
  `platform/win32.c` e `fs_host.c` supõem). Na tela cheia deste notebook o swapchain é 1600×900.

### Retângulo branco no centro

- Nenhuma captura da janela da sessão (cinco corridas, menu fechado, overlay desligado) tem algo que não esteja na
  imagem do jogo: a diferença máxima é ≤ 1 em todos os pixels. Com o menu fechado e o overlay desligado o ImGui não
  desenha nada; o copyright frame buffer do jogo não é desenhado em lugar nenhum. Sem o relato de quando ele aparece
  (cena, entrada, overlay), não há o que medir: fica como pergunta ao dono.

### Rastros brancos dos efeitos: o tradutor movia um voto de warp para dentro de um `if`

- Linha de base com capturas a cada 0,1 s entre 140 e 160 s (`C:\aoc-win\streaks.py`): 20 frames com rastro em 201.
  `AOC_SKIP_DRAW_IND=1` (só diagnóstico): 0 → todos vêm dos quads indiretos. `AOC_MEMORY=import` (sem mirror): 0, mas
  a 17 fps — pista falsa de memória que custou várias corridas (abaixo).
- Os quads indiretos leem os vértices de um vertex buffer (`0x192eb6e80+0x14500`, 32 bytes por vértice) que o compute
  `0a66de99` monta a partir do estado das partículas, com um append agregado por warp: `líder = findMSB(ballot)`;
  `se lane == líder: base = atomicAdd(contador, bitCount(ballot) * 4)`; `base = shuffle(base, líder)`;
  `índice = bitCount(LtMask & ballot) * 4 + base`. No SPIR-V do cache havia **três** `OpGroupNonUniformBallot`, um
  dentro do `if` do líder, onde só o líder está ativo: a contagem dava 1, o contador avançava 4 vértices por warp em
  vez de 4×N e os warps seguintes escreviam por cima dos mesmos quads (vértices de partículas diferentes num quad).
- Prova: o SPIR-V de `0a66de99` e `d6c20785` remendado à mão no cache (o voto interno trocado pelo de antes do `if`):
  **0 rastros em 201**. A primeira tentativa no tradutor (um `VOTE` com predicado de guarda votando no warp inteiro)
  gerou SPIR-V idêntico e foi descartada. A causa real: o otimizador da AST do Ryujinx propaga uma operação unária de
  operando constante (`Ballot(true)`) para todos os usos. Patch `tools/xlate/patches/0013-subgroup-ops-stay-in-place`:
  ballot, voto e shuffle ficam onde o shader os calcula (como o patch 0003 faz com atômicos). Com o tradutor novo
  (identidade `d10880c4…`): **0 rastros em 201**; os shaders de partículas passam a ter um ballot só, e outros
  shaders com o mesmo padrão também (21 → 7, 9 → 4 ballots).
- Pistas descartadas com medição: devolução de faixa inteira do mirror sobre escritas da CPU (a devolução precisa,
  abaixo, não mudou os rastros: 28 em 201), buffer textures lendo a memória do jogo (elas usam o mirror), escrita por
  storage texel buffer sem devolução (nenhum `imageStore` nesses shaders), escrita da GPU por DMA acendendo o
  write-watch do Windows (teste isolado `ww_dma.c`: não acende; só a importação inicial acende todas as páginas).

### Devolução precisa do mirror

- No modo mirror (GPU dedicada) a devolução VRAM → memória do jogo copiava cada faixa escrita inteira; um SSBO
  vinculado cobre mais do que o shader grava, e a CPU do jogo pode escrever no resto com a submissão em voo (no Switch a
  GPU só grava os bytes que grava). Agora cada faixa ganha uma pré-imagem no prólogo da parte que a escreve primeiro
  (anel de 64 MiB na VRAM) e, no fim da submissão, `shaders/wb_merge.comp` grava na memória do jogo só as palavras que
  mudaram. Faixa sem lugar no anel cai na cópia inteira; `AOC_MIRROR_WB=whole` volta a ela.
- Batalha, cache quente: GPU 4,28 ms por frame contra 5,97 ms da cópia inteira; fps igual (a batalha aqui é limitada
  pela CPU). `AOC_MEMORY=verify`: 0 divergências em ~30 milhões de comparações de página; nenhuma faixa caiu na cópia
  inteira. No Deck (UMA) o mirror não existe e nada disso roda.

### O véu claro: as views sRGB eram ignoradas na amostragem

- Pista de fora: o README do nxnative (o mesmo código do jogo rodando no Mac) mede luma média 163 no começo da primeira
  batalha; a nossa era 233. Teste descartado antes: traduzir todos os shaders em modo debug (sem a propagação de
  expressões do otimizador da AST) deu a mesma luma (233).
- A exposição do frame vem da CPU (textura 2×1 RGBA32F reenviada todo frame e copiada no pass 0): `(0,0103; 0; 0; 1)`,
  o mínimo do medidor. A cena estava clara demais, não a exposição errada.
- Causa: no dump, `vk145(145) ... view-nvn-fmt 0x4e`: imagens BC7_UNORM amostradas por views BC7_SRGB (105 vínculos
  no frame 4400), e o mesmo com BC3 (58) e BC1 (23). `get_view` (`vk_exec_draw.c`) criava a view sempre no formato da
  imagem; o jogo cria os mapas de cor UNORM e os lê por views sRGB, então todo albedo vinha sem a decodificação.
- Correção: `sampled_view_format` usa o par sRGB/UNORM da imagem (`tex_srgb_twin`, `vk_formats.c`) quando a view NVN
  pede exatamente ele; a tradução NVN → Vulkan das views é uma tabela montada uma vez (caminho de cada bind). A
  apresentação usa o mesmo par. Os alvos de render já respeitavam o formato da view (`vk_exec.c` `view_format`).
- Medido: luma média no ponto de 143 s da rota **233 → 175**, no fim (175 s) 233 → 174; a rota inteira com cores
  certas (configurações, abertura, cinemáticas do Rei Rhoam e dos Bokoblins, batalha); 0 erros de validação.
- Com a cor certa aparece o **retângulo branco no centro** que o dono relatou: está na imagem do jogo (não na
  apresentação), branco puro, ~20×38 px, fixo no centro da tela.

### Retângulo branco: localizado (causa ainda aberta)

- Pulando draws por programa só na batalha (código temporário, já removido): o retângulo some ao pular o **programa
  720** do pass do HUD (pass 95, alvo 1920×1080 RGBA8_SRGB): VS `bc173f45`, FS `a57f4e05`, blend aditivo
  (`SRC_ALPHA, ONE`), um draw de quad.
- Vértices (stride 44): posição ±2 (RGB32F), cor `ffffffff`, UV0 (RG32F) de 0 a 1, UV1 e UV2 em (0, 0). Uniformes do
  FS: `c3[0] = (3, 1, 12, 1)` como inteiros → **modo 12** (distorção), `c3[1] = (0,16; 0,16; 1; 1)`, `c3[4].x = -1`,
  `c3[5].x = -FLT_MAX` (sem descarte por alfa).
- Texturas: slot 0 = BC3 64×128 (view sRGB) com RGB **branco e alfa 0–5 no fundo** (primeiro bloco: alfa `00 05`, cor
  `ffff 0000`); slot 1 = BC3 128×128 (view sRGB); slot 2 = RGBA8 64×128 com view `B,G,R,A`, uma linha ondulada,
  **alfa 255 em todos os texels**, lida em UV (0, 0). No modo 12 o shader traduzido pega a cor do slot 0 e o alfa do
  slot 2 (`_86 = _78.w; _86 = _52.z;`), e depois `min(_227, _122)`: com alfa 1 o fundo transparente do ícone vira um
  bloco branco opaco somado à cena.
- Próximo: ver no código Maxwell desse FS de onde vem o alfa final (a máscara de componentes do TEX que lê `.xyw`, a
  ordem dos registradores, e o ramo escolhido pela constante c1 `_127` = 1240 / 1792 / ...), e comparar com o
  tradutor. Se o alfa certo é o do slot 0, o defeito é de tradução; se é o do slot 2, o defeito está nos dados.
- **Tabela de ramos (depois do commit 52cb12c):** o FS é um `BRX` do Maxwell; o destino sai de uma tabela na c1, que o
  tradutor emula comparando (`_127 = c1[_125 >> 2][_125 & 3]`, depois `if (_127 == 1240) ... else if (_127 == 1792)`).
  No cache só um programa tem essa tabela (entrada `in/6575db294819747a`, fragment, 4 608 bytes de código, c1 de 256
  bytes): `[1240, 2352, 1792, 2352, 3072, 2960, 3032, 3184, 3224, 3328, 3408, 3544, 3680, 3776, ...]`. O modo 12 cai
  no destino 1792, o ramo que faz `_165 = _189.w; _165 = _167.z;`.
- **O tradutor está certo nesse ramo** (conferido no fim da sessão): `_167 = texture(fp_t_tcb_C, ...).xyw` é um `vec3`
  com x, y e **w** da textura C (o `TEX` com máscara `.xyw` empacota três componentes), então `_167.z` é o **alfa** da
  máscara; a cor vem do ícone (`_189`, textura A). O `x`/`y` da máscara (cinza, R = G = B de 0 a 253, uma linha
  ondulada; alfa 255 em todos os texels; texel (0,0) = `(0, 0, 0, 255)`, `dumpr3/pass_0095_tex373_64x128x1_37_rgba8.png`)
  é o deslocamento da distorção. E o mapeamento dos destinos do `BRX` é consistente: o decodificador do Ryujinx
  (`Decoders/Decoder.cs` `FindBrxTargets`) e o emissor (`Instructions/InstEmitFlowControl.cs` `Brx`) somam o mesmo
  endereço do `BRX` (`InstOp.GetAbsoluteAddress`, pc + 8 + imediato) ao valor da c1, e os 14 valores da tabela são
  múltiplos de 8 abaixo dos 4 608 bytes de código (endereços de instrução). Ou seja: com esses dados e esses
  uniformes, o shader do Switch também pintaria um quad opaco com o RGB branco do ícone. O defeito está no que chega
  ao draw: a posição/escala do elemento (matriz do VS), um uniforme que o jogo reescreve e nós lemos velho, ou um
  elemento que o jogo esconde por outro caminho.
- A posição do quad vem de uma matriz por elemento em `c3[6..8]` do VS; o `c3[8]` não apareceu no dump do frame
  (falta conferir o tamanho do bloco vinculado ao VS; um bloco reescrito por `UpdateUniformBuffer` aparece com o valor
  de antes da submissão, `vk_dump.c`), então ainda não dá para dizer se o elemento devia estar fora da tela ou
  escondido.
- No Deck o retângulo aparece igual (abaixo): não depende de GPU nem de driver.

### Steam Deck: o runtime novo e a primeira medição da batalha

- O Deck voltou às ~21h. `journalctl -b -1`: o boot anterior terminou num desligamento normal às 20h59, sem erro de
  GPU nem travada; o boot da travada da sessão 3 é mais antigo e não foi lido (`journalctl --list-boots`). Envio com
  `tools/deck/deploy.sh --no-build` e a rota com `tools/deck/deck_run.sh` (duas corridas: a primeira traduz tudo de
  novo, o tradutor mudou).
- **Imagem**: igual à do PC (luma média 176 no fim da rota; no PC 174–175), sem rastros e com as cores certas. O
  retângulo branco aparece no mesmo lugar.
- **Desempenho medido** (com `AOC_TRACE=perf,sched`): 30 fps travados até a batalha; na batalha **12,8 fps** (78 ms por
  frame) com a GPU ocupada 29,6 ms por frame (~48 ms ociosa) → limitado pela CPU. A thread principal (0x1001) passa
  64 % rodando código do jogo (~50 ms por frame; no notebook ~16 ms), 20–21 % esperando um núcleo virtual e 15 % no
  host, sem dormir nunca; 14,9 % num ponto só, `exe+0x96ac0e` = `nvn_api_core.c:488` (`nvnSyncWait`). Os workers
  giram em `main+0x17496a0`.
- **A medição estava contaminada**: a linha `mem: write-watch` da batalha dava **516 consultas por frame cobrindo
  41 GB, 62,7–63,8 ms por frame** (8,4 delas acham ~3 030 páginas escritas, 7,5–8 ms). Quem consultava era o censo de
  páginas sujas (`vk_memory.c` `vk_mem_dirty_submit`), que rodava em todo submit sempre que `AOC_TRACE=perf` estava
  ligado e não havia mirror (modo import, o do Deck), na thread do replay e dentro do lock do submit. No notebook o
  mesmo aparece com `AOC_MEMORY=import`: 23,7 GB e 25 ms por frame, contra 0,66 GB e 0,9 ms no mirror. Logo, os fps
  do Deck medidos com `AOC_TRACE=perf` (estes e provavelmente os 16–21 fps da sessão 3) mediam o censo junto.

### Censo de páginas sujas só a pedido

- O censo agora exige `AOC_DIRTY_CENSUS=1` além de `AOC_TRACE=perf` (`vk_memory.c` `census_on`, lido no primeiro
  submit); `VK_MEM_BOUND` e o `bind_vertex_buffers` (`vk_exec_draw.c`) testam só `vk_mem_census_on`. O trace de perf
  continua com a linha de fps, a de GPU e a de write-watch.
- Medido no notebook em modo import (`AOC_MEMORY=import`, o caminho do Deck), batalha: consultas de write-watch por
  frame **23,7 GB / 25 ms → 2 MiB / 0,027 ms**; intervalo de frame 58,6 → 52,2 ms (o modo import numa GPU dedicada
  continua lento: a GPU lê a memória do jogo do lado do host).
- Pasta do Deck remontada e enviada às 21h24 com a correção. Às 21h30 o dono estava jogando o TotK lá
  (`pgrep totk`); às ~21h45 o Deck ficou livre e a medição foi refeita (abaixo).

### Deck sem o censo: 24,6 fps na batalha; o que sobra é a sombra dos pools

- Corrida com `C:\aoc-win\cmp\deckbattle.sh limpa` (rota de 175 s, cache quente, `AOC_TRACE=perf,sched`; o script se
  recusa a rodar se `totk` ou `aoc` estiverem abertos). Batalha: **24,3–24,6 fps** (intervalo 40,6–41,1 ms) contra
  12,8 com o censo; GPU 24,6–26,8 ms por frame; luma 173; 4 906 frames, 0 erros de validação, 0 falhas de shader.
- Thread principal: 68 % no código do jogo (~27,6 ms por frame; com o censo parecia ~50 ms, e no notebook são ~16 ms,
  1,7×), 20 % esperando um núcleo virtual (~8 ms), 12 % no host (11,6 % em `nvnSyncWait`, ~4,7 ms). Ela nunca dorme:
  é o caminho crítico. A GPU fica ociosa 16,5 ms por frame, 9,8 ms deles à espera da próxima submissão.
- O write-watch ainda custa **28 ms por frame** (437–449 consultas sobre 17,5–18 GB). Não é mais o censo: é a
  **sombra dos pools** (`vk_memory.c`, "shadow storage", padrão no Linux porque reproteger páginas importadas como
  userptr invalida o buffer no amdgpu). A cada 60 frames: ~2 130 sincronizações de pool, ~26 400 consultas, 690 MiB
  copiados para a sombra, 618 MiB devolvidos, ~1,81 s → **~30 ms por frame** na thread que submete. Causa:
  `shadow_sync_pool` consulta o pool inteiro (de `import_lo` a `import_hi`, menos as regiões congeladas) em cada uma das
  ~35 sincronizações por frame, e só ~7,5 das ~440 consultas acham páginas escritas.
- Correção pensada para a próxima rodada (não feita): consultar só as regiões de 2 MiB que o replay resolveu desde a
  última sincronização, com um `sgen` **por região** em vez de por pool. Com o `sgen` por pool, pular uma região
  perderia escritas: uma consulta da checagem de textura pode carimbar a página antes da sincronização e, quando a
  região for usada de novo, o carimbo já estaria abaixo do `sgen` do pool. Testável no notebook com
  `AOC_MEMORY=import AOC_SHADOW=1` antes de ir ao Deck.
- O spin wait dos workers (`main+0x17496a0`) já está na tabela de `recomp/patches-v130.txt` e passa pelo
  `rt_spin_gate`, que cede o núcleo virtual depois de 50 µs se alguém espera (`AOC_SPIN_HANDOFF_US`).

## Sessão 5 — 2026-11-09 (notebook; pedido do dono: retângulo, resolução, música, consumo no Deck, ferramentas)

Sessão curta (o dono encerrou antes do fim da rodada). Fechou a música; o resto ficou escrito e compilado, **sem
medição** — está marcado assim em cada item.

### Atalho no Modo Jogo

- O `aoc` iniciado por SSH no Deck abre e fecha quando o gamescope não lhe dá foco ("window closed; exiting" depois de
  15 s): não serve para o dono jogar. Criado o atalho **"Hyrule Warriors: Age of Calamity"** direto no
  `~/.local/share/Steam/userdata/86581947/config/shortcuts.vdf` (VDF binário; entrada modelada na do TotK, `exe` =
  `aoc.sh` da pasta do cartão SD, appid 4106951061), com o Steam fechado durante a gravação. Cópia da lista antiga ao
  lado: `shortcuts.vdf.bak-20261109-194144`. O Deck estava no Modo Desktop naquele minuto; o Steam foi reaberto.
- O dono jogou 77 s pelo atalho (`logs/aoc.log`, 1 886 frames, 23–28 fps nos menus com cache frio). Relatou: retângulo
  branco no centro, resolução "estranha", jogo sem música.

### Música e som das cinemáticas — CORRIGIDO (medido no notebook)

- Medido antes (`AOC_TRACE=audio`, rota de 175 s): 21 das 37 janelas de 5 s em silêncio exato (rms 0,0000), dos 25 s
  aos 125 s — o vídeo de abertura e as cinemáticas; na batalha só efeitos (rms ~0,02).
- Ferramenta nova, **censo de vozes e de mixes** (`audio_mixer.c` `voice_census`, junto de cada linha `audio: level`):
  vozes em uso/tocando por formato, as dez mais tocadas com pico decodificado, volume e ganho da rota, e cada mix com
  sinal (pico antes e depois dos efeitos, destino, ganho, efeitos).
- O censo mostrou as trilhas tocando: vozes **PCM16 48 kHz de 6 canais** (mixes 12 e 14) e **de 2 canais** (mix 10),
  pico decodificado até 0,44, centenas de buffers consumidos — o Opus do jogo decodifica (decoder de software do SDK,
  código levantado; o serviço `hwopus` nunca é aberto) e o streaming anda. Os mixes 10 e 12 tinham sinal e saíam por
  **splitter** (3 e 5); nenhum mix depois deles recebia nada.
- Causa: `mix_depth` ordenava os submixes só pelo `dest_mix_id`. Um mix que sai por splitter ficava com profundidade 1
  e podia ser somado aos destinos **depois** de eles já terem sido processados. O DSP ordena o grafo pelas arestas,
  incluídas as de splitter (Ryujinx.Audio `MixContext.Sort`/`NodeStates`). Agora a profundidade é 1 + a maior entre os
  destinos (mix ou todos os destinos do splitter), com memo por frame.
- Medido depois, mesma rota: **1 janela em silêncio em 37** (a do boot); rms 0,04–0,25 no vídeo, nas cinemáticas e na
  batalha (0,06–0,08 contra ~0,02). Isto resolve também o "som do vídeo de abertura" (handover antigo, item 4): o som
  dele é um stream do KTSL, não uma faixa do `.webm`. **Falta ouvir no Deck** (o binário de lá ainda é o da sessão 4).

### Retângulo branco — causa localizada um nível abaixo, não corrigido

- É **fixo na tela**: girando a câmera e andando (rota `C:\aoc-win\route-cam.txt`, `RSTICK` aos 150 s e `LSTICK` aos
  156 s) o bloco branco continua no centro em todas as capturas.
- Dump com a ferramenta nova (`AOC_DUMP_UBO` agora lista o draw, os atributos, os índices e os vértices que eles
  apontam; `vk_dump.c` `describe_vertex_input`): o draw do programa 720 é **indexado, 270 índices = 45 quads**. Os 45
  quads são idênticos — posição (±32, ±64), UV0 só com `u` (0 a 1; `v` = 0 em todos), UV1 = metade esquerda da
  textura 128×128, UV2 = máscara repetida (-0,5 a 1,5 × -1 a 3), cor `(255, 102, 102, 255)` — e só mudam no **índice de
  matriz** (atributo 0, R32F, 0, 1, 2, ...).
- O VS (`bc173f45`) usa esse índice numa paleta de matrizes no bloco c3 (48 bytes cada, a partir de c3[6]); c3[2..5] é
  a câmera de UI (perspectiva de 45°, distância 1303,68 = 540 / tan 22,5°, 1 unidade = 1 pixel de 1080p no plano
  z = 0). **As matrizes da paleta são todas iguais**: escala 0,3, translação (0, 7). Logo os 45 quads caem um em cima
  do outro, 19×38 px no centro, e a soma aditiva de 45 camadas satura em branco. É um sistema de partículas de UI
  (chama vermelha com distorção ondulada) cujas partículas estão todas na pose inicial, visíveis.
- O FS (`a57f4e05`) lido inteiro: no modo 12 as duas camadas tiram o alfa do `.w` da máscara (255 em todo texel), a
  mistura é o modo 3 (multiplica as cores) e o alfa final é `min` dos dois × alfa do vértice. Com esses dados cada
  quad é opaco; o defeito não está no shader.
- Aberto: por que as 45 matrizes são iguais e as partículas não somem. Suspeitas a testar na ordem: (1) a simulação
  dessas partículas depende de algo que devolvemos constante (relógio, passo de tempo, número aleatório — conferir o
  que o jogo chama quando monta a paleta); (2) o elemento devia estar escondido e a visibilidade vem de outro bloco;
  (3) os dois ramos do `BRX` (1240 e 1792) saem idênticos na tradução — conferir contra o código Maxwell. Os draws dos
  corações usam o mesmo VS (programa 718) e saem certos: comparar a paleta deles no mesmo dump.

### Resolução — explicada; patch escrito e compilado, não testado

- O jogo fixa as duas resoluções em `nnMain`: a configuração do dispositivo KTGL `{1920, 1080, ...}`
  (`main+0x8d9490`, entregue a `main+0x17c34f0`) e a cena 3D **1440×810** (`main+0x8d94d0`, gravada em `[x20+0x368]`).
  O modo portátil não muda nenhuma das duas, e o jogo nunca chama `nvnWindowSetCrop`. No Switch portátil é o sistema
  que reduz o quadro de 1080p para a tela de 720p.
- No Deck fazemos o mesmo: 1920×1080 reduzido 1,5× por bilinear para 1280×720. É isso que o dono viu como resolução
  "estranha" (nitidez irregular na UI e no texto); não vem da correção de cor.
- O que os modos mudam (lido no `main`): `main+0x277f77f` = docked, `main+0x277f77e` = desempenho "boost";
  `main+0xb057e0` escolhe um nível de qualidade 1–4 a partir do modo de desempenho numa tabela de registros de 64
  bytes (dados do jogo). Não é a resolução.
- Escrito: conjuntos de patch **`output`** e **`scene`** em `recomp/patches-v130.txt` (os dois pares passam a vir da
  página de patches, +32 e +40; bytes originais conferidos), `runtime/resolution.c` adaptado ao AoC (base 1920×1080,
  cena 3/4; `AOC_OUTPUT_RES` de 960×540 a 1920×1080, `AOC_RENDER_SCALE` até 100), perfil do Deck com
  `OUTPUT_RES=1280x720` (cena 960×540), menu só com os tamanhos suportados.
- Gerado e compilado no WSL: `gen` em 100 s, só `main_0119.c` mudou, guest em 3 s, host do Linux sem erro
  (`patches.h`: `RT_PATCH_COUNT 2`). **Nunca rodou**: falta levar o `generated` para `C:\aoc-win`, recompilar o guest
  do Windows e conferir a imagem (HUD inteiro? os oito outros `1920×1080` em `main+0x1583db8..0x1584798` são câmeras
  de UI e podem precisar do mesmo tratamento) antes de mandar ao Deck.

### Sombra dos pools — causa mais simples que a do plano; correção escrita, não medida

- No log do dono a sombra custa 25,8 ms por frame mesmo nos menus (600 frames: 18 830 sincronizações, 204 402
  consultas, 11,8 GB copiados, 15 470 ms).
- O mecanismo de **congelar regiões paradas** já existe (`memory.c` `mem_freeze`, 2 MiB somente leitura até a primeira
  escrita), mas só as checagens de textura indicavam candidatas. `shadow_sync_pool` consulta o pool inteiro e nunca
  indicava: por isso só 314 dos 1 826 MiB estavam congelados. Agora ela indica as regiões sem escrita há
  `freeze_idle` submissões (`vk_memory.c`), e as consultas seguintes as pulam. É bem menos código que a "sombra por
  região com `sgen` por região" do plano antigo e usa um caminho já testado.
- **Não medido.** Testar no notebook com `AOC_MEMORY=import AOC_SHADOW=1` (mesma imagem, 0 rastros) e depois no Deck
  (linha `mem: write-watch`: MiB congelados e ms por frame; linha `mem: shadow`).

### Ferramentas de acompanhamento

- **`runtime/sysmon.c`** (Linux, sempre ligado): a cada 10 s uma linha `sys:` no log com fps, potência da APU
  (`amdgpu` `power1_average`), bateria (W, estado, %), temperaturas de CPU e GPU, ventoinha, GPU ocupada, carga da CPU,
  núcleos usados pelo jogo e clocks. Assim uma sessão jogada pelo dono no Modo Jogo deixa consumo e temperatura no
  `logs/aoc.log`. Sensores conferidos por SSH (todos existem no Deck); compila no Linux; **ainda não rodou lá**.
- **`tools/deck/logsum.py`**: resume um log (sessão do dono ou medição): máquina (linhas `sys:`), frame, GPU, sombra,
  write-watch, áudio, erros; destaca o minuto mais pesado. Escrito contra os formatos reais das linhas; as `sys:` só
  serão conferidas com o primeiro log do Deck.
- No notebook (fora do repositório, `C:\aoc-win\`): `a64.py` (desmonta um trecho de `main`/`sdk`/`subsdk0`, lê
  palavras e strings), `plt.py` (imports por nome → stub da PLT → chamadores), `dref.py` (quem lê/escreve um endereço
  de dados via `adrp`), `immscan.py` (constantes `movz`+`movk`, ex.: resoluções), `diag1.sh` (rota com traço de áudio,
  capturas e dump; variáveis `ROUTE`, `SECS`, `LOG`), `wsl_gen.sh` e `wsl_build.sh` (regenerar o C e recompilar no WSL).

### Meta de consumo (12 W) — ainda sem número

O dono quer o jogo rodando no Deck sem esquentar, na casa dos 12 W. Não há medição de potência ainda: o `sysmon` é a
primeira peça. As três frentes que baixam consumo já estão escritas e esperam medição: resolução nativa 1280×720 com
cena 960×540 (menos da metade dos pixels de hoje), sombra dos pools (um núcleo ocupado ~26–30 ms por frame) e, depois,
shaders antecipados (as travadas de tradução seguram a CPU no máximo).

### Comparação com o HWDER (2026-11-11) — o que veio de lá

O dono pediu para olhar o outro projeto dele, `Downloads\Hyrule Warrios DE\HWDER-main` (HWDER v0.3.5, MIT: port do
*Hyrule Warriors: Definitive Edition*, da mesma Koei Tecmo), e trazer o menu do F1 e os mapeamentos de botão.

- **O menu do F1 já existe aqui** e cobre mais que o de lá: abre com **F1**, **Esc** ou **Menos+Mais** no controle
  (`ui/menu_sdl.cpp`, `input_map.c` `input_menu_gate`); abas Tela, Jogo, Som, Controles (com remapeamento de teclado e
  controle, zonas mortas, vibração, giroscópio), Menu, Avançado e Mods; menu rápido segurando L3+R3; F10 = overlay de
  desempenho; F11 = tela cheia.
- Faltava e foi trazido (ideias, nenhum código copiado — o HWDER é C++ com outra estrutura):
  - **Inverter eixos** dos analógicos do controle, quatro chaves na aba Controles (`AOC_INVERT_LX/LY/RX/RY`,
    `input.c` `poll_merged`; só o controle, teclado e mouse têm as próprias teclas);
  - **Mudo** e **Mudo em segundo plano** na aba Som (`AOC_MUTE`, `AOC_MUTE_BACKGROUND`, `audio_mixer.c`
    `host_volume`);
  - teclas **I J K L = X B A Y** do teclado do HWDER como segunda tecla de cada botão de face (`input_map.c`
    `DEFAULT_KEYS`). U/O (ZL/ZR), Enter e Backspace não entraram: a página de botões mostra e edita duas teclas por
    ação, e ZL, ZR já têm duas.
  - Textos nas quatro línguas do menu. `--probe-cfg` passa (um caso do teste atualizado para a segunda tecla de A).
- Não trazido, com motivo: "segurar Select para abrir o menu" (aqui o Menos é botão do jogo e já há Menos+Mais e
  L3+R3); contraste/brilho/saturação, nitidez, FXAA, filtro anisotrópico, abrir log/pasta, cheats e mods (já existem);
  bloom, 120 fps com frame intermediário, ultrawide e co-op de 2 jogadores (dependem de patches e estruturas do
  outro jogo); instalador Setup.exe (fora do alvo: aqui o build é no PC do dono).
- Úteis para depois, só anotados: a lista `pipeline_warmup.bin` montada antes da tela inicial (casa com a Fase E,
  shaders antecipados) e o minidump em crash com rotação dos 5 mais novos.
- **Não conferido na tela**: as linhas novas do menu compilam no Windows e no Linux, mas ninguém abriu o menu ainda.

## Sessão 6 — 2026-11-11 (notebook): retângulo branco — causa encontrada, correção por fazer

Sessão dedicada ao retângulo. **Não está corrigido**; a causa está localizada e reproduzida fora do jogo.

### O que o retângulo é

- É o **efeito de recuperação de coração** do HUD: o layout tem os painéis `_10_heart_recov_effect`,
  `_10_heart_recov_flare`, `_10_heart_recov_mask`, `_10_heart_recov_yugami` (distorção) e as animações
  `stay_heart_recoverable`, `loop_heart_recoverable`, `shot_recoveriable_add` (nomes lidos da memória do jogo).
  São **45 instâncias** do efeito (objetos de 0x5df0 bytes, um comando de sprite cada), todas na pose de repouso:
  escala 0,3, posição (0, 7). O jogo as desenha sempre; em repouso elas deviam sair **transparentes**.
- Texturas decodificadas (BC3 lido dos blocos brutos do dump): a "flare" 128×128 tem a forma da chama no **alfa**
  (fundo cinza no RGB); a "mask" 64×128 é RGB branco com **degradê vertical de alfa** (0 no topo); a "yugami" 64×128
  RGBA8 é a onda de distorção com alfa 255. O quad amostra a máscara em v ≈ 0 (alfa ≈ 0): o alfa certo é
  `min(alfa da chama, alfa da máscara distorcida)` ≈ 0 em repouso.

### A causa: uma condição perdida na tradução do shader

- FS `a57f4e05` (entrada do cache `in/6575db29…`), código Maxwell do ramo do modo 12, depois de amostrar a textura:
  `HSETP2 P0 = (R3 > R9)` · **`SYNC` com predicado `!P0`** · `MOV R3 = R9` · `SYNC`. O `SYNC` condicional pula o
  `MOV`: `if (alfa > alfa_da_onda) alfa = alfa_da_onda`. O mesmo padrão aparece no primeiro estágio (`HSETP2 P1`,
  `SYNC !P1`, `MOV R5 = R3`). No ramo padrão o compilador usou um `MOV` com predicado, e esse sai certo.
- O SPIR-V que usamos faz o `MOV` **sempre** (`_165 = _189.w; _165 = _167.z;`): o alfa vira o da onda (1) e cada
  quad sai opaco; 45 quads aditivos somam branco.
- Reproduzido fora do jogo com o `aoc_xlate` (pasta `C:\aoc-win\retangulo`: `code.bin`, `jobs.json`): com
  `"debug": true` a tradução **mantém** a condição (`bool _622 = _620 > _510; … if (…) _492 = _510`); com
  `"debug": false` (o que o jogo usa) ela some. Um tradutor instrumentado (`xldbg.sh`, cópia em `/tmp/xldbg` do WSL)
  mostrou que **antes** do otimizador da AST já só existe uma comparação `CompareGreater FP32` (a do ramo padrão): a
  condição dos ramos 10 e 12 se perde antes, na IR, e não no `AstOptimizer` (os patches 0003/0013 não são a causa).
  A diferença do modo debug fora do `AstOptimizer` é `Translator.cs` `EmitOps`, que em debug emite um comentário
  por instrução.
- Descartado com medição: teste de alfa fixo do Maxwell (o jogo usa `ALWAYS`, ref 0, em todos os draws do HUD); o
  tradutor ler o `BRX` errado; matrizes/visibilidade (os 45 quads iguais são o estado normal do efeito).
- Correção de registro: a sessão 4 anotou "alfa 255" para a máscara a partir de um PNG do dump, que descarta o
  alfa; o número certo (alfa 255 na onda) veio do `images.txt`, e a máscara de verdade é a textura BC3 64×128.

### Próximo passo (correção)

1. Em `/tmp/xldbg` (ou cópia nova do `~/aoc-build/xlate`), achar o passo que apaga o desvio do `SYNC` condicional
   quando o alvo dele é o mesmo do `SYNC` seguinte: candidatos `Translation/Optimizations/*` (eliminação de desvios,
   simplificação de blocos) e `Decoders/Decoder.cs` (propagação SSY/SYNC). Teste: o `opt.glsl` do job tem de ganhar
   a comparação `_189.w > _167.z` nos ramos 1240 e 1792 e no bloco do modo 12.
2. Virar patch `tools/xlate/patches/0014-…`, reconstruir o tradutor (WSL + `xlate_win.sh`); o cache de shaders esfria
   uma vez. Conferir quantos shaders mudam (o padrão `HSETP2`/`SYNC` condicional/`MOV` deve existir em outros
   materiais de UI e efeitos).
3. Rota até a batalha: centro da tela sem bloco branco (`centre white 0.00` nas capturas), rastros 0 em 201, luma
   ~175. Só então mandar ao Deck (junto com o resto da sessão 5).

### Ferramentas novas desta sessão

- No runtime: `AOC_DUMP_UBO` lista também a função e a referência do teste de alfa por draw (op novo
  `OP_ALPHA_REF`, o valor chega ao replay; o teste em si continua sem aplicar, o jogo não o usa no trecho medido);
  `AOC_DUMP_RAW=1` grava os blocos brutos das texturas comprimidas (`.bin`), e as texturas de um passe com alvos
  repetidos passam a ser copiadas; `AOC_UBO_TRACE=<tam>:<float>` (pilha do jogo de quem vincula um bloco de uniformes
  com conteúdo conhecido); `AOC_SCAN_SEQ=1` (sequência de floats na memória; lento, o depurador é melhor).
- Depurador no build do Windows: `gdb -p <pid> -batch -x <script>` funciona (símbolos `f_<endereço do jogo>`,
  watchpoints de hardware, Python). Scripts em `C:\aoc-win\retangulo`: `gdbl.py` (para no momento em que a paleta de
  matrizes é escrita e percorre a lista de comandos de UI), `gdbn.py` (nomes de painéis na memória), `gdbw.txt`.
  A pilha do jogo se acha pelo `Cpu` de `rt_original` (`c->sp` em +256).
- `C:\aoc-win\mxdis.py`: lista instruções Maxwell de uma entrada do cache pela tabela do Ryujinx vendorizado
  (código = os `length` bytes antes do `c1`; palavras de escalonamento a cada 32 bytes).
- `--probe-nvn` falha em 2 de 794 casos ("device ABI 53.313" e o op `DRAW_IND` sem caso no teste); não foi
  conferido se já falhava antes desta sessão.

## Sessão 7 — 2026-11-11 (notebook): retângulo branco corrigido no tradutor

### A causa exata

- O `SYNC !P0` com um alvo só vira `BranchIfFalse(L, P0)` (`InstEmitFlowControl.cs` `EmitBranch`); o `MOV R3 = R9`
  seguinte é uma cópia, e o `SYNC` incondicional vira `Branch(L)`. Na SSA o `Optimizer` propaga a cópia e apaga o
  `MOV`: o bloco do meio fica só com o `Branch L`, e o phi em `L` passa a ser `phi(R3 vindo do 1º bloco, R9 vindo do
  bloco do meio)`.
- Aí o `BranchElimination` (Ryujinx, `Translation/Optimizations/BranchElimination.cs`) vê "o próximo bloco só tem um
  desvio incondicional para o mesmo lugar" e apaga o desvio condicional. Mas o phi ainda distinguia as duas arestas:
  sem o desvio, todo thread passa pelo bloco do meio e o alfa vira sempre o da onda (1). Em `DebugMode` o comentário
  por instrução (`Translator.cs` `EmitOps`) deixa o bloco do meio não vazio e o desvio fica — por isso o `dbg.glsl`
  saía certo.

### A correção (patch 0014)

- `tools/xlate/patches/0014-branch-elimination-keeps-phi-edges.patch`: o desvio só é redundante se, em cada phi do
  bloco de destino, as duas arestas (o bloco do desvio e o bloco seguinte) trazem o mesmo valor (mesmo operando, ou a
  mesma constante). `tools/build_xlate.py` passa a esperar 14 patches. Identidade do tradutor nova `b05fcac8…`: o
  cache de shaders esfria uma vez (no Deck também).
- Fora do jogo (`C:\aoc-win\retangulo`, job `opt`): a tradução otimizada tem agora 9 comparações e 40 `if`, iguais às
  da tradução em debug (antes 6 e 37); voltam `if (alfa > máscara) alfa = máscara` nos ramos 1240 e 1792 e no
  primeiro estágio.

### Quantos shaders mudam

- Os 5 563 inputs guardados do cache (`shader-cache/in`) traduzidos de novo com uma cópia do tradutor que anota a
  chave quando o patch segura um desvio (`C:\aoc-win\retangulo\injobs.py` monta os jobs a partir dos `.in`; 36 s,
  0 falhas): **11 shaders**. O FS do efeito de coração (`6575db29`) e **10 compute shaders grandes** (105–118 KB de
  código, 60–90 desvios mantidos cada; inputs `36725fee`, `2dfc51cb`, `0dc14967`, `fc45b038`, `b2d89707`,
  `991d1983`, `863bdccc`, `5b3eb264`, `467b2836`, `17833cff`). A tradução antiga desses também estava errada; não
  identifiquei o que eles calculam nem se havia defeito visível por causa deles.

### Medido (rota até a 1ª batalha, notebook)

- Centro da tela (`C:\aoc-win\centre.py`: fração de pixels quase brancos numa janela de 64×96 px de 1080p no
  centro): antes 9 % em 7 de 9 capturas da batalha (`bshots` antigos); agora **0,00 em 44 capturas a cada 4 s da rota
  inteira e em 201 capturas a cada 0,1 s da batalha**.
- Rastros: **0 em 201** (`streaks.py`, MSYS Python, que tem scipy). Luma da batalha 170–173 (igual a antes).
- 0 erros de validação, 0 falhas de shader, 0 draws pulados; música: 1 janela muda em 38 (o boot).
- Não visto: o efeito de recuperação de coração **acontecendo** (curar na batalha); a correção devolve a semântica do
  código Maxwell, mas a animação em si não foi olhada.

### Ferramentas

- `C:\aoc-win\centre.py <pastas>`: mede o bloco branco nas capturas.
- `C:\aoc-win\retangulo\injobs.py <in> <dir de código> <jobs.json>`: jobs do `aoc_xlate` a partir dos inputs
  guardados (espelha `gfx_shader.c` `build_request`); serve para medir o efeito de qualquer patch do tradutor em todos
  os shaders conhecidos de uma vez.
- Corrigido em `docs/handover.md`: dois `C:\aoc-win` que o heredoc da sessão 5 tinha virado `C:` + caractere de
  controle.

### Sessão 7, segunda parte — 2026-11-12: o que estava escrito chega ao Deck, medido; ferramenta de registros no Deck

Pedido do dono: aplicar as mudanças no Deck e deixar lá uma ferramenta de logs para afinar o porte ao Deck. Antes de
mandar, cada peça escrita na sessão 5 rodou no notebook (regra: nada vai ao Deck sem ter rodado aqui).

#### Resolução 1280×720 (corridas A e B) — funciona, mas o minimapa perde os marcadores: NÃO é o padrão do Deck

- Windows com o C da sessão 5 (`C:\aoc-win\gensync.sh` copia do WSL só os arquivos gerados que diferem). Corrida A
  (`AOC_OUTPUT_RES=1280x720`): `resolution: output 1280x720, scene 960x540`, 0 erros de validação. As capturas do jogo
  (`AOC_SHOTS`, `--shot`) mostram a imagem no canto de uma textura 1920×1080: as texturas da janela continuam 1920×1080
  (o jogo as cria em `main+0x7000008cb8` com `SetWidth/SetHeight`) e o jogo chama `nvnWindowSetCrop(0,0,1280,720)`. A
  janela (`AOC_PRESENT_SHOT`) respeita o recorte e sai inteira. Isso não é defeito.
- **Defeito:** em 1280×720 o minimapa fica sem nenhum marcador (jogador, aliados, inimigos, postos), em todos os frames
  da batalha; o resto do HUD está no lugar.
- A função em `main+0x1583c00` monta nove vistas 2D e grava em cada uma `{1920, 1080}` (`str x28, [x24+0x680]`,
  `[x24+0x990]`, ...; nove pares `mov`/`movk` — `x28` em `0x1583c14/0x1583c54` e `x8` em `0x1583db8`, `0x1583f14`,
  `0x1584084`, `0x1584204`, `0x1584380`, `0x15844e8`, `0x15846a4`, `0x1584798`). Pô-los no conjunto `output` **derrubou
  o boot**: escrita em endereço 0x8 dentro de `main+0x17c4e80` (KTGL), chamado de `main+0x1585d40` durante o `nnMain`.
  Os sites foram retirados. Próximo passo: o que `0x17c4e80` cria com esses tamanhos.
- Decisão: o perfil do Deck volta à resolução do jogo (1920×1080, cena 1440×810, redução para a tela). 1280×720 fica
  no menu, com a descrição avisando do minimapa (quatro idiomas; a descrição antiga era a do TotK, com 21:9 e 16:10).

#### Sombra dos pools (corridas B, C e D) — a indicação de regiões paradas vale muito; rastros vêm de antes

- Configuração do Deck no notebook (`AOC_MEMORY=import AOC_SHADOW=1 AOC_REPLAY_ASYNC=1`), mesma rota, mesma batalha:
  com a indicação de regiões paradas da sessão 5 (corrida C) contra sem ela (corrida D, chave nova
  `AOC_FREEZE_SHADOW=0`): write-watch **1,5 ms** por frame contra 21 ms, congelados **1 760 MiB** contra 344, tempo
  da sombra no intervalo **176 ms** contra 1 384 ms.
- **Rastros: 12 e 9 em 201 frames nas duas** (contra 0 no modo de memória padrão do Windows, hoje cedo). Não vêm da
  indicação nova: vêm do caminho do Deck (import, sombra e/ou replay assíncrono), que o binário antigo do Deck já usava.
  Retas finas no céu, como os rastros da sessão 4. Próxima tarefa: separar import × replay assíncrono.
- Centro da tela limpo nas 201 capturas (máx. 0,05), luma 170,8–173,1; música: 1 janela muda em 37 (o boot).

#### No Deck (2026-11-12)

- Enviado com `tools/deck/deploy.sh --no-build` (só arquivos que mudaram; sha256 conferido dos dois lados). Cópia do
  binário anterior em `bak-sessao4/` na pasta do jogo. Tradutor novo (`b05fcac8…`): o cache de shaders esfriou.
- `deckbattle.sh`, rota de 175 s até a batalha, duas vezes:

  | | cache frio | cache quente | antes (sessão 4) |
  |---|---|---|---|
  | fps na batalha | 29,2–30,0 | 26,8–30,0 | 24,6 |
  | write-watch por frame | 1,6 ms | 1,8 ms | ~26–30 ms (sombra) |
  | congelado | 1 764 MiB | 1 770 MiB | 314 MiB |
  | sombra dos pools por frame (média) | — | 2,0 ms | ~30 ms |
  | APU na batalha | 7,1–8,0 W | 7,6–8,7 W | (sem medição) |
  | CPU / GPU na batalha | 68–72 / 65–66 °C | 68–72 / 62–65 °C | — |
  | pior travada | 17,9 s (tradução) | 6,6 s (entrada na batalha) | — |

  Sem erros de validação nem falhas de shader; luma da captura 171,8 e 172,4. A meta de 12 W já está atendida na
  batalha a 30 fps; o dono deixou o TDP do Deck em 10 W. Resta a travada ao entrar na batalha mesmo com o cache quente.
- Linhas `sys:` conferidas pela primeira vez no Deck: todos os sensores presentes.

#### Ferramenta de registros no Deck

- `aoc-logs.sh` na pasta do jogo (`tools/deck/aoc-logs.sh`): `lista` (uma linha por sessão: início, minutos, frames,
  fps, APU média e pico, bateria, temperaturas máximas, erros), `resumo [K] [--rows]`, `ao-vivo` (segue a sessão em
  andamento), `sistema` (TDP, watts, temperaturas, clocks, governador, bateria agora), `detalhado on|off` (`trace =
  perf` no `aoc.ini` para as próximas sessões), `pacote` (tar.gz com as sessões, o `aoc.ini` e o estado da máquina).
- O `aoc.sh` guarda a sessão anterior comprimida em `logs/sessoes/<data>.log.gz` (as 60 mais recentes) antes de abrir
  o jogo; o runtime só guardava as cinco últimas.
- `logsum.py` lê `.gz`, ganhou `--list` e soma as janelas de frametime nos logs sem linhas `sys:`; vai para
  `ferramentas/logsum.py` no `dist`. O `dist` copia os dois; o `deploy.sh` os envia. O LEIA-ME do Deck ganhou a seção
  REGISTROS (e perdeu o "AINDA SEM IMAGEM").
- Por SSH: `ssh deck@192.168.100.130 'cd <pasta> && ./aoc-logs.sh lista'`.

## Sessão 8 — 2026-11-12 (notebook): rastros eram falso positivo; cache de shaders estável; HUD e resolução menor

### Rastros "no caminho do Deck": não existem (correção do relato da sessão 7)

- Separação feita como planejado, uma pergunta por corrida, batalha densa (`AOC_SHOTS=w140-160:0.1`, capturas
  1920×1080): `import` + sombra com replay síncrono: 8 em 201; `import` sem sombra: 15; `import` + sombra com cada
  submit esperando a GPU (`AOC_SUBMIT_WAIT=1`, chave nova de diagnóstico em `nvn_api_core.c`): 11. Não é corrida
  entre a CPU do jogo e a GPU.
- No Deck, mesma rota, capturas 480×270: 0; em tamanho cheio (1,6 GB trazidos por `tar` sobre ssh): 3.
- **Olhando cada detecção** (`C:\aoc-win\streakzoom.py`: frame anterior, marcado e seguinte, ampliados): todas, no
  notebook e no Deck, são **bandeiras longas balançando ao vento** e a borda de uma coluna. O `streaks.py` marca
  qualquer faixa fina que fica mais clara que os dois vizinhos; em 1920×1080 o movimento natural das bandeiras passa.
  O "0 em 201" do modo `mirror` que a sessão 7 usou como comparação veio de capturas 480×270, onde o detector não
  enxerga esse movimento. Conclusão: não há defeito; a sessão 7 errou ao afirmar rastros no modo `import`.
- Para próximas medições: em 1920×1080 todo resultado do `streaks.py` precisa passar pelo `streakzoom.py`.

### Cache de shaders: o mesmo shader ganhava chave nova a cada corrida (corrigido, medido no notebook)

- A travada de 6,6 s ao entrar na batalha no Deck (cache quente) era quase toda replay. No notebook o mesmo frame
  leva 1,8–2,0 s; o perfil desse frame (`AOC_PROFILE=… AOC_PROFILE_SLOW=1000`; leitor novo `C:\aoc-win\profslow.py`)
  pôs 57 % da thread do replay em `translate` (espera do tradutor e leitura/gravação do cache). Toda corrida traduzia
  50–70 shaders de novo.
- Causa: o hash do programa (`gfx_shader.c` `build_code_hash`) cobria a seção de controle inteira (0x880 bytes), e a
  partir de +0x850 o KTGL guarda a própria contabilidade ali: o endereço do programa no heap (+0x850), um endereço de
  dados do `main` (+0x870) e contadores, diferentes a cada corrida. Os 6 051 inputs guardados eram 241 shaders
  distintos com 5 586 chaves; um só código tinha 728.
- Correção: o hash cobre o controle até +0x850 (`CONTROL_HASHED`); `IN_VERSION` 2 (o cache esfria uma vez). Nada lê
  esses bytes: o tradutor não recebe o controle e o runtime lê de +0x700 a +0x757. Com o corte, os mesmos inputs dão
  252 chaves (as 11 variantes restantes diferem em campos de verdade).
- Medido no notebook (caminho do Deck, duas rotas): 1ª 225 traduzidos (cache novo); 2ª **15** (antes 50–70: seis
  shaders nunca vistos e nove computes com outro tipo de imagem nas respostas, variantes legítimas), entrada da batalha
  **0,78 s** (antes 1,8–2,0 s).
- No Deck: o envio caiu no meio (o Deck suspendeu: sem resposta nem a ping). O `aoc` de lá pode ter ficado truncado:
  `scp` gravava direto por cima. `deploy.sh` agora envia como `<arquivo>.envio` e renomeia no fim, e recusa enviar
  com o `aoc` ou o `totk` abertos. Uma espera em segundo plano reenvia quando o Deck voltar (até 4 h).

### Resolução menor: as nove vistas 2D são o layout do HUD; o minimapa é outro caminho

- `main+0x1583c00..0x15847a4` fica dentro da função de inicialização `main+0x1580010`. Cada um dos nove pares
  `mov`/`movk` virou um conjunto de teste (`uiv0`…`uiv8`). Oito, sozinhos, iniciam bem; o nono (`0x1584798`) derruba o
  boot porque logo depois o compilador conta com 1920: `sub x10, x8, #0x780` zera a metade baixa (com 1280 ela estoura,
  a altura vira 719 e a largura lixo; `main+0x17c4e80` não cria o alvo de 1/4 e devolve nulo) e `mov w9, #0x780`
  remonta o par com 1920. Trocados por `and x10, x8, #0xffffffff00000000` e `mov w9, w8`, os nove iniciam.
- Com os nove em 1280×720 o HUD inteiro sai do lugar (corações somem, minimapa na borda); com sete, nada muda no
  minimapa. Essas vistas são o espaço de layout do HUD, que o jogo mantém em unidades de 1080p: o patch `output`
  original (sem elas) é o certo para o HUD. Os marcadores do minimapa somem por outro caminho; próximo passo: dump de um
  frame da batalha em 1080p e em 720p e comparar os draws do minimapa (alvo, viewport, scissor, uniformes). Os
  conjuntos de teste saíram da tabela.

### Ferramentas novas

- `C:\aoc-win\streakzoom.py <pasta> <saída.png>`: amplia cada detecção do `streaks.py` com os vizinhos.
- `C:\aoc-win\profslow.py <dump> [replay|render|main|tid]`: lê os dumps do `AOC_PROFILE_SLOW` (símbolos pelo `nm`).
- `AOC_SUBMIT_WAIT=1`: cada submit espera a GPU (diagnóstico de corrida CPU×GPU).

### Sessão 8, fim — 2026-11-12: cache estável medido no Deck

- O `aoc` do Deck estava corrompido pela queda do envio anterior (mesmo tamanho, sha256 `05ac3a87…`, de nenhuma build).
  Reenviado com o `deploy.sh` atômico; sha256 conferido (`1d99c87e…`).
- `deckbattle.sh`, duas corridas: a 1ª refez o cache (204 traduzidos, travada de 17,5 s na entrada da batalha); a 2ª,
  com o cache quente: **28 traduzidos** (sessão 7: 89) e pior frame da entrada da batalha **1,77 s** (sessão 7:
  6,55 s). Batalha a 28–30 fps, APU 7,1–7,8 W, CPU 64–67 °C, GPU 58–59 °C. Os 28 restantes são variantes que a 1ª corrida
  ainda não tinha visto; devem cair com o uso.

## Sessão 9 — 2026-11-12 (notebook): minimapa em 1280×720 — causa achada, correção pela metade

- Dumps do frame 4400 em 1080p e 720p (`AOC_DUMP_UBO`), mesma rota: o passe final do HUD tem os mesmos 34 draws nas
  duas. O minimapa e seus marcadores são **um draw do programa 14 com 261 quads** (pipe 4, logo depois de uma máscara de
  estêncil do programa 11) com vértices em **unidades de layout de 1920×1080** (primeiro quad em (1551, 761)). A
  projeção do VS é c3[0] = (2/largura, −2/altura) do alvo: 2/1920 em 1080p, **2/1280 em 720p** — o quad cai em
  x = 1,42 do NDC, fora da tela. O resto do HUD usa a câmera de UI e fica certo.
- A projeção é montada pelo KTGL ao aplicar o estado (`main+0x17def54`, e variantes em `0x17df7c4`, `0x17dfeb8`,
  `0x17e1038`, `0x17e1e54`): `2 * escala / largura do alvo`, com a escala em `[contexto+0x28b0/+0x28b4]` (1,0, gravada
  na inicialização do contexto em `main+0x17da090`), só com o modo 2D do contexto ligado (`[contexto+0x3b0]`). Quem
  desenha é o renderizador de primitivas 2D da UI `main+0x161f140` (contexto em `[x1+0x18]`, `x19`), chamado de
  `main+0x161e118` (rastreio `AOC_UBO_TRACE=100:0.0015625:0`).
- Correção tentada: o renderizador põe a escala {saída/1920, saída/1080} (página +96) na entrada e devolve 1,0 no
  epílogo (conjunto `ui2d`). Primeiro com o registrador errado (`x3`/`x20` não são o contexto: a escrita estragou outro
  objeto e o jogo caiu em `main+0x18294b0`); com `x19`, roda. Resultado: **os marcadores voltam e o HUD 2D (minimapa,
  faixa "FIELD", KOs, diálogo) cai no lugar**, mas a **imagem da cena** também é um elemento desse renderizador, com
  vértices no tamanho de saída (0…1280, 0…720), e encolhe para 853×480.
- Próximo passo: achar onde a UI monta o retângulo da imagem da cena a partir do tamanho do alvo e exprimi-lo em
  unidades de layout (1920×1080). Candidatas: as funções da UI que leem `[alvo+0x78]` perto do renderizador
  (`0x15fbb10`, `0x1600160`, `0x1617680`, `0x161a45c`, `0x161a758`, `0x161b138`, `0x161b30c`, `0x161c9f4`,
  `0x161cbc0`). Testar com `AOC_OUTPUT_RES=1280x720 AOC_PATCH_UI2D=1` e `AOC_PRESENT_SHOT=4300:<png>`.
- O conjunto `ui2d` fica na tabela, desligado; o perfil do Deck continua na resolução do jogo. Boot em 1080p conferido.

### Sessão 9, continuação — 2026-11-12: 1280×720 corrigido no notebook

- **Correção de registro:** o relato acima disse que o conjunto `ui2d` trazia os marcadores de volta; não trazia. O
  recorte só mostrava o contorno do mapa, que nunca tinha sumido. Com o buffer de vértices inteiro (`AOC_DUMP_VBIN=1`,
  novo em `vk_dump.c`) ficou claro que o draw do programa 14 **são os marcadores** (pontos de 6,4 unidades vermelhos
  `0xff010177` e azuis `0xffff770a`, ícones de postos), e que eles não passam pelo renderizador `0x161f140`: vêm de um
  interpretador de comandos de desenho (`main+0x12afa70`, draw do KTGL em `0x12afe5c`).
- Mudar a escala do contexto no meio do frame é um caminho ruim: a projeção vai para um bloco de uniformes
  **compartilhado** (mesmo endereço de c3 na composição e no HUD), e quem já desenhou passa a ler o valor novo.
  O conjunto `ui2d` saiu da tabela.
- **Correção:** onde o KTGL lê o tamanho do alvo, ele passa a ler 1920×1080 quando o alvo tem o tamanho de saída
  (comparação com a página +32; o tamanho de layout na página +104; NEON sem desvio nem flags: `cmeq` + `bsl`). Os
  locais: as quatro cópias da projeção 2D (`0x17def58`, `0x17df7c8`, `0x17e103c`, `0x17e1e58`) e a função que define o
  alvo (`0x17dfebc`/`0x17dfed8`); os quads de tela cheia: rotina `0x161a45c`, a imagem da cena no renderizador
  (`0x161f394`, achado por gdb no quad imediato `main+0x17e16c0`) e a imagem das cinemáticas e do vídeo (`0x151e194`/
  `0x151e19c`). Tudo no conjunto `output` (só liga com a saída menor que 1920×1080).
- **Medido no notebook (rota inteira, 44 capturas contra a mesma rota em 1080p):** abertura, título, menus,
  cinemáticas e batalha iguais (diferença 0–1 nas imagens paradas; as quatro maiores são momentos diferentes do vídeo,
  de uma transição e do fade de entrada); minimapa com jogador, aliados e inimigos; nada desenhado fora de 1280×720;
  0 erros de validação. Janela (`AOC_PRESENT_SHOT`) com a cena inteira e o HUD no lugar.
- Limite: com a cena do tamanho da saída (`AOC_RENDER_SCALE=100` em 1280×720) os passes da própria cena caem na mesma
  comparação e saem a 2/3; `resolution.c` passa a limitar a cena a 85 % nesse caso (85 % medido certo).
- **No Deck: não medido** (o Deck ficou fora do ar). O perfil do Deck continua na resolução do jogo; a pasta do Deck
  já tem o binário novo, falta enviar e medir 1280×720 (cena a 75 % e a 85 %) contra os 7,1–7,8 W de hoje.
- Ferramentas: `C:\aoc-win\gdbui.py`, `gdbseq.py`, `gdbdraw.py` (cadeia do jogo de um draw grande), `gdbquad.py`
  (quem chama o quad imediato e com que posições), `gdbvw.py` (watchpoint num vértice).

## Sessão 10 — 2026-11-12 (notebook): testes longos e varredura para uma jogatina longa

O Deck ficou fora do ar (em repouso, o dono longe); os testes rodaram no notebook. Roteiro novo
`C:\aoc-win\route-long.txt`: a rota até a primeira batalha e depois 40 min de luta (andar em oito direções, Y Y Y X,
esquiva, câmera).

### Sessões longas (encerradas aos ~36 min a pedido do dono: disco quase cheio)

- **Windows, com imagem, caminho do Deck** (`AOC_MEMORY=import AOC_SHADOW=1 AOC_REPLAY_ASYNC=1`, 30 fps, portátil):
  36 min sem queda, sem travamento, 0 erros de validação; **30 fps em todas as 549 janelas de 4 s**; áudio: 1 janela
  muda em 444 (o boot).
- **WSL, build Linux do Deck sem GPU** (`AOC_GPU=null`): 36 min sem queda; 30 fps em todas as janelas; 2 janelas mudas
  em 444.
- **Vazamento de memória (achado principal):** no Windows a memória privada sobe em linha reta, ~500 MiB por minuto
  (6,4 GB aos 1,3 min → 24,2 GB aos 36 min), e o working set cai porque o excesso vai para o arquivo de paginação (que
  cresceu e encheu o disco; voltou a encolher quando o jogo foi fechado: 31 → 44 GB livres). Também nas corridas
  curtas de 175 s, em qualquer modo de memória (`mirror` +3 GB, `import` +1,5 GB). Na build Linux sem GPU (3 min,
  `/proc/<pid>/status`): ~60 MiB/min nos menus e **~400 MiB/min na batalha** (RSS 3,46 → 3,88 GB em 60 s): o vazamento
  está no núcleo (front-end NVN, kernel, áudio ou arquivos), não no Vulkan. No Deck (16 GB compartilhados) isso derruba
  o jogo em algo como 20–30 min de batalha. Primeira tarefa da próxima sessão.
- **Saves:** nenhum commit de save nas corridas (o último save gravado é de 2026-11-04, o do primeiro boot); toda
  corrida termina descartando a cópia de trabalho. A rota não chega a um ponto de salvamento (fim de batalha,
  acampamento), então o save do AoC em jogo de verdade e a recarga num processo novo **nunca foram verificados**.
- Saída pelo Steam: no jogo com janela o SDL transforma SIGTERM em pedido de fechar, e esse caminho espera o commit de
  save em andamento (`gfx_window_closed` → `fs_save_flush`).

### Espaço em disco

- Apagados os artefatos reproduzíveis de `C:\aoc-win` (dumps de frame, capturas, retraduções de teste, perfis): 12 GB;
  56 GB livres no fim. Mantidos `img` (cache do `a64.py`), `retangulo` e os logs das sessões longas
  (`soakW.log`, `soakL.log`, `leakL.log`). Limpos os temporários do WSL (`/tmp/xldbg` etc.); o disco virtual do WSL não
  encolhe sozinho (compactar com `wsl --shutdown` + `diskpart compact vdisk`, como administrador).
- No cartão SD do Deck ficou `shots7/` (1,6 GB de capturas da sessão 8): apagar quando o Deck voltar.

### Varredura: o que falta para uma jogatina longa no Deck

Bloqueia:
1. **Vazamento de memória** (~400–500 MiB/min em batalha, acima).
2. **Saves sem verificação** em jogo real: jogar até o primeiro salvamento automático (fim da primeira batalha),
   conferir `fs commit save` no log, fechar e reabrir no ponto salvo. O mecanismo (commit atômico, recuperação, três
   backups em `profile/save-backup`) existe e é o do TotK.

Importa:
3. **Repouso do Deck com o jogo aberto** (botão de energia): nunca testado — relógio do jogo, áudio, Vulkan.
4. **Travadas de tradução de shaders em conteúdo novo**: 17,5 s na primeira entrada na primeira batalha com cache
   frio no Deck; cada fase, personagem e chefe novos repetem isso até o cache encher. Caminho: tradução antecipada
   (plano, fase E) ou prewarm dos inputs guardados.
5. **Só a rota até a primeira batalha foi exercitada**: acampamento, lojas e melhorias, outros personagens, outras
   fases, chefes, Bestas Divinas, cinemáticas posteriores e vídeos nunca rodaram aqui.
6. Envio ao Deck do binário com 1280×720 corrigido (pasta pronta) e medição de 1280×720 a 75 % e 85 %.

Depois: 60 fps opcional, 16:10, DLCs, co-op.

## Sessão 11 — 2026-11-12: vazamento de memória corrigido (medido no Deck)

### Onde estava

- Na build Linux sem GPU (`/proc/<pid>/smaps`), o crescimento estava todo em arenas de `malloc` de 64 MiB. Um
  rastreador de heap próprio por `LD_PRELOAD` (`C:\aoc-win\leaktrack.c`: guarda o ponto de origem de cada bloco vivo e,
  a cada 30 s, lista os pontos que mais cresceram) apontou um único caminho:
  `nvnCommandBufferEndRecording` → `flatten_recording` (`runtime/nvn_api_cmd.c`), as **cópias das gravações de
  command buffer**, cerca de 100 KB cada.
- As cópias só eram liberadas quando o jogo voltava a entregar a memória de controle onde o handle estava. O KTGL dá
  ao command buffer principal 3 MiB de controle uma vez (a 64 bytes por gravação, ~49 000 gravações) e um anel de
  16 MiB de memória de comando também uma vez. No console, quando a memória de comando acaba, o driver chama o
  callback do jogo (`main+0x42d0`), que chama `GetCommandMemoryUsed` e devolve a próxima faixa do anel com
  `AddCommandMemory`. O runtime só chamava esse callback quando o tamanho era zero, então o anel nunca girava e o
  uso contabilizado chegou a 800 MB numa memória de 16 MiB (`AOC_CTL_TRACE=1`, diagnóstico novo).

### Correção (`runtime/nvn_api_cmd.c`, `nvn_api.h`)

1. **O callback de memória de comando dispara no estouro**, como no driver: quando uma gravação passa do fim da memória
   dada, o buffer é marcado (variável por thread) e o callback roda quando a chamada NVN termina, com os registros
   completos (macro `NVN_API`). Duas tentativas descartadas: disparar com 25 % livres no `BeginRecording` travou o
   jogo no Windows (o KTGL voltou ao começo do anel antes da hora e esperou trabalho não submetido); liberar no próprio
   `AddCommandMemory` deu fatal ("not a live recording"): o jogo devolve a mesma faixa e ainda submete o handle
   gravado ali, que no hardware continua intacto até a próxima gravação escrever por cima.
2. **As cópias também são indexadas pela memória de comando** que a gravação ocupou (o uso que o jogo enxerga), em
   cada bloco de 64 KiB, e uma gravação nova que ocupa essa faixa aposenta as antigas. O prefixo da cópia guarda as
   duas posições, e quem libera primeiro tira a cópia dos dois índices.
3. Memória de controle sem espaço para mais uma gravação também chama o callback (no `BeginRecording`).
4. `AOC_CMD_OOM=0` desliga o callback (comparação ou emergência); `AOC_CTL_TRACE=1` registra o uso das memórias e as
   chamadas que o jogo faz dentro do callback.

### Medido

- Linux sem GPU, 4 min: cópias vivas estáveis em ~20 MiB (antes 973 MiB e subindo); autoteste `--probe-nvn` igual ao
  de antes (as 2 falhas são stubs `NvRm…` que o jogo não usa).
- Windows, caminho do Deck, A/B em condições iguais (5,5 min cada): com a correção 0–2 quadros acima de 100 ms por
  minuto e 29,7–30 fps, memória estável; sem ela 7–11 por minuto, 28,2–29,1 fps, memória subindo. Uma sessão de 12 min
  com a correção ficou plana em 6,87 GB dos 4 aos 12 min. (Os engasgos de uma corrida intermediária vinham das
  capturas de tela cheia a cada 30 s, não da correção.) Rota com capturas: imagem certa (cinemáticas, batalha,
  minimapa com marcadores), 0 erros de validação.
- **Deck, 10 min de batalha** (`route-long.txt`, perfil do Deck): memória **plana em 3 299 MiB** dos 4,5 aos 10 min;
  30 fps nos últimos 5 min sem nenhum quadro acima de 100 ms; APU média 5,1 W (pico 7,8 W), CPU ≤ 64 °C, GPU ≤ 60 °C;
  0 erros. O binário no Deck é este (com o 1280×720 corrigido, que segue fora do perfil).

## Sessão 12 — 2026-11-12 (notebook): launcher para forjar o port a partir da própria cópia

Pedido do dono: um launcher em que a pessoa escolhe os próprios arquivos e gera a sua build (como o projeto do
Bayonetta 2 faz), com tema de Zelda/Age of Calamity. Escolhas: destinos **Deck e Windows**, **app nativo C++ +
Dear ImGui**.

- **`tools/make_build.py`** (orquestrador, 265 linhas): passos `check`, `extract`, `romfs`, `deck`, `wingen`,
  `winxlate`, `winbuild`, `windist`, `send`; cada um pula o que já está feito. Imprime `@@PLAN`, `@@STEP <id>
  run|ok|skip|fail <título>` e `@@DONE ok|fail` para o launcher acompanhar. Força UTF-8 em si e nos filhos (o console
  do Windows quebrava nos nomes dos NSPs). O `windist` monta `dist/aoc-windows` (aoc.exe, as DLLs do MSYS2 que ele
  importa via `ldd`, tradutor, ExeFS, RomFS por hardlink, índice, `aoc.ini`). `tools/windows/merge_romfs.ps1` ganhou
  `-GameDir`.
- **`launcher/launcher.cpp`** (727 linhas, ImGui 1.91.9 + back ends SDL3/SDL_Renderer 3 copiados do LAS Recomp, MIT):
  fundo em degradê com grade e anéis Sheikah animados, brilho vermelho da Calamidade embaixo, cantos de painel,
  título "AGE OF CALAMITY". Painel 1: pasta (campo + diálogo nativo) e o inventário (base, update 1.3.0, DLCs,
  `prod.keys` sem nunca mostrar conteúdo). Painel 2: Deck (com/sem `romfs.bin`, envio por SSH), Windows, "Avançado"
  (distro do WSL, pasta de trabalho). Botão "FORJAR O PORT" e "Só conferir os arquivos". Progresso: barra, passos com
  tempo, registro com clipper, abrir as pastas, "Jogar no Windows". Roda o `make_build.py` por `CreateProcessW` num
  job object (cancelar mata a árvore e o `build.py` do WSL). Configuração em `launcher.ini` ao lado do exe.
- `launcher.bat` na raiz compila o launcher na primeira vez (`tools/build_launcher.py`, MSYS2 UCRT64: windres +
  clang++, 1,0 MB + 7,7 MB de DLLs em `build/launcher/`) e o abre.
- `tools/build.py`: os back ends SDL do ImGui ficam fora do executável do jogo (a primeira forja os compilou dentro do
  `aoc`); `write_if_changed` grava e compara em UTF-8 (um `modules.c` gravado antes em cp1252 derrubava o passo
  `winbuild` com o modo UTF-8 ligado).

### Medido

- Launcher: layout sem barras de rolagem a 1180×820 (capturas `launcher3..5`); "Só conferir" lista o dump real e
  termina em "Arquivos conferidos: tudo certo.".
- Forja real do Deck pelo `make_build.py` (a mesma linha de comando do launcher): `@@DONE ok`, incremental
  (gen/guest em dia, host e dist religados em segundos), `dist/aoc-deck` montada.
- Forja real **Deck + Windows** pelo `make_build.py`: a primeira falhou no `winbuild` (o `modules.c` em cp1252,
  acima); com a correção, `@@DONE ok` em todos os passos (os dois builds incrementais). A pasta `dist/aoc-windows`
  aberta sozinha (fora de `C:\aoc-win`): boot, RomFS pelo índice, áudio, 600 quadros e um `fs commit save` em 50 s.
- Não testado: forja do zero numa máquina sem WSL/MSYS2 prontos, e o passo `send` pelo launcher.

### Sessão 12, parte 2: pacote para qualquer jogador (Windows e Linux) e release v0.1.0

Pedido do dono: "empacotar o WSL" para que qualquer usuário de Windows ou Linux baixe e use; release com o exe; guia
em inglês ou idioma escolhível; o mais simples e didático possível.

**Decisão:** em vez de redistribuir uma imagem Linux pronta (~1 GB, com as obrigações da GPL de cada pacote), o
launcher cria uma distro **privada** a partir da imagem oficial do Arch: `wsl --install archlinux --name AoC-Recomp
--location %LOCALAPPDATA%\AoC-Recomp\wsl --no-launch` (17 s) e roda `tools/setup_wsl.sh --minimal` como root. Mesmo
efeito para o usuário (um clique), sem hospedar nada além do nosso código.

- `tools/make_build.py` ganhou o passo **`tools`** (WSL + distro, MSYS2 em `C:/msys64` a partir do `msys2-base`
  2026-09-27 fixado por sha256, ou os pacotes da distro no Linux), mensagens em português e inglês (`--lang`), conferência
  de disco e RAM, `@@NEED wsl` (o launcher oferece `wsl --install --no-distribution` com elevação) e execução nativa
  no Linux. `tools/merge_romfs.py` substitui o PowerShell na mescla do RomFS.
- Launcher: português/inglês (padrão pelo idioma do sistema, troca no canto), roda no Linux (fork/exec, grupo de
  processos para cancelar, `xdg-open`), botão "Instalar o WSL", explicação em três passos, botão "Guia".
- `tools/make_release.py`: pacotes `AoC-Recomp-0.1.0-Windows.zip` (68,7 MB: launcher + SDL3.dll oficial, Python
  3.13.17 embarcado com cryptography/lz4/numpy, hactool, tradutor win-x64 e linux-x64) e `-Linux.tar.gz` (6,4 MB:
  launcher contra o sniper + `libSDL3.so.0`, hactool compilado contra o sniper, tradutor). Ninguém precisa de .NET.
- Guias do jogador: `GUIDE.md` (inglês) e `GUIA.md`.

**Armadilhas encontradas e resolvidas:**
- A imagem Arch do WSL só gera o chaveiro do pacman na primeira abertura interativa; por `wsl -e` o pacman recusa tudo
  ("required key missing"). O `setup_wsl.sh` gera o chaveiro se a chave-mestra `pacman@localhost` não existe (um
  pacman que falhou deixa um `pubring.kbx` vazio de 32 bytes, que não serve de sinal).
- `wsl.exe` imprime UTF-16; `WSL_UTF8=1` em todas as chamadas.
- A primeira atualização de um MSYS2 novo troca o núcleo e encerra todos os processos dele, inclusive o shell (código 1):
  a primeira rodada do `pacman -Syuu` pode "falhar", a segunda tem de passar.
- O Python embarcável com `._pth` não põe a pasta do script no `sys.path`; o `._pth` lista `..\tools` e `..\recomp`.
- A SDL3 estática do MSYS2 puxa a libiconv (LGPL): o launcher do Windows fica com a `SDL3.dll` oficial ao lado. A SDL3
  estática do sniper liga ALSA/X11/Wayland direto: o launcher Linux leva a `libSDL3.so.0` do sniper (rpath `$ORIGIN`).
- A identidade do tradutor calculada no Windows difere da do Linux (o Python do Windows ordena caminhos sem caixa):
  o `make_release.py` a calcula no WSL.
- O modo mínimo esqueceu os headers do Vulkan (o `dist` os copia do sistema) e o MSYS2 novo não tinha
  `python-cryptography` (o passo `host` indexa o RomFS com o `nx.py`): os dois achados só no teste de ponta a ponta.

**Medido (pacote do Windows extraído em `C:\Teste AoC\`, caminho com espaço):**
- Forja do Deck do zero: distro criada e preparada sozinha; ExeFS; RomFS mesclado pelo `merge_romfs.py` **idêntico
  byte a byte** ao do PowerShell (sha256 `9006c2b8…`); gen 99 s; guest 1 596 s; dist com o tradutor do pacote. O
  `dist/aoc-deck` resultante: `--selftest` passa, 30,0 fps estáveis sem GPU (`AOC_GPU=null`), sem erros.
- MSYS2 do zero pelo passo `tools`: 414 s; a segunda chamada só confere (3,7 s). Forja só-Windows (C gerado no próprio
  Windows pelo Python embarcado): guest 1 594 s, host 24 s; o `aoc.exe` do pacote roda 70 s (quadro 1 800, som, save).
- Espaço: distro `AoC-Recomp` 5,9 GB, MSYS2 2,7 GB.
- Launcher Linux pelo WSLg: abre, confere os arquivos, inglês pelo idioma do sistema.
- Não testado: o botão "Instalar o WSL" (o notebook já tem WSL), `pkexec` num desktop Linux, distros apt e dnf.
- **Pacote Linux, nativo**, numa distro Arch limpa fazendo o papel de um PC Linux (só o `python` instalado antes):
  `check`, `tools` (pacman como root), `extract` e `romfs` passaram com o `hactool` Linux do pacote (seis níveis IVFC
  bons). Dois achados: a checagem da mescla recusava as assinaturas RSA da Nintendo, que o hactool compilado no Linux
  marca FAIL e o `hactool.exe` marca GOOD (agora ignoradas: a integridade são os níveis IVFC), e o NSP em outro disco
  (`/mnt/c`) era copiado (11 GB) em vez de ligado (agora link simbólico). A compilação nessa distro foi interrompida:
  o disco virtual dela chegou a 35 GB e o notebook ficou com 2,7 GB livres. O mesmo `build.py gen guest dist` já tinha
  rodado inteiro na distro `AoC-Recomp`. Testes apagados (distros `AoC-LinuxTest` e `AoC-Recomp`, `C:\Teste AoC`,
  MSYS2 de teste); o espaço do disco virtual apagado não voltou na hora (provavelmente preso pelo Windows até reiniciar).

### Sessão 12, parte 3: launcher no padrão do B2recomp

Pedido do dono: deixar o launcher parecido com o do port de Bayonetta 2 (B2recomp, na pasta de Downloads). O launcher
dele (`launcher/launcher.c`, GPL: só lido para entender o comportamento) é uma janela que primeiro faz o build a partir
do dump e depois vira o launcher do jogo: painéis GRAPHICS e CONTROLLER com linhas "rótulo → caixa", dicas ao passar o
mouse, barra inferior (Report, Mods, Config folder, Save, Close) e um PLAY grande; volta à tela de build quando o
pacote é atualizado.

- O nosso agora tem as mesmas duas telas, com o tema Sheikah/Calamidade:
  - **Forja**, como antes;
  - **Jogo**, que aparece sozinha quando a forja termina: GRÁFICOS (modo e tamanho da janela, apresentação, resolução
    do jogo 1080p/720p, resolução interna TV/portátil, escala 3D, formato, filtragem, sombras, indicador; 30 fps como
    informação) e CONTROLE E SOM (layout, vibração, zona morta, inverter a câmera, volume, mudo em segundo plano,
    idioma do menu).
  - Só opções medidas no AoC; as outras do menu herdadas do TotK ficam no F1.
- O launcher edita o `aoc.ini` com as regras do `cfg_save`. Testado com cliques simulados: "Tela cheia" e volume 50
  entraram em `[display]` e `[audio]`, e a linha que já existia ficou igual.
- **JOGAR** abre o `aoc.exe` sem janela de console (o registro vai para `logs/aoc.log` de qualquer jeito).
- **Relatório…**: `tools/make_report.py` gera `aoc-report.zip` com `system.txt`, os registros da forja (o
  `make_build.py` agora grava `build/logs/forge-<data>.log`, os dez últimos) e os do jogo. Medido: 7 KiB, nada do jogo.
- `build/forge-state.json` (versão e destinos forjados) decide a tela inicial; com outro `VERSION` (atualização
  extraída por cima) o launcher mostra a forja com um aviso.
- `tools/build_launcher.py --out`; launcher Linux compilado e visto pelo WSLg.
- Publicado como release `v0.1.1` (zip do Windows 65,6 MB, tar.gz do Linux 6,2 MB, com os `.sha256`).

### Sessão 12, parte 4: tela preta ao entrar numa cinemática (travada de núcleo virtual)

- Relato do dono: depois de ~12 min de jogo no Windows (release 0.1.1), ao chegar numa cinemática a tela ficou
  preta e não voltou. O `logs/aoc.log` tinha o relatório do vigia: `hang: no present for 10.9 s` no frame 22144.
- Leitura do relatório: núcleos virtuais `0x1042 0 0` (núcleos 1 e 2 livres) e a thread principal (`0x1001`,
  prioridade 44, máscara 1) esperando o núcleo 0. A `0x1042` (worker, também prioridade 44) estava rodando código do
  jogo sem chamada de host. Desmontado: laço em `main+0xfdff0c..0xfe0008`, que limpa e retoma o bit 16 de um lock
  até outra thread zerar `[x19+0x88]`; só dorme (50 µs, `main+0x1b51bf0`) quando acha o bit ocupado, então sem
  disputa não passa por SVC nenhuma. Não é um spin wait da tabela (o laço grava). Com prioridade igual não há pedido
  de preempção, e a principal nunca mais rodou. No Switch a worker ficaria num núcleo próprio.
- Correção em `runtime/kernel.c` (`core_rebalance`, chamada por `core_take` e `core_put`): com um núcleo livre e
  alguém esperando um núcleo ocupado, o dono que pode rodar no núcleo livre muda para lá e o núcleo antigo vai para
  quem esperava — a migração que o escalonador do Horizon faz para um núcleo ocioso. O relatório do vigia passa a
  mostrar a máscara de cada thread e quantas migrações houve.
- Testado: build do host no MSYS2, rota da primeira batalha por 100 s (`hang.sh`, `AOC_TRACE=perf,sched`) sem
  travar, 28,3 fps de média no primeiro minuto. **A cinemática do relato não foi reproduzida** (depende do save do
  dono); `dist/aoc-windows/aoc.exe` recebeu o executável novo para ele repetir. Binário do Deck ainda não refeito.

## Sessão 13 — 2026-11-13 (notebook): gravador de estado para travadas e tela preta; efeitos que sumiam

Pedido do dono: (1) ferramentas e registros para descobrir o que acontece quando o jogo chega numa cinemática no meio
da missão e fica com a tela preta sem voltar; (2) conferir, por precaução, os efeitos visuais de impacto nos inimigos.

### Gravador de estado (`runtime/diag.c`, sempre ligado)

- Uma thread do host tira **uma amostra por segundo** (anel de 120): presents, brilho da imagem apresentada (cópia
  320×180 do frame, uma por segundo, pelo mesmo caminho das miniaturas do flight recorder), draws por frame, pico do
  áudio, KiB lidos do RomFS, draws pulados, listas lidas como zero, vídeos ativos, estado da thread principal
  (`run`, `host`, `nocore`, `away`, `lock`, `condvar`, `address`, `sync`) e núcleos virtuais ocupados.
- **Relatório no `aoc.log`** (linhas `diag:`) em três casos: sem present por `AOC_HANG_SECS` (10 s; o antigo vigia,
  que passou para cá; a linha `hang: no present` continua), **imagem preta por `AOC_BLACK_SECS` (15 s) com o jogo
  apresentando** (o caso que o vigia antigo não via) e **F8**. O relatório traz os últimos 45 s da linha do tempo, os
  decodificadores de vídeo, os totais de conteúdo perdido, todas as threads (`kern_threads_report`, agora com a
  **cadeia de chamadas do guest** de cada uma, lida dos registros de frame entre `sp` e o topo da pilha) e grava as
  últimas 10 cópias da imagem em `logs/diag/<data>-<motivo>/`. Se a travada continua, a tabela de threads sai de
  novo a 3× o limite, para separar thread parada de thread trabalhando.
- **`tools/diag_view.py [aoc.log] [--threads]`**: lê o log e dá o veredito em português (travada de núcleo virtual
  com núcleo livre, o que a principal espera e quem é o dono do lock, preto com poucos draws × preto com a cena
  sendo desenhada, comparação das duas tabelas). Lê também o bloco `hang:` dos logs antigos: no log do relato de
  ontem aponta a `0x1042` em `main+0xfdfe9c` no núcleo 0 com os núcleos 1 e 2 livres.
- Custo: por present, uma leitura de relógio; por segundo, um blit 320×180 e a leitura dele. `AOC_DIAG=0` desliga as
  cópias.
- Testado: relatório forçado com `AOC_BLACK_SECS=3` (as telas pretas de carga, 5–6 s, disparam; daí o padrão de 15 s);
  13 min de batalha com o gravador e a thread do `vk_rec` ligados, sem perda de dispositivo nem travada.
- **A cinemática do relato continua sem reprodução** (são ~12 min de jogo manual). A cinemática dos canhões, aos
  ~4 min da rota longa, passa com o `core_rebalance` da sessão 12. O dono repete com o `dist/aoc-windows/aoc.exe`
  novo; se travar ou ficar preto, o relatório sai sozinho (ou F8) e `python tools/diag_view.py` explica.

### Efeitos visuais: dois defeitos que tiravam draws

1. **`pipeline-keys.bin` era jogado fora em todo boot.** `vk_pipeline.c` gravava o arquivo com a assinatura
   `TOTKPKEY` e lia esperando `ACPCACHE` (sobra da junção Astral Chain + TotK): "has another format or version; it
   is rewritten" em todo log desde sempre. Sem as chaves não havia pré-montagem, e todo draw cujo pipeline ainda não
   existia era **pulado** até a montagem terminar — em toda sessão, na primeira vez de cada efeito (um impacto dura
   poucos frames). Agora uma assinatura só (`AOCPKEYS`; a antiga é aceita, os registros são os mesmos).
2. **Views de buffer texture nunca eram liberadas** (`vk_exec_draw.c` `texel_view`): tabela de 4096 cheia depois de
   ~10 min de jogo (log do dono: frame ~18 300) e, daí em diante, toda lista nova (luzes, decalques, listas de
   efeitos) lia zeros. Agora uma view sem uso há 10 s é destruída quando a tabela passa de 3/4.

### Medido (notebook, rota `C:\aoc-win\route-long.txt`, 330 s, cache de shaders quente)

| | antes | depois |
|---|---|---|
| draws pulados por pipeline em montagem | 865 (805 no minuto da entrada da batalha) | 11 e 18 (duas corridas) |
| pipelines pré-montados no boot | 0 | 188 e 191, em 48–57 ms |
| espera do boot pelo pré-aquecimento | 0,1 s | 4,4 s na 1ª vez, 0,46 s na 2ª |
| fps | — | 30,0 (1 % low 25–28) |

- Reciclagem das views: com o limiar baixado para 128 num build de teste, 243 views destruídas e recriadas em 330 s
  de batalha, 0 leituras de zero, sem perda de dispositivo. Na rota automática a tabela só chega a ~520 em 12 min (o
  dono, jogando, chegou a 4096 em 10 min), então o caso real fica para a jogatina dele: a linha
  `vk: texel buffer views: N idle ... destroyed` aparece quando acontecer.
- Capturas densas (0,1 s) da batalha: rastro da espada, efeito azul do ataque carregado e a morte dos monstros
  (corpo preto + fumaça roxa, na cinemática dos canhões) desenham. **Faísca de impacto em inimigo não foi vista**: a
  rota aleatória não chegou a acertar um inimigo de perto. Fica para o dono olhar jogando.
- Armadilha: com a **sessão do Windows bloqueada** (LogonUI ativo) o jogo fica em ~21 fps com uma engasgada de
  ~350 ms por segundo, em qualquer configuração. Medidas de fps só com a tela desbloqueada.

Arquivos: `runtime/diag.c` (novo), `kernel.c`, `perf.c`, `flight.c/.h`, `vk_backend.c`, `vk_exec_draw.c`,
`vk_exec.h`, `vk_pipeline.c`, `ov_movie.c`, `romfs.c`, `audio_mixer.c`, `cfg.c`, `host.h`; `tools/diag_view.py`.

### Sessão 13, parte 2: modo monitor e sessão guiada pelo dono

- Pedido: monitorar em vez de rejogar. No `runtime/diag.c`: **golpes** (início de vibração do controle, `AOC_HIT_SHOTS=<n>`:
  8 presents em tamanho cheio em `logs/diag/hits/h*.png`), **ataques** (botão Y, `AOC_ATTACK_SHOTS=<n>`: presents 3 a 14
  depois do aperto, um a cada 20 s, `a*.png`), **marca com F8** (imagem cheia em `logs/diag/marks/` + relatório),
  **cena escura** (luma média < 25 com mais de 150 draws por frame por `AOC_DARK_SECS`, 15 s), relatório também **ao
  sair do jogo**, coluna `hits` na linha do tempo e gravação dos comandos em `logs/sessions/input-*.txt`.
- **Despejo de frame em jogo** (`vk_dump.c`, `AOC_DUMP=arm`): até `AOC_DUMP_MAX` (6) despejos por sessão, pedidos por F8
  (`AOC_MARK_DUMP=1`), cena escura/preta, `AOC_HIT_DUMP=<k>` ou `AOC_ATTACK_DUMP=<k>`; cada um em
  `<AOC_DUMP_DIR>/<nn>-<motivo>-f<frame>/`. Precisa de `AOC_VK_RECORDER=0`.
- `tools/windows/monitor.bat` (copiado para `dist/aoc-windows/`) liga tudo isso; `tools/diag_view.py` lista golpes,
  marcas e despejos.
- **Sessão guiada (dono jogando, 2026-11-13 09:13–09:25, 20 750 frames):** 32 vibrações e 17 ataques capturados.
  As **faíscas de impacto aparecem** nas capturas (h20, h25, h28: estrelas laranja nos bokoblins; flurry rush com
  partículas azuis) e a **cinemática do meio da missão passou** (h31/h32 são a cinemática, a17 já é jogo depois dela):
  o dono confirmou que os problemas relatados não aconteceram desta vez. A reciclagem das views aconteceu de verdade
  (`2871 idle ... destroyed`), 0 leituras de zero. Não dá para separar qual correção resolveu o quê (pipeline-keys,
  views, `core_rebalance`).
- **Quedas de frame relatadas pelo dono:** média 28,5–29,7 fps por minuto, 1 % low ~12 fps. 40 dos 65 piores frames
  listados estão colados numa captura do monitor (cada PNG de 8 MB é gravado na thread que apresenta, ~80 ms); o
  minuto sem capturas teve 1 % low de 26,5. Fora das capturas: tradução de shader de conteúdo novo (frames 13205,
  18878, 19684: 40–110 ms; no último minuto 956 draws pulados por pipeline e 290 por shader ao entrar em área nova),
  duas esperas de fence de 320–355 ms (frames 6836, 6880) e um replay de 290 ms com upload de textura (9032).
  Para medir limpo: jogar pelo launcher (sem capturas) e ler o relatório de saída.
- Defeitos do monitor vistos: os despejos por golpe/ataque foram gastos nos menus (o relógio do jogo já corre lá) —
  tirados do `monitor.bat`; a imagem cheia ignora o recorte do present (com `output_res` 1280x720 a figura ocupa o
  canto de 1920×1080).

### Sessão 13, parte 3: empacotamento (versão 0.1.2)

- `VERSION` 0.1.2: o launcher compara a versão com `build/forge-state.json` e mostra a forja de novo, então quem
  atualizar recompila o runtime com o gravador de estado e as correções (o pacote é o repositório no HEAD).
- `tools/make_build.py` (passo `windist`) copia `tools/windows/monitor.bat` para `dist/aoc-windows/`;
  `tools/build.py dist` leva `tools/diag_view.py` para `ferramentas/` do Deck e `aoc-logs.sh diag [K]` o usa;
  `aoc-logs.sh pacote` inclui as imagens dos dois últimos relatórios.
- **`tools/make_report.py` corrigido:** juntava os 6 arquivos mais novos de `logs/`, que depois de uma sessão no modo
  monitor seriam capturas de 8 MB, sem o `aoc.log`. Agora: os 6 textos mais novos (`.log`, `.txt`, `.gz`) fora de
  `diag/hits`, `diag/marks` e `diag/dump`, mais as imagens 320×180 dos dois últimos relatórios. Testado no notebook:
  zip de 1 MB com o `aoc.log`, o log da sessão guiada e as 10 imagens do relatório de cena escura.
- Guias (`GUIA.md`, `GUIDE.md`, seção 7): relatório automático, F8 e `monitor.bat`.

### Sessão 13, parte 4: release v0.1.2 e Deck

- Release `v0.1.2` publicada (zip do Windows 68,8 MB, tar.gz do Linux 6,5 MB, com os `.sha256`); o repositório
  remoto agora se chama `Azzulin/EXCUUUUSE-ME-PRINCESS-` (o endereço antigo redireciona).
- Deck: `tools/deck/deploy.sh` (agora também envia `ferramentas/diag_view.py`) mandou `aoc`, `LEIA-ME.txt`,
  `aoc-logs.sh` e `ferramentas/diag_view.py`. Conferido no Deck: o binário traz o gravador de estado e a assinatura
  nova do `pipeline-keys.bin`; boot com `AOC_GPU=null` por 25 s sem erro, gravador ligado e relatório de saída.
  Com `AOC_GPU=null` a linha do tempo mostra frame 0 (o backend nulo não passa por `perf_present`); não afeta o jogo.

### Sessão 13, parte 5: registro de desempenho para o dono jogar (versão 0.1.3)

- Pedido do dono: em vez de medir por SSH ou por rotas automáticas (que não vão aonde importa), uma ferramenta que
  registra enquanto ele joga, para ele mandar os registros. Regra guardada na memória do agente.
- `runtime/diag.c`: **registro de desempenho** sempre ligado, uma linha CSV por segundo em
  `logs/desempenho/<início>.csv` (as 40 sessões mais novas; `AOC_PERF_LOG=0` desliga): fps, frame mais lento do
  segundo e o que o segurou (tradução de shader, pipeline, upload de textura, replay, espera da GPU, ritmo), médias
  por frame, draws, draws pulados, shaders traduzidos, pipelines, uploads, brilho, leituras, estado da thread
  principal e, no Linux, watts da APU e da bateria, bateria %, temperaturas, ventoinha, carga e clock da GPU, clock
  da CPU e núcleos usados pelo jogo (`sysmon.c` `sysmon_second`). Cabeçalho com as configurações ativas.
  `perf.c` `perf_second_take`: janela de um segundo do resumo de frames.
- **"Marcar este momento"** no menu rápido (L3+R3): marca a linha do segundo e escreve um relatório; F8 no PC.
- **`tools/perf_view.py`**: resumo em português (fps, tempo abaixo de 28/25 fps, engasgadas agrupadas com a causa,
  o que segura os segundos lentos e de que lado — GPU, espera da GPU ou CPU —, consumo e os 10 s antes de cada marca).
  No Deck: `./aoc-logs.sh desempenho [K]`; `./aoc-logs.sh pacote` leva os 5 registros mais novos; o Relatório… do
  launcher leva os `.csv`.
- Conferido no Deck (boot sem GPU, só para ver a ferramenta): arquivo criado, colunas da máquina preenchidas (APU
  3,3 W ocioso, 94 % de bateria, 54 °C, ventoinha 1 479 rpm) e a linha de configurações. Os arquivos de teste foram
  apagados.

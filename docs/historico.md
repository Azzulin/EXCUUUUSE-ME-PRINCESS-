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

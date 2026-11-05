# Notas do port — fatos medidos no nosso dump

Este arquivo guarda **números e endereços confirmados no nosso dump** (nunca conteúdo do jogo). Enquanto um fato vier
só de referência externa, ele fica marcado como *(nxnative)* e precisa ser reconferido.

## Entrada — verificada em 2026-11-03

Dump em `Game Files/` (ignorado pelo git), 6 NSPs, ~12,5 GiB no total. Todos os containers PFS0 íntegros (nenhuma
entrada truncada) e todos os cabeçalhos NCA decifram como `NCA3` com o `header_key` do `prod.keys`.

| Pacote | Title ID | Versão | Tamanho | NCAs |
|---|---|---|---|---|
| Base | `01002B00111A2000` | v0 (1.0.0) | 10,65 GiB | Program 10 903 MiB, Control, Manual, Meta |
| Update | `01002B00111A2800` | v327680 (1.3.0) | 0,43 GiB | Program 434 MiB (patch BKTR sobre a base), Control, Manual, Meta |
| DLC — Bônus de pré-venda digital | `01002B00111A3001` | v0 | 0,15 MiB | PublicData 0,1 MiB (praticamente só licença), Meta |
| DLC — Bônus de compra do Expansion Pass | `01002B00111A3002` | v0 | 88 MiB | PublicData 87,7 MiB, Meta |
| DLC — *Pulse of the Ancients* | `01002B00111A3003` | v0 | 218 MiB | PublicData 218,2 MiB, Meta |
| DLC — *Guardian of Remembrance* | `01002B00111A3004` | v0 | 1,11 GiB | PublicData 1 136,8 MiB, Meta |

- SDK do conteúdo: **9.6.0** em todos os NCAs de programa/dados (bate com o perfil do nxnative). Os NCAs Meta dos
  DLCs e do update foram montados com SDKs mais novos (10.4.0 a 13.2.0), o que é normal.
- Geração de chave: **0x0B** em todos; o `prod.keys` tem chaves até 0x15 → suficiente.
- Criptografia por *rights ID*: os NCAs de programa e de dados usam ticket; cada NSP traz o seu `.tik`, então o
  `title.keys` não é necessário (ele não tem entradas deste jogo).
- Bate com o nxnative: "quatro pacotes de DLC, um é só uma licença".

## ExeFS 1.3.0 — extraído e conferido

`tools/extract.py exefs` lê o NCA de programa do update direto do NSP (ticket comum do próprio NSP), verifica a
tabela de hashes e todos os blocos, e grava em `build/v130/exefs/`. `tools/inspect_dump.py` confirma:

| Módulo | Build ID (prefixo) | Arquivo | Imagem em memória | text / ro / data / bss |
|---|---|---|---|---|
| `main` | `c3cf52bf2b05d7310884971b50bcccb8` ✔ | 17,1 MiB | 43,7 MiB | 27,3 / 10,9 / 1,2 / 4,2 MiB |
| `subsdk0` | `3ab92c3444d4ece2f52417b5d8ee86eb` ✔ | 3,4 MiB | 7,1 MiB | 3,4 / 2,3 / 0,19 / 1,1 MiB |
| `sdk` | `95832210b36121e88b4f9b7b66239dad` ✔ | 5,1 MiB | 12,6 MiB | 5,3 / 6,3 / 0,38 / 0,66 MiB |
| total | | | **63,4 MiB (66,5 MB)** | |

- Os três build IDs batem com o perfil 1.3.0 do nxnative → todos os endereços `main+0x...` dele valem para nós
  (ainda conferindo os bytes originais de cada um antes de usar).
- 66,5 MB de módulos confirma o problema do `mem_used`: o host precisa reportar 72 MB, não 64 MB.
- O `.text` do `main` tem 27,3 MiB — cerca de 3,5× o do Astral Chain (7,6 MB de arquivo, 27 788 funções). Esperar
  algo na casa de 100 mil funções só no `main`; tempo de compilação proporcional.
- NPDM: thread principal com prioridade 44, core 0, pilha 1 MiB; **system resource = 0** (usa `SetHeapSize`).

## Censos da Fase 0

| Censo | Resultado |
|---|---|
| Tamanho dos módulos (main / subsdk0 / sdk) | 43,7 / 7,1 / 12,6 MiB em memória (tabela acima) |
| NPDM (prioridade, core, pilha, system resource) | 44, core 0, 0x100000, **0** |
| RomFS da base 1.0.0 | **1 086 arquivos, 10,60 GiB**: dados RDB 8 280 MiB, `.file` 1 290 MiB, vídeos `.webm` 1 246 MiB, `.bin` 29 MiB, índices `.rdb` 13 MiB |
| RomFS 1.3.0 mesclado (`build/v130/romfs.bin`) | **1 101 arquivos, 10,91 GiB**, seis níveis IVFC verificados. Em relação à base: 18 arquivos novos (vários `.rdb.bin1..3` de patch), 3 removidos (`data/LinkData.bin`, `data/LinkInfo.bin`, `asset/AtelierToolVersion.txt`), 120 com tamanho diferente |
| DLCs | 3001: 1 arquivo (licença); 3002: 4 arquivos, 87 MiB de dados RDB; 3003: 15 arquivos, 218 MiB; 3004 (*Guardian of Remembrance*): 186 arquivos, 1,11 GiB — 561 MiB `.rdb.bin3_*`, 389 MiB de vídeos, 184 MiB `.file` |
| Imports do `main` | 387: `nn::audio` 88, libc 67, `nn::os` 56, `nn::hid` 40, `nn::fs` 25, `movie` 20, `nn::settings` 16, `nn::oe` 14, `nn::nfp` 14 (amiibo), `nn::time` 8, `nn::vi` 7, `nn::codec` 6, `nn::mem` 6, `nn::account` 3, `nn::aoc` 2 (DLC), `nn::util` 2, `nn::err` 1, mais `nv::InitializeGraphics`, `nv::SetGraphicsAllocator` e `nvnBootstrapLoader` |
| Imports do `subsdk0` (vídeo) | 650: libc 275, `android` 208 (a biblioteca de vídeo é baseada em código Android), C++ 102, `nn::os` 25, `nn::audio` 19, `nn::sf` 11 |
| Imports do `sdk` | 13 (libc) |
| Imports × overrides de referência | `main`: 65 de 383 já têm override no Astral Chain ou no TotK Recomp (hid 17, nfp 13, oe 10, time 7, vi 4, fs 3, account 3...). Os outros são resolvidos pelo próprio `sdk` recompilado e só viram trabalho quando chegam num serviço do sistema. Novos em relação às referências: `nn::ec::ShowShopAddOnContentList`, `nn::aoc::CountAddOnContent`, Opus multistream, cópia de segurança de saves (`nn::fs::CreateFile/DeleteFile/Commit`...) — `tools/census_overrides.py` |
| Imports sem dono | nenhum: tudo que `main` e `subsdk0` importam é exportado pelos módulos (só sobram marcadores do linker `__rel_*` e um símbolo fraco do SDK) |
| Exceções C++ / `longjmp` nos imports | **nenhum** → a otimização de registradores callee-saved do lifter pode ficar ligada |
| Nomes NVN pedidos × `nvn_procs.inc` | — (precisa rodar o jogo até `nvnBootstrapLoader`; nxnative lista 523) |
| Funções / jump tables / instruções não suportadas | **101 212 funções, 0 instruções não suportadas** — seção "Fase 1" abaixo |
| Shaders por estágio | **40 729 únicos** (37 045 pixel, 3 441 vertex, 241 compute, 2 geometry) — seção abaixo |
| Formatos de textura | **nenhum ASTC** — tabela abaixo |

## Conteúdo dos RDB do 1.3.0 (`tools/census_rdb.py`)

994 arquivos RDB (`*.rdb.bin*` e `asset/data/*.file`), lidos só pelos cabeçalhos das entradas IDRK. "Real" é o
tamanho descomprimido. DLCs ainda não entram (ficam nos NSPs de DLC).

| Tipo (KTID) | Magic | O que é | Entradas | Guardado | Real |
|---|---|---|---|---|---|
| `afbec60c` | `GT1G` | texturas G1T | 40 198 | 4,4 GiB | 10,3 GiB |
| `563bdef1` | `_M1G` | modelos G1M | 9 698 | 1,4 GiB | 2,5 GiB |
| `7bcd279f` | `_S2G` | shaders G2S (bate com o nxnative) | 23 108 | 0,8 GiB | 2,3 GiB |
| `0d34474d` | `TSRS` | som (KTSR) | 969 | 1,3 GiB | 1,3 GiB |
| `786dcd84` | `_N1G` | ? (poucas entradas grandes) | 20 | 140 MiB | 775 MiB |
| `5b2970fc` | `2FTK` | ? (provável fonte KTF2) | 23 | 188 MiB | 688 MiB |
| `20a6a0bb` | `_DOK` | recursos de sistema do engine (inclui 151 shaders) | 5 062 | 75 MiB | 618 MiB |
| `bbd39f2d` | `ASRS` | som (o mesmo tipo que travava a inicialização no nxnative) | 1 270 | 478 MiB | 525 MiB |
| `6fa91671` | `_A1G`/`_A2G` | animações | 12 209 | 250 MiB | 453 MiB |

O relatório completo (todos os tipos) fica em `build/v130/rdb-census.json`.

### Formatos de textura

| Código G1T | Formato | Texturas |
|---|---|---|
| `0x5f` | BC7 | 11 819 |
| `0x59` | BC1 | 6 110 |
| `0x5d` | BC5 | 1 941 |
| `0x5b` | BC3 | 594 |
| `0x5c` | BC4 | 521 |
| `0x5e` | BC6H | 191 |
| `0x06` / `0x08` | BC1 / BC3 (códigos antigos) | 3 |
| `0x01`–`0x04` | não comprimidos; nas amostras, placeholders 1×1 (0x03 ainda não conferido) | 19 172 |

Os códigos 0x59–0x5F vêm da Amicitia Wiki e foram conferidos aqui pela razão tamanho/pixels: BC1 e BC4 dão
5,33 bits por pixel (4 bpp + mipmaps), BC5/BC6H/BC7 dão 10,67 (8 bpp + mipmaps).

**Consequência:** o AoC não usa ASTC. Todo o conteúdo comprimido é BC1–BC7, que o RDNA2 do Steam Deck (e qualquer GPU
de PC) amostra nativamente. Some a decodificação ASTC, o maior custo de textura do Astral Chain no Deck.

## Shaders (`tools/census_shaders.py`)

Levantamento estático, sem rodar o jogo: lê as saídas do compilador GLSLC dentro dos containers G2S e `_DOK` dos RDB
do 1.3.0 e no `main`. Roda em ~30 s.

| Estágio | Únicos | Ocorrências | Código Maxwell |
|---|---|---|---|
| pixel | 37 045 | 52 854 | 576 MiB |
| vertex | 3 441 | 50 378 | 23 MiB |
| compute | 241 | 262 | 2,8 MiB |
| geometry | 2 | 2 | — |
| **total** | **40 729** | **103 496** | **~602 MiB** |

- Origem dos únicos: 40 485 nos 23 108 containers G2S, 127 em 2 dos 5 062 containers `_DOK`, 117 no `main`.
- Controles: 27 300 de 0x880 bytes, 13 426 de 0x850 e 3 de 0x7d1 (o formato antigo que o nxnative trata à parte).
- **As 40 729 chaves batem uma a uma com o `shader_map.tsv` do nxnative**, inclusive o estágio de cada uma (e com
  as "40 729 chaves extraídas" do MacNativeGames). Ou seja: as tabelas do nxnative para este jogo
  (`shader_facts.tsv`, `shader_pairs.tsv`) valem para o nosso dump sem ajuste.
- Inventário completo (chave, estágio, ocorrências, bytes) em `build/v130/shader-inventory.tsv`, fora do git.

Consequências para o plano:

- Pixel shaders dominam: quase 600 MiB de código para traduzir. A tradução AOT tem que ser em paralelo e com cache
  por chave; no PC é o passo mais longo da instalação.
- Só 3 441 vertex shaders para 50 mil usos: muitos materiais compartilham vertex shader, o que ajuda a montar
  pipelines por partes (graphics pipeline library).
- Próximo passo de shader: teste de tradução com o tradutor do Ryujinx + `spirv-val` (precisa do .NET 10 no WSL).

## DLCs (`census_rdb.py --dlc`, `census_shaders.py --dlc`)

Lidos direto dos NSPs, sem extrair. 176 arquivos RDB nos três DLCs com conteúdo:

| DLC | Arquivos RDB | Principal conteúdo (descomprimido) |
|---|---|---|
| `…3002` (bônus de compra) | 3 | texturas 203 MiB |
| `…3003` (*Pulse of the Ancients*) | 14 | texturas 349 MiB, animações 26 MiB, modelos 21 MiB, fontes/UI 18 MiB, som 24 MiB |
| `…3004` (*Guardian of Remembrance*) | 159 | texturas 673 MiB, modelos 245 MiB, som 231 MiB, fontes/UI 158 MiB, animações 34 MiB |

- **Nenhum container de shader nos DLCs**: o conteúdo extra usa os 40 729 shaders do jogo base. Portar os DLCs não
  aumenta o trabalho de tradução de shaders.
- Texturas dos DLCs também só em BCn (o total de formatos do `rdb-census.json` já inclui os DLCs).

## Fase 1 — lifter nos três módulos (`recomp/`, vindo do Astral Chain)

Gerado no ambiente de nuvem da sessão (2 núcleos, 7 GB) a partir do ExeFS 1.3.0:

| Módulo | Funções | Jump tables | `br` por dispatch | Fallbacks "todas as labels" | Traps (sites de SO) | Não suportadas | C gerado |
|---|---|---|---|---|---|---|---|
| `main` | 52 412 | 1 706 | 5 140 | 21 | 87 701 | **0** | 440 MB |
| `subsdk0` | 13 618 | 335 | 3 970 | 1 | 16 189 | **0** | 62 MB |
| `sdk` | 35 182 | 534 | 8 907 | 13 | 38 967 | **0** | 97 MB |
| **total** | **101 212** | 2 575 | | | | **0** | **~600 MB** em 374 arquivos |

- Geração completa em **161 s** com 2 workers. Descoberta de funções: menos de 1 s por módulo.
- O `main` do AoC dá ~1,9× as funções do `main` do Astral Chain (27 788), não 3,5×: as funções do KTGL são maiores.

Testes contra Unicorn (os mesmos do Astral Chain), todos sobre o código do nosso dump:

| Teste | Resultado |
|---|---|
| `tests/flags_check.py` | 2 000 484 pares de operandos, 0 divergências (-O0 e -O1) |
| `tests/diff/lift.py` (60 000 codificações sorteadas dos 3 módulos) | **179 958 casos, 0 falhas**; só 19 palavras "não suportadas", todas dado não decodificável (`?` no capstone) |
| `tests/diff/func.py` (funções inteiras: laços, jump tables, chamadas, SIMD) | **627 funções, 4 246 casos, 0 falhas** |
| `tests/diff/simd.py` (sem dados do jogo; 2026-11-04) | 1 048 640 codificações checadas (lifter e Unicorn concordam na validade de todas), **159 976 casos, 0 falhas** |
| `tests/diff/atomic.py` (sem dados do jogo; 2026-11-04) | 198 testes, **12 672 casos, 0 falhas** |
| `tests/jumptables_check.py` | `main` e `sdk`: **0 divergências**. `subsdk0`: 1 divergência (`subsdk0+0x5da14`), o resolvedor dá 7 alvos e o oráculo 6 — superconjunto seguro: o limite `cmp w16,#5` fica nos predecessores e os "facts" de entrada de bloco não usam condições de aresta. A divergência do `main` (`main+0x1867d08`) foi corrigida em `recomp/jumptables.py` `_bounds`: um `cmp wN` agora limita também o índice de 64 bits quando ele cabe em 32 bits por construção. 17 `br` computados não resolvidos caem no dispatch. |

Compilação (clang 18, flags do Astral Chain: `-O1 -march=x86-64-v3`), sem nenhum erro nos 44 arquivos compilados:

- Arquivos comuns (250 KB a 3 MB, centenas de funções): ~5–7 s por MB de C num núcleo.
- **35 funções gigantes no `main`** (cada uma num arquivo próprio, 1–7 MB de C, 69 MiB no total) são o problema:
  `main_0041.c` (3 MB, 1 função) levou ~15 min e `main_0039.c` (5 MB) ~19 min a -O1, com até 1,8 GB de RAM cada;
  a -O0 a de 3 MB passou de 7 GB e foi morta. É o principal risco de tempo de build (e o pior para compilar no Deck).
- Próximo passo: medir o resto e atacar as gigantes no gerador (quebrar a função em blocos que se chamam com
  `musttail`, ou desligar passes caros só nesses arquivos), antes de montar o build completo.

### Build completo — medido em 2026-11-04 (notebook, i5-11400H 6c/12t, WSL Arch com 11 GB, clang 23.1.4)

| Passo | Tempo | Pico de RAM |
|---|---|---|
| `gen` (101 212 funções, 374 arquivos, ~600 MB de C, 5 workers) | 2 min 46 s (1 min 05 s regenerando só o que mudou) | 0,55 GB |
| `guest` (377 arquivos → `libaoc_guest.a` de 259 MiB, `-j10`) | **~48 min** de relógio no total | 1,6 GB num clang |
| `host` (runtime + link de `aoc`, 222 MB) | ~1 min o runtime, 2 s o link | — |
| `dist` (runtime contra o sniper + link + pasta) | 28 s (mais ~1 min na primeira vez: sysroot e zstd) | — |

- **40** arquivos de função gigante (limite de 900 KB de C). As 4 maiores (5–7 MB) levaram ~45 min rodando de 2 em 2;
  as 36 restantes (≤ 3,3 MB, ~1,2 GB de RAM cada) levaram 8 min rodando de 4 em 4 (`--big-jobs 4`). Com 11 GB, 4 ao
  mesmo tempo cabem com folga. Nenhuma falha de compilação.
- **Spin waits** (`tools/spin_waits.py`): **1 112** — `main` 1 090, `subsdk0` 12, `sdk` 10 (o TotK 1.4.3 tem 857, o
  Astral Chain 32). Tabela em `recomp/patches-v130.txt`; regenerar com ela mudou 67 arquivos de C, nenhum gigante.
- O executável de desenvolvimento (Arch, glibc 2.44) **não serve para o Deck**: o `dist` linka contra o sysroot
  sniper e o resultado pede no máximo **GLIBC_2.29**.

## Fase 2 — boot (2026-11-04, `AOC_GPU=null`, WSL)

| Marco | Resultado |
|---|---|
| `aoc --selftest` | passa: 3 módulos, 101 212 funções na tabela de dispatch (63,4 MiB, montada em 24 ms), 19 ns por busca |
| Carga | `main` 142 157 relocações / 387 imports, `subsdk0` 19 177 / 650, `sdk` 31 396 / 13; todos resolvidos |
| `nn::init::Start` → construtores | `main` 25, `subsdk0` 44, `sdk` 109 entradas de `init_array`, sem erro |
| RomFS | índice de 1 101 arquivos; metadados 0xe1c4 bytes em 0x2ba8463e8 do `romfs.bin`; `MountRom` pelo cache montado no host |
| `--boot` (até o 1º NVN) | passa: `nvnBootstrapLoader("nvnDeviceGetProcAddress")` de `main+0x9f80`, 79 SVCs, 2 threads, 39 chamadas ao host |
| Laço principal | **30,0 fps estáveis, intervalo de present 2, relógio do jogo 0,999–1,000× o real**; thread principal em `main+0xfdec50` (chamada de `nnMain+0x37c`), dormindo 1 ms entre frames |
| Threads | 64 (a maioria trabalhadoras KTGL esperando fila), mais `audren` |
| NVN | **8 756 `ProgramSetShaders`** no início (o nxnative registra ~8 705 programas no primeiro frame), ~490 texturas, 9 pools |
| Save | `save:` montado no perfil do host; primeiro commit grava 1 arquivo de 1,0 MiB (`svdt`) |
| Áudio | `audren` REV8, 48 kHz × 240, 132 mix buffers, 138 vozes, 16 efeitos, 19 submixes, 85/1 800 splitters (bate com o nxnative). Sem entrada o jogo fica nas telas do primeiro boot, em silêncio; com A em 6, 8, 10, 12, 14 e 16 s o PCM sai **não-silencioso** (rms 0,12, pico 0,71). Nenhum decodificador `hwopus` foi aberto até aqui |
| Vídeo de abertura | `movie/Movie001.webm` aos ~28 s (com os A): VP9 1280×720, 4 buffers de entrada de 2 MiB, 8 frames de saída; decodificado pelo libvpx do host a **1,3–1,55 ms por frame** (máx. 13,8 ms), 2 400 frames sem erro. **Som do vídeo em silêncio** (a investigar) |

Pontos que o boot do AoC expôs no runtime herdado (corrigidos):

- `fsp-srv` vira **domínio CMIF** no SDK 9.6 (`IsEnabledAccessLog` → `GetFileSystemProxyServiceObject`): o
  `DomainInHeader` vem antes do cabeçalho `SFCI`; o `ipc.c` do Astral Chain lia na ordem inversa e nunca serviu
  domínio de verdade. Agora: `ConvertToDomain` devolve o objeto 1, pedidos vão ao objeto pelo ID, subinterfaces viram
  IDs depois dos dados, tipo 2 fecha o objeto.
- `nn::hid::GetTouchScreenState<1>` (o AoC lê a de 1 toque) abortava o SDK com 2202-0041 (`0x52ca`); a de 16 toques
  do runtime escrevia só 4 bytes do estado. Agora o estado inteiro é zerado e o número da amostra avança.
- `nn::oe` copyright framebuffer (3 funções) e `nn::aoc::CountAddOnContent` não tinham tratamento.
- `nvnCommandBufferSetCopyImageStride` (no vídeo de abertura) não existia no front end NVN: agora é o passo de
  camada das cópias buffer↔textura, como no nxnative (`bufferImageHeight` no Vulkan).
- `mem_used` de 72 MB do nxnative **não se aplica**: este runtime calcula a memória usada pelo tamanho real dos módulos
  (`memory.c image_bytes`), e o problema só existia porque o nxnative fixava 64 MB.
- API NVN: o SDK 9.6 pede 53.313, o mesmo valor que o runtime do Astral Chain já informa (nxnative `hle_nvn.c`).
- Vulkan no WSL: só o Dozen (Vulkan 1.2 sobre D3D12, RTX 3050 e Intel UHD), sem `VK_EXT_external_memory_host` —
  o back end Vulkan precisa do Deck (RADV), de Linux nativo ou de um build Windows.

## Primeira execução no Steam Deck (2026-11-05, pelo dono; log lido por SSH)

| Item | Medido |
|---|---|
| Sistema | SteamOS 3.9.5, kernel 7.2.7-valve2, jogo no cartão SD (`/run/media/deck/<uuid>/Games/aoc-deck`) |
| GPU | `AMD Custom GPU 0405 (RADV VANGOGH)`, Mesa 26.2.0-devel, Vulkan 1.4.350; graphics pipeline library e fast-link sim; memória UMA (pools importados) |
| Perfil | "Steam Deck" detectado sozinho (DMI): 30 fps, modo portátil, tela cheia; SDL 3.4.18 com driver x11 |
| Execução | 1 391 frames em 46,5 s, **29,9 fps de média**, 1 % low 23,8 fps; pior frame 156,6 ms (124,5 ms de espera de present); sem crash, encerrado pelo jogador fechando a janela |
| Áudio | `Audio Coprocessor Speaker`, 48 kHz estéreo float |
| Imagem | **tela preta**: nenhum tradutor de shaders (`translator not found`, 19 626 vezes; 9 804 traduções falhadas) — Fase 3 |
| Steam | o atalho "não Steam" nunca foi criado (`shortcuts.vdf` sem entrada); resolvido com `instalar-atalho.sh` (entrada `.desktop`, que a janela do Steam lista) |

## Primeira batalha na RTX 3050 (2026-11-05, build nativo do Windows)

- **Seção de controle NVN de compute**: +0x748 = tamanho do grupo (3 × u32), **+0x754 = memória compartilhada em
  bytes** (0x130 a 0x1230 nos compute do AoC; o `fbb562b2` de colisão usa 0x1230 = 4 656), +0x758 parece ser memória
  local por thread (0x10, 0xd0), +0x760 = 0x600 em todos.
- **Spinlock com yield** em `main+0x157ab64`: `while (*lock) nn::os::YieldThread()` (PLT `main+0x1b51c00`;
  `YieldThread` = `sdk+0xd4b20`, `svcSleepThread(-1)`). Três workers de prioridade 44 o rodam ao mesmo tempo.
- **Batalha (frame 4400, resolução interna 1440×810 com resolução dinâmica)**: 96 passes; G-buffer no pass 9 (945
  draws), grade de froxels/luzes no pass 39 (dispatch 23×13×16, blocos de 64 px × 16 fatias), sol no pass 40, luzes
  locais no pass 53, bloom 73–86, histograma de luminância 87–89 (64 bins R32UI lidos como buffer texture), tonemap
  90, HUD 94–95. Exposição em 2×1 R32F: 0,0103 e 97,0 (o inverso).
- **Buffer textures da iluminação** (fs): slot 16 R32UI 1 009 568 elementos (cabeçalhos + índices por célula: contagem
  de pontuais em `>>16`, de spots em `&0xffff`), 17 RGBA32F 256 (posição + raio), 18 RGBA32F 768 (3 por luz: cor…),
  19 R32UI 768 (3 por luz: tipo 2, máscara 0xff, 0), 20 RGBA32F 160 (5 por spot), 21 R32UI 96, 25 R32UI 12 (tabela
  de materiais; bits 16–23 escolhem a linha da rampa 256×8).
- **Custo na batalha** (i5-11400H + RTX 3050): 30 fps estáveis; GPU 6,7 ms, replay 7,8 ms, thread do jogo ocupando os
  33 ms (`bound: cpu`). Entrada da batalha com cache frio: frame de 20,6 s (pipelines 13,6 s, tradução 4 s).

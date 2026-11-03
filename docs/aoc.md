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
| `tests/jumptables_check.py` | `sdk`: 0 divergências. `main` e `subsdk0`: **1 divergência cada**, nos dois casos o resolvedor dá alvos a mais que o oráculo (superconjunto), porque não usa um `cmp w8,#3` / `cmp w16,#5` que limita um índice já mascarado por `ubfx`/`and`. É seguro em execução (casos a mais nunca tomados), mas o critério do plano é 0: ajustar `recomp/jumptables.py` (`main+0x1867d08`, `subsdk0+0x5da14`). 17 `br` computados não resolvidos caem no dispatch. |

Compilação (clang 18, flags do Astral Chain: `-O1 -march=x86-64-v3`): amostras de 250 KB a 2,9 MB compilam sem
erro a ~5–7 s por MB de C num núcleo. Os ~600 MB dão por volta de 1 hora-núcleo: ~30 min em 2 núcleos, alguns
minutos num PC de 8–16 threads, ~10–15 min no Steam Deck (o que reforça compilar no PC).

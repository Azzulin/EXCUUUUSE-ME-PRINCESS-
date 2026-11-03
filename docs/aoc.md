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
| RomFS do update 1.3.0 | seção BKTR (patch sobre a base) — falta o passo de mesclagem |
| DLCs | 3001: 1 arquivo (licença); 3002: 4 arquivos, 87 MiB de dados RDB; 3003: 15 arquivos, 218 MiB; 3004 (*Guardian of Remembrance*): 186 arquivos, 1,11 GiB — 561 MiB `.rdb.bin3_*`, 389 MiB de vídeos, 184 MiB `.file` |
| Imports do `main` | 387: `nn::audio` 88, libc 67, `nn::os` 56, `nn::hid` 40, `nn::fs` 25, `movie` 20, `nn::settings` 16, `nn::oe` 14, `nn::nfp` 14 (amiibo), `nn::time` 8, `nn::vi` 7, `nn::codec` 6, `nn::mem` 6, `nn::account` 3, `nn::aoc` 2 (DLC), `nn::util` 2, `nn::err` 1, mais `nv::InitializeGraphics`, `nv::SetGraphicsAllocator` e `nvnBootstrapLoader` |
| Imports do `subsdk0` (vídeo) | 650: libc 275, `android` 208 (a biblioteca de vídeo é baseada em código Android), C++ 102, `nn::os` 25, `nn::audio` 19, `nn::sf` 11 |
| Imports do `sdk` | 13 (libc) |
| Imports sem dono | nenhum: tudo que `main` e `subsdk0` importam é exportado pelos módulos (só sobram marcadores do linker `__rel_*` e um símbolo fraco do SDK) |
| Exceções C++ / `longjmp` nos imports | **nenhum** → a otimização de registradores callee-saved do lifter pode ficar ligada |
| Nomes NVN pedidos × `nvn_procs.inc` | — (precisa rodar o jogo até `nvnBootstrapLoader`; nxnative lista 523) |
| Funções / jump tables / instruções não suportadas | — (Fase 1, dry-run do lifter) |
| Shaders por estágio | — *(nxnative: 40 726)* |
| Texturas ASTC × BCn | — |

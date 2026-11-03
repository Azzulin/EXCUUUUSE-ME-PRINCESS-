# Notas do port — fatos medidos no nosso dump

Este arquivo guarda **números e endereços confirmados no nosso dump** (nunca conteúdo do jogo). Enquanto um fato vier
só de referência externa, ele fica marcado como *(nxnative)* e precisa ser reconferido.

## Entrada

| Item | Valor | Status |
|---|---|---|
| Base | 1.0.0, `01002B00111A2000` | a conferir |
| Update | 1.3.0 (v327680), `01002B00111A2800` | a conferir |
| DLCs | Expansion Pass (*Pulse of the Ancients*, *Guardian of Remembrance*) — 4 pacotes, 1 só licença *(nxnative)* | a conferir |
| Build IDs | ver `tools/data/known-builds.json` *(nxnative)* | a conferir com `tools/inspect_dump.py` |

## Censos da Fase 0

| Censo | Resultado |
|---|---|
| Tamanho dos módulos (main / subsdk0 / sdk) | — |
| NPDM (prioridade, core, pilha, system resource) | — |
| RomFS mesclado: arquivos / GB | — |
| DLCs: arquivos / GB | — |
| Imports `nn::*` × overrides | — |
| Nomes NVN pedidos × `nvn_procs.inc` | — |
| Funções / jump tables / instruções não suportadas | — |
| Exceções C++ / `longjmp` nos imports | — |
| Shaders por estágio | — *(nxnative: 40 726)* |
| Texturas ASTC × BCn | — |

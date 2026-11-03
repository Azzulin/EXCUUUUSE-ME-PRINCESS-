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

| Item | Valor | Status |
|---|---|---|
| Build IDs do ExeFS 1.3.0 | ver `tools/data/known-builds.json` *(nxnative)* | a conferir após a extração (`tools/inspect_dump.py`) |

## Censos da Fase 0

| Censo | Resultado |
|---|---|
| Tamanho dos módulos (main / subsdk0 / sdk) | — |
| NPDM (prioridade, core, pilha, system resource) | — |
| RomFS mesclado: arquivos / GB | — (Program da base: 10,6 GiB comprimido em NCA) |
| DLCs: arquivos / GB | — (1,4 GiB em NCA) |
| Imports `nn::*` × overrides | — |
| Nomes NVN pedidos × `nvn_procs.inc` | — |
| Funções / jump tables / instruções não suportadas | — |
| Exceções C++ / `longjmp` nos imports | — |
| Shaders por estágio | — *(nxnative: 40 726)* |
| Texturas ASTC × BCn | — |

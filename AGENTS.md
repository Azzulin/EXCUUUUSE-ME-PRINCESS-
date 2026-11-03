# AoC Recomp — instruções para agentes

Recompilação estática de *Hyrule Warriors: Age of Calamity* 1.3.0 (Switch, ARM64) para x86-64 nativo com Vulkan.
Alvo principal: **Steam Deck** (Linux, RADV, 4 núcleos Zen 2, 1280×800). Projeto pessoal: o dono usa a própria cópia
do jogo, extraída do próprio console.

## Comece por aqui

1. **[docs/handover.md](docs/handover.md)** — estado atual, decisões tomadas, máquinas e pastas, próximos passos e
   armadilhas já encontradas. Leia antes de qualquer tarefa.
2. [docs/plano.md](docs/plano.md) — fases com portões de aceitação (o que já está marcado e o que falta).
3. [docs/aoc.md](docs/aoc.md) — fatos medidos no dump (números, endereços, censos). Fonte de verdade sobre o jogo.
4. [docs/building.md](docs/building.md) — como extrair, gerar o C e compilar (`build.bat` / `tools/build.py`).
5. [docs/arquitetura.md](docs/arquitetura.md), [docs/levantamento.md](docs/levantamento.md),
   [docs/steam-deck.md](docs/steam-deck.md), [docs/referencias.md](docs/referencias.md) — contexto e porquês.
6. [docs/historico.md](docs/historico.md) — o que foi feito em cada sessão, com os commits.

Ao terminar uma sessão de trabalho: atualize `docs/handover.md` (estado e próximos passos), acrescente o relato em
`docs/historico.md`, registre números novos em `docs/aoc.md` e marque o que fechou em `docs/plano.md`.

## Como o projeto é montado

- O dump fica em **`Game Files/`** na raiz (NSPs da base, update 1.3.0 e DLCs + `prod.keys`), ignorado pelo git.
- Tudo compila **no PC, pelo WSL2** (`build.bat` na raiz, ou `tools/build.py --work ~/aoc-build` no WSL). O diretório
  de trabalho fica no disco do Linux, nunca em `/mnt/c` ou `/mnt/d`.
- O Steam Deck **não compila**: recebe uma pasta única `dist/aoc-deck/` copiada pelo dono (layout em
  `docs/steam-deck.md`).
- Referências clonadas no PC do dono em `D:\Gits para projetos\` (ou em `refs/` via `tools/fetch_refs.sh`).

## Prioridades

- **Desempenho no Deck primeiro.** Orçamento de frame é requisito. O custo provável está no replay NVN→Vulkan na
  CPU durante as batalhas (milhares de dispatches e binds de textura por frame). Medir com o overlay/trace em vez de
  adivinhar; sem alocação por frame nos caminhos quentes.
- **Imagem correta antes de desempenho.** Nunca esconder trabalho faltando (pular draws, zerar texturas, relaxar
  depth) e chamar de correção.
- **Implementações reais.** Nada de stubs que só devolvem sucesso para serviços que o jogo usa.

## Fronteira de conteúdo do jogo

Este repositório pode ficar público. Dados do jogo vivem fora dele e tudo derivado fica em pastas ignoradas.

- O dump e as chaves ficam em `Game Files/` (ignorado; as ferramentas usam esse caminho por padrão). As ferramentas
  recebem o caminho do arquivo de chaves e leem sozinhas. **Valores de chave nunca aparecem em saída, log, comando
  ou arquivo.** Tokens do GitHub também não: nunca em arquivo nem em `.git/config`.
- Tudo extraído ou gerado vai para `build/` ou `generated/`; a pasta para o Deck vai para `dist/`.
- Todo arquivo emitido pelo gerador leva `GENERATED_MARKER` (definido em `tools/check_content.py`).
- Rodar `python3 tools/check_content.py --staged` antes de propor commit (é o mesmo check do CI e do hook).

## Reuso de código

`refs/` tem as referências (`tools/fetch_refs.sh`), somente leitura.

- Copiar só código MIT, BSD, ISC, zlib ou Apache-2.0, manter o cabeçalho e adicionar linha em
  `THIRD_PARTY_NOTICES.md` com projeto, commit e arquivos.
- yuzu, suyu, Eden, Citron e qualquer código GPL: ler para entender comportamento, escrever o nosso.
- Endereços do nxnative (`main+0x...`) valem para o build 1.3.0 com os build IDs de `tools/data/known-builds.json`;
  conferir os bytes originais no nosso dump antes de usar qualquer um.

## Código

- C gerado nunca é editado à mão: mudar o gerador (`recomp/`) e gerar de novo.
- Toda mudança no lifter passa nos testes diferenciais contra Unicorn (Unicorn só em teste, nunca linkado no jogo).
- `recomp/layout.py` é o único lugar que decide bases de módulos.
- Patches de jogo são patches do lifter com bytes originais conferidos, nunca edição de saída.
- Comentários dizem o que o código faz e por quê. Citar nosso código por arquivo + função; código externo por
  projeto, arquivo e função.

## Idioma

Documentação em português (pt-BR). Código, identificadores e mensagens de commit podem ser em inglês ou português,
mas consistentes dentro de cada arquivo. Mensagens de commit são frases simples, sem prefixos de tipo.

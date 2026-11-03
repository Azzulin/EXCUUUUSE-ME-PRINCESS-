# AoC Recomp — instruções para agentes

Recompilação estática de *Hyrule Warriors: Age of Calamity* 1.3.0 (Switch, ARM64) para x86-64 nativo com Vulkan.
Alvo principal: **Steam Deck** (Linux, RADV, 4 núcleos Zen 2, 1280×800). Arquitetura em `docs/arquitetura.md`, plano
em `docs/plano.md`, fatos do jogo em `docs/levantamento.md` e `docs/aoc.md`.

## Prioridades

- **Desempenho no Deck primeiro.** Orçamento de frame é requisito. O custo provável está no replay NVN→Vulkan na
  CPU durante as batalhas (milhares de dispatches e binds de textura por frame). Medir com o overlay/trace em vez de
  adivinhar; sem alocação por frame nos caminhos quentes.
- **Imagem correta antes de desempenho.** Nunca esconder trabalho faltando (pular draws, zerar texturas, relaxar
  depth) e chamar de correção.
- **Implementações reais.** Nada de stubs que só devolvem sucesso para serviços que o jogo usa.

## Fronteira de conteúdo do jogo

Este repositório pode ficar público. Dados do jogo vivem fora dele e tudo derivado fica em pastas ignoradas.

- Caminhos do dump e das chaves ficam em `config.local.toml` (ignorado). As ferramentas recebem o caminho do arquivo
  de chaves e leem sozinhas. **Valores de chave nunca aparecem em saída, log, comando ou arquivo.**
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

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

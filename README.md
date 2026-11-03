# AoC Recomp

Recompilação estática de *Hyrule Warriors: Age of Calamity* (Nintendo Switch, 2020, versão 1.3.0) para um programa
nativo x86-64 com renderização Vulkan, com foco no **Steam Deck** e, em segundo lugar, em PCs mid-end (Linux e
Windows).

> [!IMPORTANT]
> **Nenhum arquivo do jogo está incluído.** É preciso ter a sua própria cópia, obtida legalmente e extraída do seu
> próprio console: base, update 1.3.0 e, opcionalmente, os DLCs. Instruções de como obter esses arquivos não serão
> fornecidas. O jogo é montado a partir dos seus arquivos, na sua máquina — o resultado contém o jogo e é só para uso
> próprio.

## Status

**Fase 0 — fundação e inventário.** Ainda não roda nada do jogo. O que existe:

- levantamento técnico completo e plano por fases ([docs/](docs/));
- guarda de conteúdo (hook + CI) que impede dados do jogo e chaves de entrarem no git;
- `tools/inspect_dump.py`, que confere o seu dump extraído (build IDs, NPDM, tamanhos do RomFS).

## Como funciona (resumo)

O código ARM64 do jogo é traduzido para C antes da execução e compilado com Clang; um runtime próprio faz o papel do
sistema do Switch (threads, serviços, arquivos, áudio) e reimplementa a API gráfica NVN sobre Vulkan. Não há emulação
de CPU nem JIT. A base é o pipeline do [Astral Chain Recomp](https://github.com/captainj-sparrow/astral-chain-pc-recomp)
/ [TotK Recomp](https://github.com/valentderah/totk-pc-recomp), e o conhecimento específico do jogo vem do perfil de
Age of Calamity do [nxnative](https://github.com/seedds/nxnative).

| Documento | Conteúdo |
|---|---|
| [docs/levantamento.md](docs/levantamento.md) | o jogo por dentro, projetos de referência, abordagens, hardware-alvo |
| [docs/arquitetura.md](docs/arquitetura.md) | arquitetura escolhida, camada por camada |
| [docs/plano.md](docs/plano.md) | fases, portões de aceitação, riscos |
| [docs/steam-deck.md](docs/steam-deck.md) | requisitos, disco (SD de 1 TB) e desempenho |
| [docs/referencias.md](docs/referencias.md) | repositórios de referência fixados e ordem de leitura |
| [docs/aoc.md](docs/aoc.md) | fatos medidos no nosso dump (preenchido a partir da Fase 0) |

## Primeiros passos (WSL2 / Ubuntu)

```sh
git config core.hooksPath .githooks        # ativa a guarda de conteúdo antes de cada commit
sh tools/fetch_refs.sh                     # baixa as referências em refs/ (ignorado pelo git)
cp config.example.toml config.local.toml   # aponte para o seu dump e as suas chaves
python3 -m unittest discover -s tests -v   # testes sem dados do jogo

# depois de extrair o ExeFS/RomFS para build/v130/ :
python3 tools/inspect_dump.py --exefs build/v130/exefs --romfs build/v130/romfs --out build/v130/inspect.json
```

## Licença

Código do projeto sob a [licença MIT](LICENSE); código de terceiros mantém a própria licença
([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). A licença não concede nada sobre o jogo.

Projeto de fã, independente e sem fins comerciais, sem afiliação com a Nintendo ou a Koei Tecmo. *Hyrule Warriors*,
*The Legend of Zelda* e *Nintendo Switch* são marcas dos seus respectivos donos.

# AoC Recomp

<a href="https://recomplauncher.com/game/excuuuuse-me-princess"><picture><source media="(prefers-color-scheme: dark)" srcset="https://recomplauncher.com/assets/press/launcher/badge-light.svg"><img alt="Get it on RecompLauncher" src="https://recomplauncher.com/assets/press/launcher/badge-dark.svg" height="48"></picture></a>

**[English](#english)** · **[Português](#português)**

## English

Static recompilation of *Hyrule Warriors: Age of Calamity* (Nintendo Switch, 2020, update 1.3.0) into a native x86-64
program with Vulkan rendering, for the **Steam Deck** first and mid-range PCs (Linux and Windows) second.

> [!IMPORTANT]
> **No game files are included.** You need your own copy, legally obtained and dumped from your own console: the base
> game, update 1.3.0 and, optionally, the DLCs. Instructions for getting those files will not be given. The game is
> built from your files, on your machine — the result contains the game and is for your own use only.

### How to play

1. Download the **launcher** package from the *Releases* page: `AoC-Recomp-<version>-Windows.zip` or
   `AoC-Recomp-<version>-Linux.tar.gz`.
2. Extract it to a folder with ~45 GB free and open `AoC-Launcher.exe` (Windows) or `./aoc-launcher` (Linux).
3. Pick the folder with your NSPs (base, update **1.3.0**, DLCs) and your `prod.keys`.
4. Tick where you will play (this PC, the Steam Deck, or both) and click **BUILD**. The first time takes 1 to 2 hours:
   the launcher sets up the free tools it needs (a compiler; on Windows also WSL for the Deck version) and compiles the
   game. Then press **PLAY**, or copy the Deck folder to the Steam Deck.

Requirements, the Linux and Steam Deck steps and troubleshooting: **[GUIDE.md](GUIDE.md)**.
Found a problem? In the launcher, **Report a problem…** makes `aoc-report.zip` (logs and PC details, nothing of the
game) and opens the form at <https://github.com/Azzulin/EXCUUUUSE-ME-PRINCESS-/issues>
([how to report](GUIDE.md#8-reporting-a-problem)).

## Português

Recompilação estática de *Hyrule Warriors: Age of Calamity* (Nintendo Switch, 2020, versão 1.3.0) para um programa
nativo x86-64 com renderização Vulkan, com foco no **Steam Deck** e, em segundo lugar, em PCs mid-end (Linux e
Windows).

> [!IMPORTANT]
> **Nenhum arquivo do jogo está incluído.** É preciso ter a sua própria cópia, obtida legalmente e extraída do seu
> próprio console: base, update 1.3.0 e, opcionalmente, os DLCs. Instruções de como obter esses arquivos não serão
> fornecidas. O jogo é montado a partir dos seus arquivos, na sua máquina — o resultado contém o jogo e é só para uso
> próprio.

### Para jogar

1. Baixe o pacote do **launcher** na página *Releases*: `AoC-Recomp-<versão>-Windows.zip` ou
   `AoC-Recomp-<versão>-Linux.tar.gz`.
2. Extraia numa pasta com ~45 GB livres e abra o `AoC-Launcher.exe` (Windows) ou o `./aoc-launcher` (Linux).
3. Escolha a pasta com os seus NSPs (base, update **1.3.0**, DLCs) e o seu `prod.keys`.
4. Marque onde vai jogar (este PC, o Steam Deck ou os dois) e clique em **GERAR**. A primeira vez leva de 1 a 2 horas:
   o launcher prepara sozinho as ferramentas gratuitas de que precisa (um compilador; no Windows também o WSL, para a
   versão do Deck) e compila o jogo. Depois é só apertar **JOGAR**, ou copiar a pasta do Deck para o Steam Deck.

Requisitos, o passo a passo do Linux e do Steam Deck e o que fazer quando algo dá errado: **[GUIA.md](GUIA.md)**.

### Status

- **Roda do começo à batalha** no Steam Deck (SteamOS, RADV) e no Windows (RTX 3050): 30 fps na primeira batalha do
  Deck, memória estável em sessões de 10 min ou mais, som, vídeos e menus. Detalhes e números em
  [docs/handover.md](docs/handover.md) e [docs/historico.md](docs/historico.md).
- **Em aberto:** saves ainda não verificados numa jogatina real, travadas de shader em conteúdo novo, o conteúdo
  dos DLCs jogado de ponta a ponta (eles já são montados e lidos), 60 fps opcional. Fases e portões em [docs/plano.md](docs/plano.md).

### Testou? Conte o que viu

Problemas e relatos em <https://github.com/Azzulin/EXCUUUUSE-ME-PRINCESS-/issues>. No launcher, **Reportar problema…**
cria o `aoc-report.zip` (registros e dados do PC, nada do jogo) e abre o formulário; no Steam Deck sem o launcher,
`./aoc-logs.sh pacote`. Passo a passo em [GUIA.md](GUIA.md#8-reportar-um-problema) /
[GUIDE.md](GUIDE.md#8-reporting-a-problem).

## Como funciona (resumo)

O código ARM64 do jogo é traduzido para C antes da execução e compilado com Clang; um runtime próprio faz o papel do
sistema do Switch (threads, serviços, arquivos, áudio) e reimplementa a API gráfica NVN sobre Vulkan. Não há emulação
de CPU nem JIT. A base é o pipeline do [Astral Chain Recomp](https://github.com/captainj-sparrow/astral-chain-pc-recomp)
/ [TotK Recomp](https://github.com/valentderah/totk-pc-recomp), e o conhecimento específico do jogo vem do perfil de
Age of Calamity do [nxnative](https://github.com/seedds/nxnative).

| Documento | Conteúdo |
|---|---|
| [docs/handover.md](docs/handover.md) | **estado atual e próximos passos** (para quem continua o trabalho, pessoa ou agente) |
| [docs/historico.md](docs/historico.md) | relato do que foi feito em cada sessão |
| [docs/levantamento.md](docs/levantamento.md) | o jogo por dentro, projetos de referência, abordagens, hardware-alvo |
| [docs/arquitetura.md](docs/arquitetura.md) | arquitetura escolhida, camada por camada |
| [docs/plano.md](docs/plano.md) | fases, portões de aceitação, riscos |
| [docs/steam-deck.md](docs/steam-deck.md) | requisitos, disco (SD de 1 TB) e desempenho |
| [docs/building.md](docs/building.md) | como extrair, gerar o C e compilar no WSL do PC; pasta única para o Deck |
| [docs/referencias.md](docs/referencias.md) | repositórios de referência fixados e ordem de leitura |
| [docs/aoc.md](docs/aoc.md) | fatos medidos no nosso dump (preenchido a partir da Fase 0) |

## Para desenvolver (compilar à mão)

Quem só quer jogar não precisa disto: o launcher acima faz tudo. Para trabalhar no código:

1. Clone o repositório: `git clone https://github.com/Azzulin/EXCUUUUSE-ME-PRINCESS-.git`.
2. Crie a pasta `Game Files` na raiz do clone e coloque nela os NSPs da **base**, do **update 1.3.0** e dos
   **DLCs**, e o seu **`prod.keys`**. Essa pasta é ignorada pelo git e nunca é enviada.
3. O mesmo caminho do launcher, sem janela: `python tools/make_build.py --deck --windows` (Windows, no MSYS2 UCRT64)
   ou `python3 tools/make_build.py --deck` (Linux). Ou, só a parte do Linux, **`build.bat`** (na raiz), que:
   - confere se o WSL abre (e diz o que fazer se não abrir);
   - prepara a distro do WSL (clang, lld, ninja, venv Python; pede a senha do `sudo` só na primeira vez);
   - extrai o código do jogo de `Game Files/` se ainda não foi extraído;
   - gera o C e compila em `~/aoc-build` (disco do Linux), com o log em `build\build-wsl.log`.

Requisitos: Windows 10/11 com WSL2 e uma distro Arch Linux ou Ubuntu (22.04 ou 24.04) funcionando — `wsl -l -v`
lista as distros. Detalhes e comandos manuais em [docs/building.md](docs/building.md).

Para o RomFS mesclado (só necessário a partir da Fase 2), rode também `tools\windows\merge_romfs.bat`, que usa o
`hactool.exe` em `toolchain\hactool-1.4.0-win\` (baixe o hactool 1.4.0 para lá; não vai no git).

## Licença

Código do projeto sob a [licença MIT](LICENSE); código de terceiros mantém a própria licença
([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). A licença não concede nada sobre o jogo.

Projeto de fã, independente e sem fins comerciais, sem afiliação com a Nintendo ou a Koei Tecmo. *Hyrule Warriors*,
*The Legend of Zelda* e *Nintendo Switch* são marcas dos seus respectivos donos.

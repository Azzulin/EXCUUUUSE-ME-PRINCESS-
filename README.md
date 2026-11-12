# AoC Recomp

Recompilação estática de *Hyrule Warriors: Age of Calamity* (Nintendo Switch, 2020, versão 1.3.0) para um programa
nativo x86-64 com renderização Vulkan, com foco no **Steam Deck** e, em segundo lugar, em PCs mid-end (Linux e
Windows).

> [!IMPORTANT]
> **Nenhum arquivo do jogo está incluído.** É preciso ter a sua própria cópia, obtida legalmente e extraída do seu
> próprio console: base, update 1.3.0 e, opcionalmente, os DLCs. Instruções de como obter esses arquivos não serão
> fornecidas. O jogo é montado a partir dos seus arquivos, na sua máquina — o resultado contém o jogo e é só para uso
> próprio.

## Para jogar

Baixe o pacote do **launcher** na página *Releases* (Windows `.zip` ou Linux `.tar.gz`), extraia, abra o
`AoC-Launcher.exe` (ou `./aoc-launcher`), aponte a pasta com a sua cópia e clique em **FORJAR**. Ele prepara
sozinho as ferramentas (Linux do WSL, compilador) e compila o jogo para o Steam Deck / Linux e para o Windows.
Passo a passo: **[GUIA.md](GUIA.md)** (português) · **[GUIDE.md](GUIDE.md)** (English).

## Status

- **Roda do começo à batalha** no Steam Deck (SteamOS, RADV) e no Windows (RTX 3050): 30 fps na primeira batalha do
  Deck, memória estável em sessões de 10 min ou mais, som, vídeos e menus. Detalhes e números em
  [docs/handover.md](docs/handover.md) e [docs/historico.md](docs/historico.md).
- **Em aberto:** saves ainda não verificados numa jogatina real, travadas de shader em conteúdo novo, DLCs,
  60 fps opcional. Fases e portões em [docs/plano.md](docs/plano.md).

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

## Compilar em qualquer máquina (Windows + WSL)

1. Clone o repositório:
   `git clone https://github.com/Azzulin/Blonde-Z-and-her-friends.git` (repositório privado: use o seu token).
2. Crie a pasta `Game Files` na raiz do clone e coloque nela os NSPs da **base**, do **update 1.3.0** e dos
   **DLCs**, e o seu **`prod.keys`**. Essa pasta é ignorada pelo git e nunca é enviada.
3. Dê dois cliques em **`build.bat`** (na raiz). Ele:
   - confere se o WSL abre (e diz o que fazer se não abrir);
   - prepara o Ubuntu do WSL (clang, lld, ninja, venv Python; pede a senha do `sudo` só na primeira vez);
   - extrai o código do jogo de `Game Files/` se ainda não foi extraído;
   - gera o C e compila em `~/aoc-build` (disco do Linux), com o log em `build\build-wsl.log`.

Requisitos: Windows 10/11 com WSL2 e uma distro Ubuntu (22.04 ou 24.04) funcionando — `wsl -l -v` lista as
distros; `wsl --install -d Ubuntu-24.04` instala uma. Detalhes e comandos manuais em
[docs/building.md](docs/building.md).

Para o RomFS mesclado (só necessário a partir da Fase 2), rode também `tools\windows\merge_romfs.bat`, que usa o
`hactool.exe` em `toolchain\hactool-1.4.0-win\` (baixe o hactool 1.4.0 para lá; não vai no git).

## Licença

Código do projeto sob a [licença MIT](LICENSE); código de terceiros mantém a própria licença
([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). A licença não concede nada sobre o jogo.

Projeto de fã, independente e sem fins comerciais, sem afiliação com a Nintendo ou a Koei Tecmo. *Hyrule Warriors*,
*The Legend of Zelda* e *Nintendo Switch* são marcas dos seus respectivos donos.

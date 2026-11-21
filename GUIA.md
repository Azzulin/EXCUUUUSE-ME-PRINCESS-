# AoC Recomp — guia do jogador

*(English version: [GUIDE.md](GUIDE.md).)*

O AoC Recomp transforma **a sua própria cópia** de *Hyrule Warriors: Age of Calamity* (Nintendo Switch, update 1.3.0)
numa versão nativa para **Steam Deck**, **Linux** e **Windows**. O launcher faz tudo no seu PC: lê os seus arquivos,
prepara as ferramentas de que precisa e compila o jogo. Nada do jogo vem neste download, e nada do que você gerar deve
ser compartilhado.

**Resumo:** baixe o launcher → extraia numa pasta com espaço → abra → escolha a pasta com os NSPs e o `prod.keys` →
**GERAR** → espere de 1 a 2 horas → **JOGAR**. O resto desta página é o detalhe e o que fazer quando algo dá errado.

---

## 1. O que você precisa

| | |
|---|---|
| **Os arquivos do seu jogo**, numa pasta | o NSP do jogo base (`01002B00111A2000`), o NSP do **update 1.3.0** (`01002B00111A2800`), os NSPs das DLCs (opcional) e o **`prod.keys`** do seu console, tudo extraído do **seu** Switch. O update tem de ser o **1.3.0** (v327680): o 1.4.1 ainda não é aceito. Os arquivos podem ter qualquer nome: o gerador os reconhece pelo conteúdo |
| **Um PC para gerar** | Windows 10 (versão 2004 ou mais nova) ou Windows 11, ou um Linux 64 bits com `python3` (quase toda distribuição tem); **8 GB de RAM** (16 GB é melhor) |
| **Espaço livre** | cerca de **45 GB** na primeira vez (cai para ~25 GB quando termina), num disco **NTFS** no Windows (não FAT32 nem exFAT: os dados do jogo são um arquivo só de 10,9 GiB). Num SSD a compilação fica bem mais rápida |
| **Internet** | só na primeira vez: o launcher baixa ~2 GB de ferramentas gratuitas (compilador, Linux para Windows) |
| **Para jogar no PC** | processador com **AVX2**: Intel Core de 4ª geração (2013) ou mais novo, AMD Ryzen ou mais novo (Pentium e Celeron antigos e AMD FX não têm). Placa de vídeo com **Vulkan 1.3** e driver atualizado: NVIDIA GeForce GTX 900 ou mais nova, AMD Radeon RX 400 ou mais nova. Vídeo Intel ainda não foi testado |
| **Para jogar no Steam Deck** | só o Deck: qualquer PC acima gera a pasta do Deck, mesmo um cujo processador ou placa de vídeo não rode o jogo |

### Antes de começar: quatro conferências que evitam a maioria das falhas

1. **O update é o 1.3.0?** No nome do NSP, `v327680` é o 1.3.0; `v458752` é o 1.4.1, que ainda não funciona. Na
   dúvida, o gerador lê cada arquivo antes de compilar qualquer coisa e para com uma mensagem clara se o update for de
   outra versão (no Windows, **Só conferir** faz só isso, em segundos).
2. **O `prod.keys` está na mesma pasta dos NSPs?** Ele tem de vir do mesmo console de onde o jogo foi extraído.
3. **Onde vai ficar a pasta `AoC-Recomp`?** Num disco com ~45 GB livres, numa pasta simples como `C:\Jogos` ou
   `D:\Jogos`. Evite Área de Trabalho, Documentos e Downloads quando o **OneDrive** os sincroniza (ele tentaria enviar
   25 GB) e evite `C:\Arquivos de Programas` (sem permissão de escrita).
4. **Antivírus.** O launcher roda um compilador que grava milhares de arquivos; alguns antivírus o deixam muito lento
   ou põem ferramentas em quarentena (`hactool.exe`, `aoc_xlate.exe`). Se acontecer, coloque a pasta `AoC-Recomp` (e
   no Windows `%LOCALAPPDATA%\AoC-Recomp`) nas exceções do antivírus.

---

## 2. Windows, passo a passo

1. **Baixe** o `AoC-Recomp-<versão>-Windows.zip` na página *Releases* do projeto.
2. **Extraia**: clique com o botão direito no zip → *Extrair tudo…* → escolha uma pasta com espaço, por exemplo
   `C:\Jogos`. Aparece uma pasta `AoC-Recomp`. Não abra o launcher de dentro do zip: extraia antes. Se o Explorador
   do Windows travar no zip (acontece em alguns PCs enquanto o antivírus o examina), extraia com o
   [7-Zip](https://www.7-zip.org/) ou o WinRAR.
3. Abra o **`AoC-Launcher.exe`** dentro dela. O Windows pode dizer que "protegeu o computador" (o programa não é
   assinado): clique em *Mais informações* → *Executar assim mesmo*.
4. **SUA CÓPIA** — clique em **Procurar…** e escolha a pasta com os NSPs e o `prod.keys`.
   Quatro pontos verdes: tudo encontrado.
5. **ONDE VAI JOGAR** — marque **Steam Deck / Linux**, **Windows (este PC)** ou os dois.
6. Clique em **GERAR** (embaixo, à direita; até a versão 0.1.5 o botão se chamava **FORJAR**) e deixe o PC trabalhar. A
   primeira vez leva **de 1 a 2 horas**; a lista à direita mostra cada passo e quanto tempo levou. Dá para usar o PC
   enquanto isso, só fica mais lento. Não deixe o PC entrar em suspensão enquanto ele trabalha.
7. Quando terminar:
   - **Windows:** a janela vira o launcher do jogo (abaixo). Aperte **JOGAR**.
   - **Steam Deck:** copie a pasta para o Deck (seção 4); **Pasta do Deck**, embaixo, abre a pasta.

**O launcher do jogo.** Depois que o jogo deste PC foi gerado, o `AoC-Launcher.exe` já abre nele:

| | |
|---|---|
| **GRÁFICOS** | modo e tamanho da janela, apresentação (VSync), resolução do jogo (1920 × 1080 ou a mais leve 1280 × 720), resolução interna (TV ou portátil), escala 3D, formato da imagem, filtragem de texturas, sombras, indicador de desempenho |
| **CONTROLE E SOM** | layout dos botões (Nintendo ou Xbox), vibração, zona morta dos analógicos, inverter a câmera, volume, mudo em segundo plano, idioma do menu do jogo |
| Barra de baixo | **Reportar problema…** (um zip com os registros e os dados do PC, para pedir ajuda), **Pasta do jogo**, **Gerar de novo** (depois de uma atualização, ou para fazer também a versão do Steam Deck), **Salvar**, **Fechar** e **JOGAR** |

Pare o mouse sobre uma opção para ver uma explicação curta. **JOGAR** salva antes. O resto (remapear botões, cores,
HDR) fica no menu do próprio jogo: **F1**, ou Menos + Mais no controle.

> **"O WSL não está instalado"?** A versão do Steam Deck é compilada dentro do WSL (o Linux que vem com o Windows).
> Clique em **Instalar o WSL**, aceite a pergunta de administrador, **reinicie o PC**, abra o launcher de novo e
> clique em **GERAR** outra vez. Ele continua de onde parou. Se o WSL ainda falhar, ligue a *virtualização*
> (Intel VT-x / AMD SVM) na BIOS do PC. Se você só vai jogar neste PC, desmarque **Steam Deck / Linux**: a versão
> Windows não precisa do WSL.

A troca de idioma (**PT / EN**) fica no canto de cima; **Guia** abre esta página.

---

## 3. Linux, passo a passo

Você precisa de um Linux 64 bits com `python3` (quase toda distribuição tem) e de internet na primeira vez. Tudo é
feito pelo launcher; os comandos abaixo são só para abri-lo.

1. **Baixe** o `AoC-Recomp-<versão>-Linux.tar.gz` na página *Releases*.
2. **Extraia e abra o launcher.** Num terminal, na pasta onde está o download (em geral `~/Downloads`):
   ```sh
   tar xf AoC-Recomp-*-Linux.tar.gz
   cd AoC-Recomp
   ./aoc-launcher
   ```
   Das próximas vezes, basta `./aoc-launcher` dentro de `AoC-Recomp` (alguns gerenciadores de arquivos também o abrem
   com dois cliques). Se faltar no seu sistema alguma biblioteca de que a janela do launcher precisa (`libdecor`,
   `libXss`, `libpulse`…), ele usa uma cópia que traz consigo, só do que falta: nada para instalar.
3. **SUA CÓPIA** — **Procurar…** e escolha a pasta com os NSPs e o `prod.keys`. Deixe **Steam Deck / Linux**
   marcado: a mesma pasta é o jogo deste PC e do Deck.
4. Clique em **GERAR**. Na primeira vez o launcher instala o compilador, e como depende do sistema:

   | Sistema | O que acontece |
   |---|---|
   | Ubuntu, Kubuntu, Mint, Pop!_OS, Debian | o sistema pede a sua **senha** numa janela e os pacotes vêm do `apt`. **Testado: Ubuntu 24.04** |
   | Arch, Manjaro, EndeavourOS, CachyOS | o mesmo, com o `pacman`. **Testado: Arch** |
   | Fedora Workstation | o mesmo, com o `dnf`. Ainda não testado: se falhar, o registro diz qual pacote faltou |
   | **SteamOS** (Steam Deck, Steam Machine), **Bazzite**, Fedora Silverblue/Kinoite, NixOS | o sistema não aceita pacotes, então o gerador cria um **contêiner do distrobox** (`aoc-recomp`, ~1,5 GB) e compila dentro dele, sem alterar o sistema. O SteamOS 3.5+ e o Bazzite já trazem o `distrobox`. **Novo e ainda não confirmado por jogadores**: se falhar, reporte (seção 8) e gere em outro PC enquanto isso |

   A janela de senha não apareceu? Ambientes sem o ajudante de senha (i3, sway e outros gerenciadores de janela
   simples) não conseguem mostrá-la. Rode isto uma vez num terminal, dentro de `AoC-Recomp`, e clique em **GERAR** de
   novo:
   ```sh
   bash tools/setup_wsl.sh --minimal
   ```
5. Deixe trabalhar: **de 1 a 2 horas** na primeira vez (a lista à direita mostra cada passo). Se você fechar ou algo
   falhar, ele continua de onde parou.
6. No fim a janela vira o launcher do jogo, como no Windows: configurações e **JOGAR**. O jogo fica em
   `AoC-Recomp/dist/aoc-deck`; o `./aoc.sh` de lá também o abre, e `sh instalar-atalho.sh` o põe no menu de
   aplicativos (e assim na lista *Adicionar um jogo que não é da Steam*). Os dados do jogo (`romfs.bin`) entram nessa
   pasta como hardlink, que não ocupa espaço a mais. Para jogar num Steam Deck, veja a seção 4.

**Sem a janela** (por SSH, ou se o launcher não abrir): a mesma geração por um terminal, dentro de `AoC-Recomp`:
```sh
python3 tools/make_build.py --deck --lang pt --game-dir ~/caminho/dos/arquivos/do/jogo
```
Depois, `dist/aoc-deck/aoc.sh` abre o jogo.

---

## 4. Copiar para o Steam Deck

O Deck não compila nada: ele recebe a pasta pronta `AoC-Recomp/dist/aoc-deck`. (Se você gerou no próprio Deck, a
pasta já está lá: pule para o passo 3.)

1. **Na primeira vez**, no Windows, marque **incluir o romfs.bin** antes de gerar (os dados do jogo, 10,9 GiB, vão
   para a pasta; no Linux eles sempre vão). Nas atualizações pode deixar desmarcado: os dados não mudam. Os DLCs que
   estiverem na sua pasta de arquivos vão sempre (`romfs/dlc-*.bin`, 1,4 GiB os quatro); copie-os uma vez junto com o
   `romfs.bin`.
2. Copie a pasta `aoc-deck` inteira para o Deck — pendrive, cartão SD, pasta de rede ou `scp` — por exemplo para o
   cartão SD: `/run/media/mmcblk0p1/aoc-deck`. Um pendrive tem de estar formatado em **exFAT** ou NTFS: o FAT32 não
   guarda o `romfs.bin` de 10,9 GiB.
3. No Deck, em **Modo Desktop**, abra a pasta, abra um terminal ali (*Konsole*) e rode uma vez:
   ```sh
   sh instalar-atalho.sh
   ```
4. Na Steam: *Jogos* → *Adicionar um jogo que não é da Steam* → marque
   **Hyrule Warriors: Age of Calamity (AoC Recomp)** → *Adicionar*. No **Modo de Jogo** ele fica na biblioteca.

O `LEIA-ME.txt` da pasta (`README.txt` em inglês) tem os controles (segure **L3+R3** para o menu rápido) e as
ferramentas de registro.

---

## 5. Atualizar para uma versão nova

Extraia o zip novo **por cima da pasta `AoC-Recomp` antiga** (substituindo os arquivos) e gere de novo. As pastas
`build` e `dist` ficam, então ele só refaz o que mudou — em geral minutos. Saves e configurações em
`dist/*/profile` e `dist/*/aoc.ini` nunca são sobrescritos. No Deck, copie de novo só o arquivo `aoc` e a pasta `lib`.

---

## 6. Onde as coisas ficam, e como remover

| O quê | Onde | Tamanho |
|---|---|---|
| O launcher, os dados que ele extraiu e as pastas prontas | a pasta `AoC-Recomp` (`build/`, `dist/`) | ~25 GB |
| O Linux do Windows (só para a versão do Steam Deck) | distro do WSL **AoC-Recomp**, em `%LOCALAPPDATA%\AoC-Recomp\wsl` | ~6 GB |
| O compilador do Windows (só para a versão Windows) | `C:\msys64` (MSYS2), se você ainda não tinha | ~3 GB |
| Linux: pasta de compilação e pacotes Python | `~/aoc-build`, `~/.venvs/aoc` | ~6 GB |
| SteamOS, Bazzite e parecidos: o contêiner do compilador | contêiner do distrobox `aoc-recomp` | ~1,5 GB |

Para remover tudo: apague a pasta `AoC-Recomp`; no Windows rode `wsl --unregister AoC-Recomp` num terminal e apague o
`C:\msys64` se foi o launcher que o instalou; no Linux apague `~/aoc-build` e `~/.venvs/aoc` e, onde houver
contêiner, rode `distrobox rm aoc-recomp`.

---

## 7. Se algo der errado

**Antes de gerar**

- **Ponto vermelho em "Seus arquivos"**: o arquivo não está na pasta escolhida. O `prod.keys` precisa estar na mesma
  pasta dos NSPs. Os NSPs podem ter qualquer nome: sem o ID no nome o launcher mostra "conferido ao gerar" e o
  primeiro passo da geração os identifica pelo conteúdo.
- **"O update da sua pasta é de outra versão"** ou **"o código do jogo extraído não é o da versão 1.3.0"**: o port só
  funciona com o update **1.3.0** (v327680). O update 1.4.1 (v458752) ainda não é aceito. Troque o NSP do update pelo
  da 1.3.0 e clique em **GERAR** de novo; o que sobrou da tentativa anterior é refeito sozinho.
- **"Pouco espaço livre"**: a mensagem diz quanto é preciso; libere espaço e gere de novo.
- **"O processador deste PC não tem AVX2"**: o jogo não roda neste PC (seção 1). Dá para gerar a versão do Steam Deck
  aqui mesmo e copiá-la para o Deck.
- **O zip não abre, ou o Explorador trava nele**: extraia com o 7-Zip ou o WinRAR (seção 2).

**Durante a geração**

- **Um passo falhou**: o motivo aparece em vermelho embaixo do passo, e o registro completo logo abaixo. Clique em
  **GERAR** de novo: os passos prontos são pulados. **Só conferir** testa o dump sem compilar. Para pedir ajuda,
  aperte **Reportar problema…** e anexe o `aoc-report.zip` (registros e dados do PC, nada do jogo).
- **"Unable to create temp file: No such file or directory"** em **Compilar para o Windows** (versão 0.1.5): falta a
  pasta temporária do MSYS2. Crie a pasta `C:\msys64\tmp` e gere de novo. A partir da versão 0.1.6 o gerador a cria
  sozinha.
- **SteamOS ou Bazzite: "unable to lock database", "rpm-ostree" ou "não deixa instalar as ferramentas"**: até a
  versão 0.1.5 o gerador não instala o compilador nesses sistemas. A partir da 0.1.6 ele usa um contêiner do distrobox
  (seção 3); até lá, gere num PC com Windows ou Linux e copie a pasta (seção 4).
- **A compilação está muito lenta**: um antivírus examinando cada arquivo atrasa muito o compilador (veja "Antes de
  começar"); um disco rígido (HD) no lugar de um SSD também. Com 8 GB de RAM os arquivos maiores demoram: feche o
  navegador e jogos enquanto ele trabalha.

**Jogando**

- **O JOGAR vira JOGANDO e volta, e o jogo não aparece**: o jogo parou ao abrir. A partir da versão 0.1.6 o launcher
  avisa embaixo dos botões, com o motivo quando o registro tem um. As causas comuns: processador sem AVX2, placa de
  vídeo ou driver sem Vulkan 1.3 (atualize o driver pelo site da NVIDIA, AMD ou Intel) ou, no Linux com a versão
  0.1.5, o `romfs.bin` faltando na pasta do jogo (gere de novo com **incluir o romfs.bin** marcado). Aperte
  **Reportar problema…** e mande o zip: o registro diz qual.
- **Travadinhas na primeira vez que joga**: os shaders são traduzidos enquanto você joga pela primeira vez e ficam
  guardados para as próximas sessões.
- **O jogo travou, a tela ficou preta ou escura, ou um efeito sumiu**: o jogo grava sozinho um relatório no registro
  quando para de mostrar imagem por 10 s ou fica preto/escuro por 15 s; aperte **F8** no momento de qualquer outro
  defeito para marcá-lo. Para investigar golpes e efeitos, abra o jogo pelo `monitor.bat` da pasta do jogo (no
  Windows) em vez do **JOGAR**: ele guarda imagens de cada golpe e um retrato completo do frame na marca ou na cena
  escura (fica um pouco mais lento e ocupa espaço em `logs\diag`). Depois aperte **Reportar problema…** e mande o zip.
- **Quedas de fps ou engasgadas**: toda sessão grava uma linha de desempenho por segundo em `logs/desempenho/`. No
  momento em que engasgar, segure **L3+R3** e escolha **Marcar este momento** (no PC também vale F8). No Steam Deck,
  `./aoc-logs.sh desempenho` resume a sessão e `./aoc-logs.sh pacote` junta tudo para mandar; no PC, **Reportar problema…**.

---

## 8. Reportar um problema

Quanto mais gente testar e contar o que viu, mais rápido o port melhora. Para reportar:

1. No launcher, aperte **Reportar problema…**. Ele cria o `aoc-report.zip` (registros e dados do PC; nada do jogo, e
   o seu nome de usuário é trocado por `user` nos textos), abre a pasta onde o zip ficou e abre no navegador o
   formulário de problemas do projeto: <https://github.com/Azzulin/EXCUUUUSE-ME-PRINCESS-/issues>.
2. Preencha o formulário (precisa de uma conta do GitHub) e arraste o `aoc-report.zip` para o campo do relatório. Uma
   captura de tela sozinha raramente diz por que algo falhou; o zip diz.
3. No Steam Deck sem o launcher: na pasta do jogo, `./aoc-logs.sh pacote` cria `logs/pacote-<data>.tar.gz`; anexe
   esse arquivo no mesmo formulário.

Antes de abrir um problema novo, veja se alguém já relatou o mesmo na lista. **Nunca anexe arquivos do jogo,
`prod.keys` ou saves.**

---

## 9. Perguntas comuns

- **Posso apagar os NSPs depois de gerar?** Por enquanto, guarde-os: gerar de novo (depois de uma atualização do
  AoC Recomp) ainda os confere. O que já foi extraído deles não é extraído de novo, então é rápido.
- **Funciona com o update 1.4.1?** Ainda não. É o pedido mais comum e está acompanhado na página de problemas.
- **Posso gerar num PC e jogar em outro?** Sim: a pasta do Deck (`dist/aoc-deck`) roda em qualquer PC com Linux e no
  Steam Deck. A pasta do Windows (`dist/aoc-windows`) pode ser copiada para outro PC com Windows, processador com AVX2
  e placa de vídeo com Vulkan 1.3.
- **Posso compartilhar a pasta gerada?** Não. Ela contém o jogo, feito a partir da sua cópia: é só para uso próprio.

## Aviso legal

Use somente uma cópia sua, extraída do seu próprio console. Este projeto não contém código, dados nem chaves do jogo e
não tem relação com a Nintendo nem com a Koei Tecmo. O código próprio do projeto está sob a [licença MIT](LICENSE); os
componentes que ele usa estão em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

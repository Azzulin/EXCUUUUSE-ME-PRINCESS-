# AoC Recomp — guia do jogador

*(English version: [GUIDE.md](GUIDE.md).)*

O AoC Recomp transforma **a sua própria cópia** de *Hyrule Warriors: Age of Calamity* (Nintendo Switch, update 1.3.0)
numa versão nativa para **Steam Deck**, **Linux** e **Windows**. O launcher faz tudo no seu PC: lê os seus arquivos,
prepara as ferramentas de que precisa e compila o jogo. Nada do jogo vem neste download, e nada do que você gerar deve
ser compartilhado.

---

## 1. O que você precisa

| | |
|---|---|
| **Os arquivos do seu jogo**, numa pasta | o NSP do jogo base (`01002B00111A2000`), o NSP do **update 1.3.0** (`01002B00111A2800`), os NSPs das DLCs (opcional) e o **`prod.keys`** do seu console, tudo extraído do **seu** Switch |
| **Um PC** | Windows 10 (versão 2004 ou mais nova) ou Windows 11, ou um Linux 64 bits com `python3` (quase toda distribuição tem); **8 GB de RAM** (16 GB é melhor) |
| **Espaço livre** | cerca de **45 GB** na primeira vez (cai para ~25 GB quando termina) |
| **Internet** | só na primeira vez: o launcher baixa ~2 GB de ferramentas gratuitas (compilador, Linux para Windows) |
| **Para jogar no PC** | placa de vídeo com Vulkan (qualquer NVIDIA, AMD ou Intel recente) |

---

## 2. Windows, passo a passo

1. **Baixe** o `AoC-Recomp-<versão>-Windows.zip` na página *Releases* do projeto.
2. **Extraia**: clique com o botão direito no zip → *Extrair tudo…* → escolha uma pasta com espaço, por exemplo
   `C:\Jogos`. Aparece uma pasta `AoC-Recomp`.
3. Abra o **`AoC-Launcher.exe`** dentro dela. O Windows pode dizer que "protegeu o computador" (o programa não é
   assinado): clique em *Mais informações* → *Executar assim mesmo*.
4. **SUA CÓPIA** — clique em **Procurar…** e escolha a pasta com os NSPs e o `prod.keys`.
   Quatro pontos verdes: tudo encontrado.
5. **ONDE VAI JOGAR** — marque **Steam Deck / Linux**, **Windows (este PC)** ou os dois.
6. Clique em **FORJAR** (embaixo, à direita) e deixe o PC trabalhar. A primeira vez leva **de 1 a 2 horas**; a lista
   à direita mostra cada passo e quanto tempo levou. Dá para usar o PC enquanto isso, só fica mais lento.
7. Quando terminar:
   - **Windows:** a janela vira o launcher do jogo (abaixo). Aperte **JOGAR**.
   - **Steam Deck:** copie a pasta para o Deck (seção 4); **Pasta do Deck**, embaixo, abre a pasta.

**O launcher do jogo.** Depois que o jogo deste PC foi forjado, o `AoC-Launcher.exe` já abre nele:

| | |
|---|---|
| **GRÁFICOS** | modo e tamanho da janela, apresentação (VSync), resolução do jogo (1920 × 1080 ou a mais leve 1280 × 720), resolução interna (TV ou portátil), escala 3D, formato da imagem, filtragem de texturas, sombras, indicador de desempenho |
| **CONTROLE E SOM** | layout dos botões (Nintendo ou Xbox), vibração, zona morta dos analógicos, inverter a câmera, volume, mudo em segundo plano, idioma do menu do jogo |
| Barra de baixo | **Relatório…** (um zip com os registros e os dados do PC, para pedir ajuda), **Pasta do jogo**, **Forjar de novo** (depois de uma atualização, ou para fazer também a versão do Steam Deck), **Salvar**, **Fechar** e **JOGAR** |

Pare o mouse sobre uma opção para ver uma explicação curta. **JOGAR** salva antes. O resto (remapear botões, cores,
HDR) fica no menu do próprio jogo: **F1**, ou Menos + Mais no controle.

> **"O WSL não está instalado"?** A versão do Steam Deck é compilada dentro do WSL (o Linux que vem com o Windows).
> Clique em **Instalar o WSL**, aceite a pergunta de administrador, **reinicie o PC**, abra o launcher de novo e
> clique em **FORJAR** outra vez. Ele continua de onde parou. Se o WSL ainda falhar, ligue a *virtualização*
> (Intel VT-x / AMD SVM) na BIOS do PC.

A troca de idioma (**PT / EN**) fica no canto de cima; **Guia** abre esta página.

---

## 3. Linux, passo a passo

1. **Baixe** o `AoC-Recomp-<versão>-Linux.tar.gz` e extraia:
   ```sh
   tar xf AoC-Recomp-*-Linux.tar.gz
   cd AoC-Recomp
   ./aoc-launcher
   ```
2. Os mesmos passos do Windows (escolher a pasta, deixar **Steam Deck / Linux** marcado, **FORJAR**).
3. Na primeira vez o sistema pede a sua **senha**: o launcher instala o compilador pelo gerenciador de pacotes
   (`pacman`, `apt` ou `dnf`). Testado no Arch Linux; Ubuntu/Debian e Fedora estão no script de preparação mas ainda
   não foram testados — se falhar, o registro diz qual pacote faltou.
4. No fim a janela vira o launcher do jogo, como no Windows: configurações e **JOGAR** (ou rode
   `dist/aoc-deck/aoc.sh`). A mesma pasta serve para o Steam Deck.

---

## 4. Copiar para o Steam Deck

O Deck não compila nada: ele recebe a pasta pronta `AoC-Recomp/dist/aoc-deck`.

1. **Na primeira vez**, marque **incluir o romfs.bin** antes de forjar (os dados do jogo, 10,9 GiB, vão para a pasta).
   Nas atualizações pode deixar desmarcado: os dados não mudam.
2. Copie a pasta `aoc-deck` inteira para o Deck — pendrive, cartão SD, pasta de rede ou `scp` — por exemplo para o
   cartão SD: `/run/media/mmcblk0p1/aoc-deck`.
3. No Deck, em **Modo Desktop**, abra a pasta, abra um terminal ali (*Konsole*) e rode uma vez:
   ```sh
   sh instalar-atalho.sh
   ```
4. Na Steam: *Jogos* → *Adicionar um jogo que não é da Steam* → marque
   **Hyrule Warriors: Age of Calamity (AoC Recomp)** → *Adicionar*. No **Modo de Jogo** ele fica na biblioteca.

O `LEIA-ME.txt` da pasta tem os controles (segure **L3+R3** para o menu rápido) e as ferramentas de registro.

---

## 5. Atualizar para uma versão nova

Extraia o zip novo **por cima da pasta `AoC-Recomp` antiga** (substituindo os arquivos) e forje de novo. As pastas
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

Para remover tudo: apague a pasta `AoC-Recomp`; no Windows rode `wsl --unregister AoC-Recomp` num terminal e apague o
`C:\msys64` se foi o launcher que o instalou; no Linux apague `~/aoc-build` e `~/.venvs/aoc`.

---

## 7. Se algo der errado

- **Ponto vermelho em "Seus arquivos"**: o arquivo não está na pasta escolhida. Os nomes dos NSPs precisam ter os IDs
  mostrados, e o `prod.keys` precisa estar na mesma pasta.
- **"Pouco espaço livre"**: a mensagem diz quanto é preciso; libere espaço e forje de novo.
- **Um passo falhou**: o motivo aparece em vermelho embaixo do passo, e o registro completo logo abaixo. Clique em
  **FORJAR** de novo: os passos prontos são pulados. **Só conferir** testa o dump sem compilar. Para pedir ajuda,
  aperte **Relatório…** e anexe o `aoc-report.zip` (registros e dados do PC, nada do jogo).
- **A compilação está muito lenta**: um antivírus examinando cada arquivo atrasa muito o compilador; colocar a pasta
  `AoC-Recomp` (e no Windows `%LOCALAPPDATA%\AoC-Recomp`) nas exceções ajuda.
- **Travadinhas na primeira vez que joga**: os shaders são traduzidos enquanto você joga pela primeira vez e ficam
  guardados para as próximas sessões.
- **O jogo travou, a tela ficou preta ou escura, ou um efeito sumiu**: o jogo grava sozinho um relatório no registro
  quando para de mostrar imagem por 10 s ou fica preto/escuro por 15 s; aperte **F8** no momento de qualquer outro
  defeito para marcá-lo. Para investigar golpes e efeitos, abra o jogo pelo `monitor.bat` da pasta do jogo (no
  Windows) em vez do **JOGAR**: ele guarda imagens de cada golpe e um retrato completo do frame na marca ou na cena
  escura (fica um pouco mais lento e ocupa espaço em `logs\diag`). Depois aperte **Relatório…** e mande o zip.
- **Quedas de fps ou engasgadas**: toda sessão grava uma linha de desempenho por segundo em `logs/desempenho/`. No
  momento em que engasgar, segure **L3+R3** e escolha **Marcar este momento** (no PC também vale F8). No Steam Deck,
  `./aoc-logs.sh desempenho` resume a sessão e `./aoc-logs.sh pacote` junta tudo para mandar; no PC, **Relatório…**.

---

## Aviso legal

Use somente uma cópia sua, extraída do seu próprio console. Este projeto não contém código, dados nem chaves do jogo e
não tem relação com a Nintendo nem com a Koei Tecmo. O código próprio do projeto está sob a [licença MIT](LICENSE); os
componentes que ele usa estão em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

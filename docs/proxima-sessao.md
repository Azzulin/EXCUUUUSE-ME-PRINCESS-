# Próxima sessão — plano de ação e prompt

Atualizado em 2026-11-12 (fim da sessão 8: rastros descartados, cache de shaders estável, envio ao Deck pendente). Detalhes
em `docs/historico.md` (sessão 7), `docs/handover.md` §6 e `docs/aoc.md` ("Resolução de saída menor: vistas 2D e
minimapa", "Deck: consumo e temperatura na primeira batalha").

## Estado (2026-11-12, fim da sessão 11)

- **Vazamento de memória corrigido** e medido no Deck (10 min de batalha: memória plana, 30 fps, 5,1 W de média).
- **Ainda bloqueia uma jogatina longa:** saves nunca verificados em jogo real.
- No Deck: o binário atual (vazamento corrigido + 1280×720 corrigido, fora do perfil). Travadas de shader em
  conteúdo novo e o repouso do Deck seguem sem teste.

## Regras da rodada (pedido do dono)

Testes conclusivos, não sondagens: cada corrida de 3 min deve fechar uma pergunta (juntar na mesma corrida o que for
independente). Medir antes de declarar corrigido. Não mandar ao Deck nada que não rodou no notebook. Nunca rodar no
Deck com `totk` ou `aoc` abertos.

## Plano, em ordem

1. Vazamento de memória: feito (sessão 11).
2. **Saves:** jogar (ou um roteiro) até o primeiro salvamento automático; `fs commit save` no log; reabrir no
   ponto salvo.
3. Deck: enviar o binário (720p corrigido), apagar `shots7/` do cartão, medir 1280×720 (75 % e 85 %) e testar o
   repouso com o jogo aberto.
4. Travadas de shader em conteúdo novo: tradução antecipada ou prewarm.

## Prompt para colar numa sessão nova

```
Projeto: recompilação estática de Hyrule Warriors: Age of Calamity 1.3.0 (Switch) para x86-64 + Vulkan, alvo Steam Deck,
testado no notebook Windows (RTX 3050). Leia ANTES de tudo: AGENTS.md (regras: docs em pt-BR, C gerado nunca editado à
mão, dados do jogo fora do git, check_content antes de commit), docs/proxima-sessao.md e docs/handover.md, seção 6;
o relato mais recente é a sessão 7 de docs/historico.md.

Estado: o Deck tem tudo das sessões 5-7 medido (batalha 27-30 fps a ~8 W), menos a resolução 1280x720 (minimapa sem
marcadores). O dono quer o porte afinado ao Deck: sem rastros, sem travadas, consumo baixo. Registros do Deck:
ssh ... 'cd <pasta do jogo> && ./aoc-logs.sh lista' (resumo, ao-vivo, sistema, detalhado on|off, pacote). Testes conclusivos: cada corrida de 3 min fecha uma pergunta; nada vai ao Deck sem ter rodado no notebook.

Ambiente (Windows nativo, MSYS2 UCRT64):
- Build do runtime + link: no PowerShell,
  $env:MSYSTEM="UCRT64"; $env:CHERE_INVOKING="1"; & C:\msys64\usr\bin\bash.exe -lc "bash /c/aoc-win/host.sh"
  (log em C:\aoc-win\host.log; não rodar host.sh pelo Git Bash: falta o python3). Depois de regenerar o C no WSL:
  powershell -c "wsl -d archlinux -- bash /mnt/c/aoc-win/gensync.sh" (copia só os arquivos que mudaram para
  C:\aoc-win\generated), wsl --shutdown e python3 tools/build.py --work /c/aoc-win --big-jobs 2 guest host (no UCRT64).
- Medidas na imagem: python C:\aoc-win\centre.py <pasta> (bloco branco no centro); rastros:
  /c/msys64/ucrt64/bin/python3 C:\aoc-win\streaks.py <pasta> (só o Python do MSYS tem scipy). Captura do que a janela
  mostra: AOC_PRESENT_SHOT=<frame>:<arquivo> (AOC_SHOTS e --shot copiam a textura inteira do jogo, sem o recorte).
- Rota até a 1ª batalha (175 s): bash /c/aoc-win/diag1.sh [VAR=valor ...] (Git Bash; ROUTE, SECS, LOG mudam rota,
  duração e nome do log; padrão: AOC_TRACE=perf,audio,fs e capturas a cada 4 s em C:\aoc-win\dshots). A rota antiga
  battle.sh continua valendo. Rota com câmera girando: ROUTE=C:/aoc-win/route-cam.txt.
- Áudio: AOC_TRACE=audio dá nível a cada 5 s + censo de vozes e mixes. Hoje: 1 janela muda em 37 (só o boot).
- Dump de frame: AOC_DUMP=4400 AOC_DUMP_DIR=C:/aoc-win/dumpX AOC_DUMP_UBO=24 AOC_DUMP_SKIP_RUNS=1 AOC_VK_RECORDER=0
  (AOC_DUMP_UBO lista uniformes, atributos, índices e os vértices de cada draw). GLSL: spirv-cross --vulkan-semantics.
- Código do jogo: python C:\aoc-win\a64.py main <offset> [n] (desmonta; também u32, str, find);
  /c/msys64/ucrt64/bin/python3 C:\aoc-win\plt.py main '<regex de import>' (stubs e chamadores);
  python C:\aoc-win\dref.py main <endereço de dado>; python C:\aoc-win\immscan.py 1280x720 ... (constantes).
- WSL (Arch): regenerar o C: powershell -c "wsl -d archlinux -- bash /mnt/c/aoc-win/wsl_gen.sh" (100 s);
  guest + host: .../wsl_build.sh; pasta do Deck: .../dist.sh; envio: bash tools/deck/deploy.sh --no-build.
- Deck: SSH deck@192.168.100.130 com ~/.ssh/id_ed25519_deck. NUNCA rodar nada lá se pgrep achar totk ou aoc (o dono
  joga nele). Medição da batalha: bash /c/aoc-win/cmp/deckbattle.sh <etiqueta> [VAR=valor ...]. Resumo de qualquer log
  (medição ou sessão do dono em logs/aoc.log): python tools/deck/logsum.py <log> [--rows] — fps, watts da APU,
  temperatura, GPU, sombra, write-watch, áudio. O dono joga pelo atalho "Hyrule Warriors: Age of Calamity" do Modo Jogo.
- Só um aoc.exe por vez (taskkill //F //IM aoc.exe). Antes de commitar: runtime compila no Linux
  (powershell -c "wsl -d archlinux -- bash /mnt/c/aoc-win/wsl_rt.sh"); commit pelo WSL editando a linha git add de
  C:\aoc-win\commit.sh e a mensagem em C:\aoc-win\commit-msg.txt e rodando
  powershell -c "wsl -d archlinux -- bash /mnt/c/aoc-win/commit.sh" (roda o check_content.py --staged).
- Armadilha: em heredoc, "\\n" chega como quebra de linha e "\a"/"\b" como controle; para texto com barras invertidas
  use a ferramenta de escrita/edição, não heredoc.

Tarefa 1: saves (passo 2). Tarefa 2: Deck — 1280x720 e repouso (passo 3). Tarefa 2: consumo e travadas restantes (passo 3).
Medir rastros: streaks.py marca bandeiras ao vento em 1920x1080; confirmar cada detecção com
C:\aoc-win\streakzoom.py. Perfil de um frame lento: AOC_PROFILE=<arq> AOC_PROFILE_SLOW=<ms> e
python C:\aoc-win\profslow.py <arq>.f<frame>.

Ao terminar cada tarefa: atualizar docs/handover.md, docs/historico.md, docs/aoc.md, docs/plano.md e este arquivo;
commitar. Fale com o dono em pt-BR, direto, com números medidos; não declare corrigido sem medir.
```

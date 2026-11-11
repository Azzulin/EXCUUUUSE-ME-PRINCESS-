# Próxima sessão — plano de ação e prompt

Escrito em 2026-11-09 (fim da sessão 5); atualizado em 2026-11-11 (sessão 6: retângulo branco). Detalhes em `docs/historico.md` (sessão 5), `docs/handover.md` §6 e
`docs/aoc.md` ("Áudio: streams e grafo de mixes", "Resolução do jogo", "Partículas de UI do retângulo branco").

## Estado

- **Corrigido e medido (notebook):** música e som das cinemáticas (ordem dos submixes que saem por splitter,
  `audio_mixer.c` `mix_depth`): 21 de 37 janelas de 5 s em silêncio → 1 (a do boot).
- **Escrito e compilado, sem medição** (commit da sessão 5):
  - resolução: patch sets `output` e `scene` (`recomp/patches-v130.txt`), `runtime/resolution.c` do AoC, perfil do
    Deck em 1280×720 com cena 960×540. O C foi regenerado e o guest/host do **WSL** compilados; o build do Windows
    (`C:\aoc-win`) ainda tem o `generated` antigo;
  - sombra dos pools: `shadow_sync_pool` indica regiões paradas para congelar (`vk_memory.c`);
  - telemetria: linhas `sys:` (`runtime/sysmon.c`) e `tools/deck/logsum.py`.
- **No Deck está o binário da sessão 4** (sem nada disto). Atalho "Hyrule Warriors: Age of Calamity" criado no Modo
  Jogo. O dono reclama de: retângulo branco, resolução estranha, falta de música; quer consumo na casa de 12 W sem
  esquentar.
- **Retângulo branco (sessão 6):** causa achada — o tradutor de shaders perde a condição de um `SYNC` condicional
  do shader do efeito de recuperação de coração (FS `a57f4e05`), e o alfa sai 1. Reproduzido fora do jogo em
  `C:\aoc-win\retangulo` (`aoc_xlate jobs.json out`: `dbg` certo, `opt` errado). **Falta o patch do tradutor.**
- **Do HWDER (2026-11-11):** inverter eixos, mudo e teclas IJKL; falta abrir o menu e olhar.

## Regras da rodada (pedido do dono)

Testes conclusivos, não sondagens: cada corrida de 3 min deve fechar uma pergunta (juntar na mesma corrida o que for
independente). Medir antes de declarar corrigido. Não mandar ao Deck nada que não rodou no notebook. Nunca rodar no
Deck com `totk` ou `aoc` abertos.

## Plano, em ordem

### 1. Levar o que está escrito até o Deck (uma corrida no notebook, uma no Deck)

1. Windows: copiar `~/aoc-build/generated` (WSL) para `C:\aoc-win\generated` (só `main/main_0119.c`, os manifestos e
   `patches.h` mudaram), `wsl --shutdown`, recompilar o guest e o host no UCRT64
   (`python3 tools/build.py --work /c/aoc-win --big-jobs 2 guest host`).
2. Corrida A no notebook (rota de 175 s, `diag1.sh`): `AOC_OUTPUT_RES=1280x720` + `AOC_TRACE=perf,audio` + capturas +
   dump de um frame da batalha. Conferir: linha `resolution: output 1280x720, scene 960x540`; alvos do `passes.txt`
   nos tamanhos novos; HUD inteiro e no lugar (comparar com a captura de 1080p reduzida); 0 erros de validação;
   áudio sem janelas mudas. Se o HUD sair cortado ou deslocado: os oito `1920×1080` de `main+0x1583db8..0x1584798`
   (câmeras de UI) e os `1280×720` de `immscan.py` entram no conjunto `output`.
3. Corrida B no notebook: `AOC_MEMORY=import AOC_SHADOW=1` (o caminho do Deck) com a rota: mesma imagem (luma ~175),
   0 rastros em 201 (`streaks.py`), linha `mem: write-watch` com os MiB congelados subindo e os ms por frame caindo.
4. `dist` no WSL, `tools/deck/deploy.sh --no-build`, medição no Deck (`deckbattle.sh`), depois
   `python tools/deck/logsum.py <run.log>`: fps na batalha (hoje 24,6), GPU ms (hoje 24,6–26,8), sombra ms por frame
   (hoje ~30), **APU em watts e temperatura** (primeira medição). Pedir ao dono para jogar 10 min pelo atalho e ler o
   `logs/aoc.log` com o `logsum.py`.

### 2. Consumo: chegar perto de 12 W

Com os números do passo 1: se a GPU sobrar, baixar a cena (`AOC_RENDER_SCALE`) não muda nada — o limite é a CPU;
atacar então, pela ordem do perfil (`AOC_TRACE=perf,sched`): espera por núcleo virtual (20 % da thread principal),
`nvnSyncWait` (11,6 %), cópias da sombra (10 MiB para dentro e 10 MiB de volta por frame), replay. Conferir o
governador e o limite de TDP do Deck (o dono pode fixar o TDP no menu rápido do SteamOS; medir a 30 fps estáveis qual
TDP basta). Shaders antecipados (Fase E antiga) tiram os picos de CPU das travadas.

### 3. Retângulo branco — PRIMEIRA TAREFA (a última que o dono pediu)

Passo a passo em `docs/historico.md`, sessão 6, "Próximo passo (correção)": achar na IR do tradutor (cópia
instrumentada: `wsl -d archlinux -- bash /mnt/c/aoc-win/retangulo/xldbg.sh`, que reconstrói `/tmp/xldbg` e traduz o
job) o passo que apaga o desvio do `SYNC` condicional; patch `tools/xlate/patches/0014`; reconstruir o tradutor
(`python3 tools/build_xlate.py --out ~/aoc-build/xlate --sysroot ~/aoc-build/toolchain/sniper` no WSL, depois
`bash /mnt/c/aoc-win/xlate_win.sh`); uma corrida da rota para conferir o centro da tela, os rastros e a luma.

### 4. Depois

Shaders antecipados (pacote + warm-up, como o `totk-recomp-main` do dono); trazer `a64.py`/`plt.py`/`dref.py`/
`immscan.py` para `tools/` sem caminhos fixos; DLCs; 60 fps opcional.

## Prompt para colar numa sessão nova

```
Projeto: recompilação estática de Hyrule Warriors: Age of Calamity 1.3.0 (Switch) para x86-64 + Vulkan, alvo Steam Deck,
testado no notebook Windows (RTX 3050). Leia ANTES de tudo: AGENTS.md (regras: docs em pt-BR, C gerado nunca editado à
mão, dados do jogo fora do git, check_content antes de commit), docs/proxima-sessao.md e docs/handover.md, seção 6.

O dono quer: (1) o que a sessão 5 deixou escrito chegar ao Deck medido — resolução nativa 1280x720, sombra dos pools,
música, telemetria; (2) consumo perto de 12 W no Deck sem esquentar; (3) o retângulo branco do centro corrigido na
causa. Testes conclusivos: cada corrida de 3 min fecha uma pergunta; nada vai ao Deck sem ter rodado no notebook.

Ambiente (Windows nativo, MSYS2 UCRT64):
- Build do runtime + link: no PowerShell,
  $env:MSYSTEM="UCRT64"; $env:CHERE_INVOKING="1"; & C:\msys64\usr\bin\bash.exe -lc "bash /c/aoc-win/host.sh"
  (log em C:\aoc-win\host.log). O guest do Windows (C:\aoc-win\lib) está ATRASADO: o C foi regenerado no WSL com os
  patch sets output/scene; copie ~/aoc-build/generated para C:\aoc-win\generated, rode wsl --shutdown e recompile com
  python3 tools/build.py --work /c/aoc-win --big-jobs 2 guest host (no UCRT64).
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

Tarefa 0 (primeira): retângulo branco — patch do tradutor para o SYNC condicional (passo 3 de docs/proxima-sessao.md
e docs/historico.md, sessão 6); material em C:\aoc-win\retangulo. Depurador: gdb -p <pid> -batch -x <script>.
Tarefa 1: passo 1 de docs/proxima-sessao.md inteiro (Windows com o C novo → corrida A de resolução 1280x720 → corrida B
de sombra em modo import → dist → Deck → logsum com watts e temperatura).
Tarefa 2: consumo (passo 2), guiado pelos números da tarefa 1.

Ao terminar cada tarefa: atualizar docs/handover.md, docs/historico.md, docs/aoc.md, docs/plano.md e este arquivo;
commitar. Fale com o dono em pt-BR, direto, com números medidos; não declare corrigido sem medir.
```

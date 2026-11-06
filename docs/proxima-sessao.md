# Próxima sessão — plano de ação e prompt

Escrito em 2026-11-05 (fim da sessão 3), commit de partida `7aae2e4`. Detalhes e números em `docs/handover.md` §6.

## Plano de ação

Estado: a batalha roda a 30 fps no notebook (RTX 3050) sem travar; a perda de GPU com o gravador foi corrigida (3 de 3
corridas limpas).

### Fase A — cor saturada na janela (prioridade do dono) — FEITA na sessão 4

A apresentação lê a imagem do jogo por uma view UNORM num draw que substituiu o `vkCmdBlitImage` (`vk_blit.c`); a
janela é igual à imagem do jogo no mesmo frame (diferença máxima ≤ 1). Números em `historico.md`, sessão 4.

### Fase B — retângulo branco fixo no centro — sem reprodução

Em todas as capturas da janela da sessão 4 a janela é igual à imagem do jogo (diferença máxima ≤ 1); com o menu
fechado e o overlay desligado nada mais é desenhado. Falta o dono dizer quando ele aparece (cena, entrada, overlay
ligado, foto da tela).

### Fase C — linhas brancas (rastros) — FEITA na sessão 4

O otimizador da AST do tradutor movia um voto de warp para dentro do `if` do líder nos computes de partículas
(append atômico errado). Patch 0013 do tradutor: 20–28 frames com rastro em 201 → 0. Detalhes em `historico.md`.

### Fase D — véu claro (imagem real do jogo)

A cena chega ~10× acima da faixa do medidor de exposição do jogo (9,85–16). Descartados: exposição, tonemap, LUT,
matemática da libm do jogo, snapshot de uniformes, máscara de sombra. Pista principal: o céu procedural do cubo de
ambiente sai ~3× mais claro que o mesmo céu na vista (shaders `e28482c2` × `e4d463d9`).

### Fase E — Steam Deck

`tools/build.py dist` no WSL, copiar `dist/aoc-deck`, medir fps na batalha (o perfil do Deck já liga `REPLAY_ASYNC`),
ler `journalctl -k -b -1` da travada anterior.

## Prompt para colar numa sessão nova

```
Projeto: recompilação estática de Hyrule Warriors: Age of Calamity 1.3.0 (Switch) para x86-64 + Vulkan, alvo Steam Deck,
testado hoje no notebook Windows (RTX 3050). Leia ANTES de tudo: AGENTS.md (regras: docs em pt-BR, C gerado nunca editado à
mão, dados do jogo fora do git, check_content antes de commit), docs/proxima-sessao.md e docs/handover.md, seção 6 (estado
e próximos passos com números). Último commit de partida: 7aae2e4.

Ambiente (Windows nativo, MSYS2 UCRT64):
- Build do runtime + link: no PowerShell,
  $env:MSYSTEM="UCRT64"; $env:CHERE_INVOKING="1"; & C:\msys64\usr\bin\bash.exe -lc "bash /c/aoc-win/host.sh"
  (log em C:\aoc-win\host.log; o guest já está compilado em C:\aoc-win\lib, não refaça).
- Rodar a rota até a 1ª batalha (175 s): bash /c/aoc-win/battle.sh [VAR=valor ...]  (no Git Bash). Variáveis úteis: SECS,
  TMO, ROUTE. Log em C:\aoc-win\battle.log, imagem final do jogo em C:\aoc-win\bshot.png, capturas em C:\aoc-win\bshots.
- Imagem final da JANELA (swapchain): AOC_PRESENT_SHOT=4300:C:/aoc-win/present.png
- Dump de frame: AOC_DUMP=4400 AOC_DUMP_DIR=C:/aoc-win/dumpX AOC_DUMP_SKIP_RUNS=1 AOC_VK_RECORDER=0 (+ AOC_DUMP_RAW=1 para
  floats .f32, AOC_DUMP_UBO=48 para uniformes). Python com PIL/numpy/scipy: /c/msys64/ucrt64/bin/python3.
  spirv-cross --vulkan-semantics para ler os sh_*.spv do dump.
- Só um aoc.exe por vez (taskkill //F //IM aoc.exe). Antes de commitar: conferir que o runtime compila no Linux com
  powershell -c "wsl -d archlinux -- bash /mnt/c/aoc-win/wsl_rt.sh"; commitar pelo WSL editando a linha git add de
  C:\aoc-win\commit.sh e a mensagem em C:\aoc-win\commit-msg.txt e rodando
  powershell -c "wsl -d archlinux -- bash /mnt/c/aoc-win/commit.sh" (roda o check_content.py --staged).
- Armadilha: em heredoc com Python, "\a" e "\b" viram caracteres de controle; caminhos C:\aoc-win em strings Python
  precisam de barra dupla ou raw string.

Tarefa 1 (prioridade do dono): a cor na janela está escura e supersaturada. Medido: grama 163,203,155 na imagem do jogo
(dump/--shot) e 92,162,81 na janela = decodificação sRGB->linear. O jogo codifica uma vez só (alvo RGBA8_SRGB, NVN 0x38);
o Switch mostra esses bytes. Nossa apresentação (runtime/gfx_present.c present_image, runtime/vk_fsr.c, runtime/vk_color.c)
usa swapchain UNORM e lê a fonte pela view do formato dela (sRGB), decodificando. Corrija para a janela mostrar os bytes
do jogo: ler a fonte por uma view UNORM (imagens de cor são MUTABLE_FORMAT) nos caminhos FSR e blit, sem mudar o menu
ImGui nem os ajustes de cor. Verifique com AOC_PRESENT_SHOT que a grama fica 163,203,155 como no --shot. A janela vai
ficar mais clara/lavada: é a imagem verdadeira; não "compense" com ajustes.

Tarefa 2: o dono vê um retângulo branco fixo no centro da janela (some na cor forte). Não aparece na imagem do jogo; depois
da tarefa 1, achar com AOC_PRESENT_SHOT qual passo da apresentação o desenha.

Tarefa 3: linhas brancas de um frame (rastros) vindas dos quads indiretos (runtime/vk_quad_ind.c); detector
C:\aoc-win\streaks.py; ver handover §6.

Ao terminar cada tarefa: atualizar docs/handover.md (estado e próximos passos), docs/historico.md e este arquivo,
commitar. Fale com o dono em pt-BR, direto, com números medidos; não declare corrigido sem medir.
```

# Próxima sessão — plano de ação e prompt

Escrito em 2026-11-06 (fim da sessão 4). Detalhes e números em `docs/handover.md` §6 e `docs/historico.md`, sessão 4.

## Estado

- Feito na sessão 4: a imagem da batalha deixou de sair lavada (views sRGB dos mapas de cor respeitadas na
  amostragem; luma média 233 → 175, nxnative 163); a janela mostra os bytes do jogo (view UNORM da textura sRGB,
  `vk_blit.c`); os rastros brancos dos
  efeitos sumiram (patch 0013 do tradutor: ballot, voto e shuffle ficam no lugar; 20–28 frames com rastro em 201 → 0);
  a devolução do mirror grava só as palavras que a GPU mudou (−1,7 ms de GPU por frame na RTX 3050); o `aoc.exe` leva
  manifesto (DPI por monitor, UTF-8).
- O tradutor mudou (identidade `d10880c4…`): o primeiro jogo depois de atualizar traduz todos os shaders de novo (a
  entrada da batalha passa de 6 s sem present uma vez).
- A pasta do Deck já está montada em `dist/aoc-deck` com o runtime e o tradutor novos, **mas não foi enviada**: às
  19h58 de 2026-11-06 o dono estava jogando o TotK no Deck.

## Plano de ação

### Fase E — Steam Deck (primeiro, quando o Deck estiver livre)

1. Conferir que nada roda lá: `ssh -i ~/.ssh/id_ed25519_deck deck@192.168.100.130 "pgrep -a totk; pgrep -a aoc"`.
2. Enviar: `bash tools/deck/deploy.sh --no-build` (Git Bash; manda só `aoc`, `aoc_xlate`, `aoc_xlate.id` e o que mudou).
3. Rodar a rota até a batalha (`tools/deck/deck_run.sh`), medir fps (o perfil do Deck liga `REPLAY_ASYNC`; antes eram
   16–21 fps) e conferir a imagem: sem rastros e com a cor da imagem do jogo.
4. `journalctl -k -b -1` da travada antiga, se ainda houver o boot dela.

### Fase D — véu claro — FEITA na sessão 4

As views sRGB dos mapas de cor (BC7/BC3/BC1 UNORM lidos por views sRGB) eram ignoradas na amostragem. Luma média
233 → 175 (nxnative: 163). Detalhes em `historico.md`.

### Fase B — retângulo branco fixo no centro

Com a cor certa ele aparece na **imagem do jogo**: branco puro, ~20×38 px em 1920×1080, no centro exato da tela, parado
com a câmera andando (capturas `AOC_SHOTS` a partir de ~140 s). Fazer o dump de um frame da batalha
(`AOC_DUMP=4300 AOC_DUMP_DIR=C:/aoc-win/dumpq AOC_DUMP_SKIP_RUNS=1 AOC_VK_RECORDER=0`), achar o primeiro pass em que o
pixel central fica branco e o draw que o pinta (HUD, mira; textura ou shader).

## Prompt para colar numa sessão nova

```
Projeto: recompilação estática de Hyrule Warriors: Age of Calamity 1.3.0 (Switch) para x86-64 + Vulkan, alvo Steam Deck,
testado no notebook Windows (RTX 3050). Leia ANTES de tudo: AGENTS.md (regras: docs em pt-BR, C gerado nunca editado à
mão, dados do jogo fora do git, check_content antes de commit), docs/proxima-sessao.md e docs/handover.md, seção 6.

Ambiente (Windows nativo, MSYS2 UCRT64):
- Build do runtime + link: no PowerShell,
  $env:MSYSTEM="UCRT64"; $env:CHERE_INVOKING="1"; & C:\msys64\usr\bin\bash.exe -lc "bash /c/aoc-win/host.sh"
  (log em C:\aoc-win\host.log; o guest já está compilado em C:\aoc-win\lib, não refaça).
- Rodar a rota até a 1ª batalha (175 s): bash /c/aoc-win/battle.sh [VAR=valor ...]  (no Git Bash). Variáveis úteis: SECS,
  TMO, ROUTE. Log em C:\aoc-win\battle.log, imagem final do jogo em C:\aoc-win\bshot.png, capturas em C:\aoc-win\bshots.
- Imagem da JANELA (swapchain) num frame: AOC_PRESENT_SHOT=<frame>:<png>; imagem do jogo no mesmo frame:
  AOC_SHOTS=<frame>-<frame>:1 AOC_SHOTS_FULL=1; comparação: python3 C:\aoc-win\cmp\cmp.py <jogo.png> <janela.png>.
- Rastros: AOC_SHOTS=w140-160:0.1 e python3 C:\aoc-win\streaks.py (hoje 0 em 201).
- Dump de frame: AOC_DUMP=4400 AOC_DUMP_DIR=C:/aoc-win/dumpX AOC_DUMP_SKIP_RUNS=1 AOC_VK_RECORDER=0 (+ AOC_DUMP_RAW=1 para
  floats .f32, AOC_DUMP_UBO=48 para uniformes). Python com PIL/numpy/scipy: /c/msys64/ucrt64/bin/python3.
  spirv-cross --vulkan-semantics para ler os sh_*.spv do dump.
- Tradutor de shaders: patches em tools/xlate/patches (13); no WSL, python3 tools/build_xlate.py --out ~/aoc-build/xlate
  --sysroot ~/aoc-build/toolchain/sniper e depois bash /mnt/c/aoc-win/xlate_win.sh (exe do Windows em C:\aoc-win\host).
- Pasta do Deck: wsl -d archlinux -- bash /mnt/c/aoc-win/dist.sh; envio: bash tools/deck/deploy.sh --no-build.
- Só um aoc.exe por vez (taskkill //F //IM aoc.exe). Antes de commitar: conferir que o runtime compila no Linux com
  powershell -c "wsl -d archlinux -- bash /mnt/c/aoc-win/wsl_rt.sh"; commitar pelo WSL editando a linha git add de
  C:\aoc-win\commit.sh e a mensagem em C:\aoc-win\commit-msg.txt e rodando
  powershell -c "wsl -d archlinux -- bash /mnt/c/aoc-win/commit.sh" (roda o check_content.py --staged).
- Armadilha: em heredoc com Python, "\a" e "\b" viram caracteres de controle; caminhos C:\aoc-win em strings Python
  precisam de barra dupla ou raw string.

Tarefa 1: levar ao Deck (Fase E de docs/proxima-sessao.md) e medir fps e imagem na batalha. Só com o Deck livre.
Tarefa 2: retângulo branco no centro da tela (Fase B): está na imagem do jogo; achar o draw pelo dump.

Ao terminar cada tarefa: atualizar docs/handover.md (estado e próximos passos), docs/historico.md e este arquivo,
commitar. Fale com o dono em pt-BR, direto, com números medidos; não declare corrigido sem medir.
```

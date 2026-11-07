# Próxima sessão — plano de ação e prompt

Escrito em 2026-11-06, 21h40 (fim da sessão 4). Detalhes e números em `docs/handover.md` §6, `docs/historico.md`
(sessão 4) e `docs/aoc.md` ("Steam Deck na batalha", "Material de UI do retângulo branco").

## Estado

- **Feito na sessão 4** (commits `1e0457e` a este): a janela mostra os bytes do jogo (view UNORM, `vk_blit.c`); os
  rastros brancos dos efeitos sumiram (patch 0013 do tradutor: 20–28 frames com rastro em 201 → 0); a imagem da
  batalha deixou de sair lavada (views sRGB respeitadas: luma 233 → 175, nxnative 163); a devolução do mirror grava só
  as palavras que a GPU mudou (−1,7 ms de GPU por frame na RTX 3050); o `aoc.exe` leva manifesto; o censo de páginas
  sujas só roda com `AOC_DIRTY_CENSUS=1`.
- **Deck**: runtime e tradutor da sessão 4 enviados às 21h24 (identidade do tradutor `d10880c4…`, cache já traduzido
  lá). Imagem igual à do PC (luma 176, sem rastros). A batalha mediu **12,8 fps** com GPU 29,6 ms por frame, mas
  **com o censo ligado** (516 consultas de write-watch sobre 41 GB, 63 ms por frame, na thread do replay): o número
  real ainda não existe. No notebook em modo import, desligar o censo levou as consultas de 23,7 GB / 25 ms para
  2 MiB / 0,027 ms por frame.
- **Retângulo branco**: localizado (programa 720 do HUD, modo 12) e com tradução e `BRX` conferidos: o shader faz o
  que o código Maxwell diz. O defeito está no que chega ao draw (posição/escala, uniformes) ou na visibilidade.

## Plano da rodada

Ordem: medir antes de mexer. Imagem certa antes de desempenho, mas o retângulo é um elemento de HUD e não bloqueia a
frente do Deck; as duas podem andar juntas (o Deck só quando estiver livre).

### Fase A — Deck: medição limpa da batalha (primeiro, só com o Deck livre)

1. `bash /c/aoc-win/cmp/deckbattle.sh limpa` (Git Bash). O script se recusa a rodar se `totk` ou `aoc` estiverem
   abertos lá; roda a rota de 175 s com `AOC_TRACE=perf,sched`, traz `run.log` e `shot.png` para
   `C:\aoc-win\cmp\deck-limpa` e resume fps, write-watch, intervalo/GPU, a thread principal e a luma.
2. Esperado: linha `mem: write-watch` com poucos MiB por frame (antes 41 GB). Registrar em `docs/aoc.md`, tabela
   "Steam Deck na batalha" (trocar a linha "com o censo ligado").
3. Se a batalha já fechar 30 fps: medições do Portão F (`docs/plano.md`, Fase 5: 1 % low, W da APU, temperatura,
   1 h sem crash). Se não: Fase B com os números novos.

### Fase B — CPU do Deck na batalha (se ficar abaixo de 30 fps)

Números da medição contaminada, para comparar: thread principal 64 % no código do jogo (~50 ms por frame contra ~16 ms
no notebook), 20–21 % esperando núcleo virtual, 15 % no host, quase tudo em `nvnSyncWait` (`exe+0x96ac0e`,
`nvn_api_core.c:488`); workers girando em `main+0x17496a0`.

1. **`nvnSyncWait`**: o que a thread principal espera — o replay (`REPLAY_ASYNC`, que agora não carrega mais o censo)
   ou a GPU. A linha `perf: ... fence wait per frame` e o `render thread blocked: fence/drain` separam os dois.
2. **Código do jogo 3× mais lento que no notebook**: o Zen 2 do Deck não explica sozinho. Medir as faltas de página do
   write-watch (`userfaultfd` com WP assíncrono: cada primeira escrita numa página protegida é uma falta) por frame;
   `/proc/<pid>/stat` (minflt) antes e depois de uma janela da batalha basta. Conferir também a frequência das CPUs
   durante a batalha (`/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq`) e o limite de TDP do Deck.
3. **Spin wait em `main+0x17496a0`**: ver se está na tabela de `recomp/patches-v130.txt` (1 112 spin waits); se não
   estiver e girar sem yield, ele rouba núcleo da thread principal (os 20 % de espera por núcleo virtual). Conferir os
   bytes originais no dump antes de qualquer patch (patch do lifter, nunca edição da saída).
4. Só depois disso: replay (binds de textura e dispatches por frame) — medir com `AOC_TRACE=perf` qual parte do
   replay pesa, sem alocação por frame nos caminhos quentes.

### Fase C — GPU do Deck

GPU 29,6 ms por frame na batalha com a saída do jogo sempre em 1920×1080 (o gerador não tem os patches de resolução;
`AOC_OPERATION_MODE=handheld` e `AOC_OUTPUT_RES` não a mudam). Com a CPU resolvida, a GPU fica no limite dos 33 ms.

1. Descobrir por que o modo portátil não muda a resolução do jogo: o que o jogo lê (`nn::oe::GetOperationMode`,
   `GetDefaultDisplayResolution`) e o que respondemos. No Switch portátil o jogo renderiza menos que 1080p.
2. Patches de resolução do nxnative (endereços valem para estes build IDs; conferir os bytes no nosso dump) como
   patches do lifter, se o item 1 não bastar.
3. Medir a GPU por pass no Deck antes de cortar qualquer coisa (nada de pular draws).

### Fase D — retângulo branco no centro (imagem)

O que já se sabe (programa 720, pass 95, quad aditivo, modo 12, alfa da máscara 255, tradução e `BRX` conferidos)
está em `historico.md`, sessão 4. Próximos passos:

1. Dump do frame com todos os uniformes do VS: `AOC_DUMP=4400 AOC_DUMP_DIR=C:/aoc-win/dumpR AOC_DUMP_UBO=48
   AOC_DUMP_SKIP_RUNS=1 AOC_VK_RECORDER=0` e ler a matriz `c3[6..8]` do VS `bc173f45` (o `c3[8]` não saiu no último;
   conferir o tamanho do bloco vinculado). Com a matriz, calcular onde o quad cai e com que escala.
2. Ver se algum `UpdateUniformBuffer` reescreve esse bloco na submissão (`vk_exec_draw.c` `upd_note`: o dump mostra o
   valor de antes) — um uniforme lido velho pode deixar visível um elemento que o jogo escondeu (escala 0, alfa 0).
3. Comparar com o nxnative no mesmo ponto da batalha (README dele, capturas): o elemento existe lá? É o retículo de
   mira / marcador de alvo? Isso diz se o certo é não desenhar ou desenhar outra coisa.
4. Corrigir na causa (replay/uniformes/estado), nunca pulando o draw.

### Fase E — travadas de shader com cache frio

A entrada da batalha com cache frio trava ~20 s (pipelines 13,6 s, tradução 4 s; 13,5 s no Deck), e toda mudança do
tradutor esfria o cache. Fazer o pacote de shaders antecipados como o `Deck Zelda/totk-recomp-main` do dono
(`tools/shader_pack.py` + `tools/linux/warmup.sh`), com o `census_shaders.py` e o `shader_pairs.tsv` do nxnative, no
formato de semente do runtime (`--prepare-shaders`). Lá também: memory guard do GTT e pools de imagens.

### Fase F — som do vídeo de abertura

Silêncio exato durante o `movie/Movie001.webm` (sem faixa de áudio no `.webm`; o som vem do motor do KTGL). Começar
pelo relógio/timestamps que o nosso decodificador VP9 entrega ao player (`ov_movie.c`); detalhes no handover §6.

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
  Resumo de desempenho: bash /c/aoc-win/cmp/perfsum.sh. Modo do Deck no notebook: AOC_MEMORY=import.
- Imagem da JANELA (swapchain) num frame: AOC_PRESENT_SHOT=<frame>:<png>; imagem do jogo no mesmo frame:
  AOC_SHOTS=<frame>-<frame>:1 AOC_SHOTS_FULL=1; comparação: python3 C:\aoc-win\cmp\cmp.py <jogo.png> <janela.png>.
- Rastros: AOC_SHOTS=w140-160:0.1 e python3 C:\aoc-win\streaks.py (hoje 0 em 201).
- Dump de frame: AOC_DUMP=4400 AOC_DUMP_DIR=C:/aoc-win/dumpX AOC_DUMP_SKIP_RUNS=1 AOC_VK_RECORDER=0 (+ AOC_DUMP_RAW=1 para
  floats .f32, AOC_DUMP_UBO=48 para 48 vec4 de uniformes). Python com PIL/numpy/scipy: /c/msys64/ucrt64/bin/python3.
  spirv-cross --vulkan-semantics para ler os sh_*.spv do dump.
- Tradutor de shaders: patches em tools/xlate/patches (13); no WSL, python3 tools/build_xlate.py --out ~/aoc-build/xlate
  --sysroot ~/aoc-build/toolchain/sniper e depois bash /mnt/c/aoc-win/xlate_win.sh (exe do Windows em C:\aoc-win\host).
- Deck: SSH deck@192.168.100.130 com ~/.ssh/id_ed25519_deck. NUNCA rodar nada lá se pgrep achar totk ou aoc (o dono
  joga nele). Medição da batalha: bash /c/aoc-win/cmp/deckbattle.sh <etiqueta> [VAR=valor ...] (recusa se ocupado).
  Pasta do Deck: wsl -d archlinux -- bash /mnt/c/aoc-win/dist.sh; envio: bash tools/deck/deploy.sh --no-build.
  O censo de páginas sujas só com AOC_DIRTY_CENSUS=1 (custa ~63 ms por frame no Deck; não ligar para medir fps).
- Só um aoc.exe por vez (taskkill //F //IM aoc.exe). Antes de commitar: conferir que o runtime compila no Linux com
  powershell -c "wsl -d archlinux -- bash /mnt/c/aoc-win/wsl_rt.sh"; commitar pelo WSL editando a linha git add de
  C:\aoc-win\commit.sh e a mensagem em C:\aoc-win\commit-msg.txt e rodando
  powershell -c "wsl -d archlinux -- bash /mnt/c/aoc-win/commit.sh" (roda o check_content.py --staged).
- Armadilha: em heredoc com Python, "\a" e "\b" viram caracteres de controle; caminhos C:\aoc-win em strings Python
  precisam de barra dupla ou raw string. Para texto com barras invertidas, use a ferramenta de edição, não heredoc.

Tarefa 1: Fase A de docs/proxima-sessao.md — medição limpa da batalha no Deck (só com o Deck livre), e Fase B/C conforme
os números.
Tarefa 2: Fase D — retângulo branco: uniformes do VS do programa 720 (c3[6..8]) e por que o elemento está visível.
Depois: Fase E (shaders antecipados) e Fase F (som do vídeo).

Ao terminar cada tarefa: atualizar docs/handover.md (estado e próximos passos), docs/historico.md, docs/aoc.md (números),
docs/plano.md e este arquivo; commitar. Fale com o dono em pt-BR, direto, com números medidos; não declare corrigido
sem medir.
```

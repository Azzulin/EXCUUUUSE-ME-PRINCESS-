# Steam Deck — restrições e orçamento

Alvo principal: Steam Deck (LCD ou OLED), SteamOS 3.8+, jogo instalado no **cartão SD de 1 TB**.

## Requisitos do sistema

| Requisito | Por quê | Deck |
|---|---|---|
| x86-64-v3 (AVX2/FMA) | build padrão do C gerado | Zen 2: sim |
| Linux ≥ 6.7 | write-watch com `userfaultfd` WP + `PAGEMAP_SCAN` | SteamOS 3.8 usa kernel 6.16 |
| Vulkan 1.3 + `VK_EXT_external_memory_host` | importar a memória dos pools do jogo | RADV: sim |
| `VK_EXT_graphics_pipeline_library` | montar pipelines sem stutter | RADV: sim |
| glibc ≥ 2.29 (jogo) | build contra o sysroot *sniper* do Steam Runtime 3 (o executável pede no máximo 2.29) | sim |
| ASTC nativo | texturas do Switch | **não**, mas o AoC só usa BC1–BC7, que o RDNA2 lê nativamente |

## Disco (cartão SD de 1 TB)

Espaço não é restrição: base + update + DLCs, executável, shaders traduzidos e todos os caches cabem com folga. O
que importa no cartão é **velocidade**: leitura sequencial de ~90–100 MB/s (UHS-I) e leitura aleatória lenta.

| Item | Tamanho estimado | Decisão |
|---|---|---|
| RomFS mesclado (base + 1.3.0) | **?** (Fase 0) | ler os RDB como estão (zlib em blocos), em leituras grandes |
| DLCs | **?** | `.rdb.bin3_0`, mesmo formato |
| Executável + bibliotecas | ~0,3–0,6 GB | |
| SPIR-V traduzido (40 726 shaders) | ~0,5–1 GB | AOT na instalação |
| Cache de pipeline Vulkan | ~0,2–0,5 GB | |
| Mesa shader cache | sem teto apertado | `MESA_SHADER_CACHE_DIR` ao lado do jogo, não em `~/.cache` (que fica na memória interna) |
| Saves e configs | < 50 MB | |

Com espaço sobrando, uma opção que seria cara fica barata:

- **Dados "quentes" descomprimidos** (por exemplo, o container de shaders e os arquivos lidos em toda batalha), se
  as medições mostrarem que a descompressão zlib pesa na CPU.

O dump original, as chaves e o C gerado continuam no **PC**. **O Deck não compila nada.**

## Pasta única para o Deck

Tudo que o jogo precisa fica numa pasta só, montada no PC por `tools/build.py --work ~/aoc-build dist` em
`<repositório>/dist/aoc-deck/` ([building.md](building.md), seção 5). Copia-se a pasta inteira para o cartão SD
(FTP, armazenamento na nuvem ou cabo). Layout atual:

```
aoc-deck/
  aoc                    executável Linux x86-64 (código do jogo recompilado + runtime), linkado contra o sniper
  aoc.sh                 lançador: MESA_SHADER_CACHE_DIR ao lado do jogo, cria logs/ e mesa-cache/
  lib/libSDL3.so.0       a SDL 3.4.18 do sniper (o executável procura em $ORIGIN/lib primeiro)
  exefs/                 main, subsdk0, sdk, main.npdm (o runtime mapeia .rodata/.data daqui e confere os SHA-256)
  romfs-index.bin        índice do RomFS (conferido contra o romfs.bin)
  romfs/romfs.bin        RomFS 1.3.0 mesclado (10,9 GiB); `dist --with-romfs` põe um hardlink (não ocupa disco no PC)
  LEIA-ME.txt            instalação por FTP, Steam e controles, em português
  aoc.ini                criado só na primeira vez (menu em pt-BR); depois é do jogador
  profile/               saves e conta local, criado ao lado do executável na primeira execução
  logs/  mesa-cache/     criados pelo aoc.sh
  (depois) shaders/      SPIR-V traduzido dos 40 729 shaders + cache de pipelines
  (depois) dlc/          RomFS dos DLCs
```

- O executável pede no máximo **GLIBC_2.29**; Vulkan, áudio (ALSA/PulseAudio/PipeWire), X11/Wayland e as demais
  bibliotecas que a SDL3 usa vêm do próprio SteamOS. Opus, libvpx e zstd estão dentro do executável.
- No Deck: Desktop Mode → copiar a pasta → "Add a Non-Steam Game" apontando para `aoc.sh` → jogar no Game Mode.
- Primeiro teste no Deck (Desktop Mode, Konsole, dentro da pasta): `./aoc --selftest` e depois
  `AOC_GPU=null AOC_TRACE=perf ./aoc.sh` — deve mostrar linhas `fps: ... (30.0 fps)`. Sem `AOC_GPU=null` ele abre a
  janela Vulkan (Fase 3: os shaders ainda não são traduzidos).
- Atualizar = rodar `dist` de novo e copiar `aoc` (o resto só muda quando muda o jogo); saves e `aoc.ini` ficam.
- O runtime tem um perfil "deck" (`cfg.c`, `AOC_DEVICE_PROFILE=auto|desktop|deck`, detectado pelo DMI: Valve
  Jupiter/Galileo): tela cheia 1280×800, vsync, **30 fps** e **modo portátil** (a resolução de render mais leve do
  próprio jogo), para poupar o Deck.
- O FTP a partir do Windows não leva o bit de execução: o LEIA-ME manda dar `chmod +x aoc aoc.sh` uma vez, e o
  `aoc.sh` ainda tenta marcar o `aoc` sozinho.

## Menu rápido (L3+R3 segurado)

Segurar L3+R3 por ~1,5 s (`AOC_QUICK_HOLD_MS`) abre um painel pequeno; tocar L3+R3 continua alternando o overlay de
FPS, e Menos+Mais abre o menu completo. B fecha.

| Linha | Valores | Observação |
|---|---|---|
| Taxa de quadros | **30** (padrão); 60 aparece desativado | 30 é a taxa do jogo: ele anda um passo fixo por quadro, então menos de 30 deixaria o jogo lento. 60 depende do patch de frame-step (Fase 6) |
| Resolução interna | **Portátil** (padrão no Deck) / TV | É o modo de operação do Switch: o jogo escolhe a própria resolução de render. A troca é ao vivo, com as mensagens `OperationModeChanged`/`PerformanceModeChanged` do `oe`, como ao tirar o Switch do dock — medido: o jogo relê o modo logo depois (`main+0x8cec30`). O ganho real de GPU só se mede com Vulkan, no Deck |
| Overlay de desempenho | desligado / FPS / completo | o mesmo do toque em L3+R3 |

Para gastar ainda menos, o menu de desempenho do próprio Steam (botão "...") limita TDP e taxa de atualização.

Ressalva: a pasta final contém o jogo (RomFS + código derivado). É para uso próprio — não compartilhar.

## Orçamento de desempenho (metas, não promessas)

| Modo | Resolução interna → saída | Meta | Energia |
|---|---|---|---|
| Original 30 (padrão) | ~1280×720 → 1280×800 | 30 fps travados na primeira batalha | ≤ 15 W |
| Bateria | ~960×600 + FSR1 → 1280×800 | 30 fps | ~10 W |
| 40 Hz | a definir | 40 fps (depende da pesquisa da Fase 6) | ≤ 15 W |
| 60 fps experimental | ~960×600 + FSR1 | 45–60 fps fora das batalhas grandes | 15 W |

Onde o tempo de frame vai pesar (em ordem de suspeita): replay NVN→Vulkan na CPU nas batalhas → uploads de pools
escritos pela CPU (write-watch + cópias sombra) → GPU em si. (Não há decodificação ASTC: o jogo só usa BCn.)

Ferramentas de medição: overlay próprio (F10 / L3+R3) com frame time p50/p95/p99, tempos de replay, upload, tradução
e montagem de pipeline; overlay de desempenho do Steam para watts e temperatura.

## Controles

- Steam Input entrega um controle tipo Xbox via SDL3 — os botões A/B/X/Y do Deck seguem a posição Xbox; oferecer a
  opção de posição Nintendo.
- Câmera no analógico direito (`pad_layout full`).
- Gyro: o Deck tem, mas o Steam Input pode escondê-lo; tratar como opcional.
- Teclado/mouse só no Desktop Mode e no PC.

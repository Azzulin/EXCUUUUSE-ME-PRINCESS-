# Steam Deck — restrições e orçamento

Alvo principal: Steam Deck (LCD ou OLED), SteamOS 3.8+, jogo instalado no **cartão SD de 1 TB**.

## Requisitos do sistema

| Requisito | Por quê | Deck |
|---|---|---|
| x86-64-v3 (AVX2/FMA) | build padrão do C gerado | Zen 2: sim |
| Linux ≥ 6.7 | write-watch com `userfaultfd` WP + `PAGEMAP_SCAN` | SteamOS 3.8 usa kernel 6.16 |
| Vulkan 1.3 + `VK_EXT_external_memory_host` | importar a memória dos pools do jogo | RADV: sim |
| `VK_EXT_graphics_pipeline_library` | montar pipelines sem stutter | RADV: sim |
| glibc ≥ 2.31 (jogo) | build contra o sysroot *sniper* do Steam Runtime 3 | sim |
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

O dump original, as chaves e o C gerado continuam no **PC** (WSL2): o build é muito mais rápido lá.

Fluxo recomendado:

1. No PC (WSL2): extrair, gerar C, compilar, traduzir shaders → pasta `dist/aoc-deck/`.
2. Copiar `dist/aoc-deck/` para o cartão SD (rede, USB ou `rsync` pelo SSH do Deck).
3. No Deck: primeira execução monta caches de pipeline; "Add to Steam" para o Game Mode.

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

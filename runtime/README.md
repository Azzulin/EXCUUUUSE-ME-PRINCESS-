# runtime/ — o "Horizon" do host

Desde 2026-11-04 este diretório é o runtime do **Astral Chain Recomp** (`3bbaf259`, MIT), que por sua vez veio do
TotK Recomp, mais a **porta Linux do TotK Recomp** (`c38e0ca`, MIT): `platform/linux.c`, `gfx_window_sdl.c`,
`input_sdl.c`, `swkbd_sdl.c`, `folder_pick_sdl.c` e os vídeos VP9 (`ov_movie.c`). As variáveis `AC_*`/`TOTK_*`
viraram `AOC_*` e o arquivo de configuração é `aoc.ini`. Origem de cada parte em `THIRD_PARTY_NOTICES.md`.

`tools/build.py` compila tudo aqui menos os arquivos do Windows (`*_win.*`, `platform/win32.c`); o `dist` compila os
mesmos fontes contra o sysroot sniper para o Deck.

| Área | Arquivos |
|---|---|
| Loader, dispatch, memória | `loader.c`, `dispatch.c`, `memory.c`, `hostfn.c`, `boot.c`, `main.c` |
| Kernel (3 cores virtuais, SVCs) | `kernel.c`, `svc.c` |
| IPC e serviços | `ipc.c` (CMIF, TIPC, domínios), `ov_*.c` (overrides `nn::*` e serviços: `fsp-srv`, `hid`, `hwopus`, `audren:u`...) |
| Áudio | `audren.c`, `audio_*.c` (SDL3) |
| RomFS / saves | `romfs.c`, `fs_host.c` |
| NVN front end | `nvn_api_*.c`, `nvn_obj.h`, `nvn_tex.c` |
| Vulkan back end | `vk_*.c`, `gfx_*.c` |
| Entrada, janela, menu | `input*.c`, `gfx_window_*.c`, `ui/` (Dear ImGui) |
| Plataforma | `platform/linux.c`, `platform/win32.c`, `platform/platform.h` |
| CPU do código gerado | `cpu.h`, `simd.h`, `simd_fp.h`, `fma.c` |

Mudanças nossas para o AoC (todas com comentário no código):

- `ipc.c`: domínios CMIF de verdade (o SDK 9.6 converte o `fsp-srv`).
- `ov_hwopus.c`: decodificadores Opus multistream (`OpusMSDecoder` da libopus).
- `ov_input.c`: `GetTouchScreenState<1>` e o estado de toque zerado por inteiro.
- `ov_system.c`: copyright framebuffer (no-op) e `CountAddOnContent`.
- `romfs.c`: sem mapeamento em endereço fixo (o AoC usa `MountRom`); `platform/linux.c`: gancho de falha de leitura.
- `hostfn.c`/`host.h`: seções ELF `aoc_ovr`/`aoc_obs`; `nvn_api_obj.c`: `movie_tick` no present.
- `nvn_api_cmd.c`, `vk_exec.c`, `vk_exec_xfer.c`: `nvnCommandBufferSetCopyImageStride` (passo de camada das cópias).
- `ui/menu.cpp`, `input.c`, `input_map.c`, `ui_text.*`: menu rápido (L3+R3 segurado); `ov_system.c`: troca de modo
  portátil/TV ao vivo e o gancho de teste `AOC_TEST_OPMODE`; `cfg.c`: 30 fps padrão, perfil do Deck em modo portátil;
  `main.c`: `profile/` ao lado do executável numa pasta portátil.

# runtime/ — o "Horizon" do host

Vazio de propósito até a Fase 2. Estrutura prevista (herdada do Astral Chain):

| Área | Arquivos previstos | Fase |
|---|---|---|
| Loader, dispatch, memória | `loader.c`, `dispatch.c`, `memory.c` | 2 |
| Kernel (3 cores virtuais, SVCs) | `kernel.c`, `svc.c` | 2 |
| IPC e serviços | `ipc.c`, `ov_*.c` | 2 |
| Áudio (audren + SDL3) | `audren.c`, `audio_*.c` | 2 / 4 |
| RomFS / RDB / saves | `romfs.c`, `fs_host.c` | 2 |
| NVN front end | `nvn_api_*.c`, `nvn_obj.h`, `nvn_tex.c` | 3 |
| Vulkan back end | `vk_*.c` | 3 |
| Entrada, janela, menu | `input*.c`, `gfx_window*.c`, `ui/` | 4 |
| Plataforma | `platform/linux.c`, `platform/win32.c` | 2 / 5 |

# Referências

Revisões fixadas em 2026-11-03 (as mesmas de `tools/fetch_refs.sh`). `refs/` é só leitura e fica fora do git.

| Projeto | Revisão | Licença | Para que olhar |
|---|---|---|---|
| [astral-chain-pc-recomp](https://github.com/captainj-sparrow/astral-chain-pc-recomp) | `3bbaf259ac099a321c78b81f5402f6070a77874a` | MIT | Pipeline x86-64 completo adaptado a um segundo jogo: `recomp/`, `runtime/`, `docs/architecture.md`, `docs/handover.md`, `docs/maxwell.md`, `tools/check_content.py` |
| [totk-pc-recomp](https://github.com/valentderah/totk-pc-recomp) | `c38e0ca13d2bceb0590b195f69a010315913850d` | MIT | Linux, Steam Deck, AppImage, write-watch, pools sombra: `docs/building.md` ("Linux"), `docs/installer.md` ("Linux release"), `docs/tester-guide.md` ("Steam Deck") |
| [nxnative](https://github.com/seedds/nxnative) | `3ace3df33b81681cdc9d17bfa48eadaccd446b5c` | MIT | **Perfil do AoC**: `dm/games/01002B00111A2000/` (`README.md`, `game.tsv`, `patches.py`, tabelas de shader); `dm/gfx/tools/shader_split.py`; `docs/reference/` (áudio, rendering, rewriter, memória) |
| [MacNativeGames](https://github.com/ly05010419/MacNativeGames) | `3ac015c3ad1291d529bb086b1342ec5ec7db8eb3` | MIT | `games/aoc/` (`ANALYSIS.md`, `README.md`, `VALIDATION.md`): auditoria de 13 ports, timing dinâmico, problema da cutscene a 60 fps |
| [HWDER](https://github.com/blocker-3/HWDER) | `444b67c02d4c57ad2e2fdd5d4430c4ac7171fb1f` | MIT | Mesma engine (geração anterior), abordagem GPU LLE, Linux no ROG Ally: `docs/how-it-works.md`, `docs/DECISIONS.md`, `docs/linux-native.md` |
| [LASRecomp](https://github.com/peiikai/LASRecomp) | `a6b4f03844ecfb4012f18deff96da8b410aeafcd` | MIT | Lifter original, testes diferenciais |
| [SavageWindRecomp](https://github.com/Revivedx/SavageWindRecomp) | `bf6146c14c37fee8781a601e5a544b93dff6d75e` | MIT | Preempção em chamadas indiretas, menu e overlay |

Leitura de comportamento apenas (GPL — nunca copiar código): yuzu, suyu, Ryujinx (fora do tradutor de shader 1.3.2
que já vem via MIT), Eden/Citron.

Documentação pública da plataforma: [Switchbrew](https://switchbrew.org) (SVCs, IPC, formatos NSO/NPDM/NCA).

## Leitura recomendada, nesta ordem

1. `nxnative/dm/games/01002B00111A2000/README.md` — tudo que já se sabe do AoC.
2. `astral-chain-pc-recomp/docs/architecture.md` — o pipeline que vamos seguir.
3. `astral-chain-pc-recomp/docs/astral-chain.md` — como foi a adaptação para um jogo novo (modelo para o nosso `docs/aoc.md`).
4. `MacNativeGames/games/aoc/ANALYSIS.md` — lições de 13 ports e portões de aceitação.
5. `totk-pc-recomp/docs/building.md` seção Linux + `docs/installer.md` seção "Linux release".
6. `astral-chain-pc-recomp/docs/maxwell.md` — comportamento Maxwell que o Vulkan precisa imitar.

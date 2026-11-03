# Third-party notices

Código copiado de outros projetos entra aqui, uma linha por componente, com projeto, commit, licença e onde foi usado.
Só MIT, BSD, ISC, zlib ou Apache-2.0. Cabeçalhos originais são preservados nos arquivos.

| Componente | Origem e commit | Licença | Usado em |
|---|---|---|---|
| MacNativeGames extractor (leitura de PFS0/HFS0, cabeçalho NCA, tickets comuns, chave AES-CTR, ExeFS com hashes), na forma vendorizada pelo astral-chain-pc-recomp | https://github.com/ly05010419/MacNativeGames @ `b75be8cfa704df3701e86130c8ced268e79d6b11` (`games/totk/scripts/extract_exefs.py`), via https://github.com/captainj-sparrow/astral-chain-pc-recomp @ `3bbaf259ac099a321c78b81f5402f6070a77874a` (`tools/vendor/macnativegames/extract_exefs.py`), Copyright (c) 2026 MacNativeGames contributors | MIT | `tools/nx.py` |
| nxnative: leitura de saídas GLSLC e chave de shader (`sph_stage`, `ctl_len`, `skey`, `check`, `glslc_stage`, `glslc_layout`, `glslc_section`, `glslc_program`, `glslc_shaders`) e descompressão das entradas IDRK (`idrk_data`) | https://github.com/seedds/nxnative @ `3ace3df33b81681cdc9d17bfa48eadaccd446b5c` (`dm/gfx/tools/shader_split.py`), Copyright (c) 2026 seedds | MIT | `tools/census_shaders.py` |
| Astral Chain Recomp: lifter ARM64 → C, gerador, jump tables, flags e registradores locais, NSO, patches, rebaixamento FP/SIMD para C (eles mesmos adaptados do LAS Recomp, MIT, Copyright (c) 2026 Peiikai, com os cabeçalhos mantidos) | https://github.com/captainj-sparrow/astral-chain-pc-recomp @ `3bbaf259ac099a321c78b81f5402f6070a77874a` (`recomp/*.py`), Copyright (c) 2026 os contribuidores do Astral Chain Recomp / TotK Recomp | MIT | `recomp/flags.py`, `recomp/gen.py`, `recomp/jumptables.py`, `recomp/lifter.py`, `recomp/module.py`, `recomp/nso.py`, `recomp/patches.py`, `recomp/regs.py`, `recomp/simd_c.py` (sem mudança); `recomp/layout.py` (sem região fixa de RomFS) |
| Astral Chain Recomp: cabeçalhos de CPU do código gerado e fma de software (o fma vem do musl, MIT) | https://github.com/captainj-sparrow/astral-chain-pc-recomp @ `3bbaf259ac099a321c78b81f5402f6070a77874a` (`runtime/cpu.h`, `runtime/simd.h`, `runtime/simd_fp.h`, `runtime/fma.c`) | MIT | `runtime/cpu.h`, `runtime/simd.h`, `runtime/simd_fp.h`, `runtime/fma.c` (sem mudança) |
| Astral Chain Recomp: testes diferenciais contra Unicorn e checagem de jump tables (adaptados do LAS Recomp) | https://github.com/captainj-sparrow/astral-chain-pc-recomp @ `3bbaf259ac099a321c78b81f5402f6070a77874a` (`tests/diff/`, `tests/jumptables_check.py`, `tests/flags_check.*`, `tests/excl_mt.py`) | MIT | `tests/diff/*`, `tests/jumptables_check.py`, `tests/flags_check.py`, `tests/flags_check.c`, `tests/excl_mt.py` (só o caminho padrão do ExeFS mudou) |
| Astral Chain Recomp: memória livre para dimensionar os workers do gerador | https://github.com/captainj-sparrow/astral-chain-pc-recomp @ `3bbaf259ac099a321c78b81f5402f6070a77874a` (`tools/hostmem.py`) | MIT | `tools/hostmem.py` (sem mudança) |

O código próprio do projeto está sob a [licença MIT](LICENSE). A licença não concede nada sobre o jogo, que pertence
à Nintendo e à Koei Tecmo.

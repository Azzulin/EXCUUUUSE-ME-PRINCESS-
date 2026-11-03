# Third-party notices

Código copiado de outros projetos entra aqui, uma linha por componente, com projeto, commit, licença e onde foi usado.
Só MIT, BSD, ISC, zlib ou Apache-2.0. Cabeçalhos originais são preservados nos arquivos.

| Componente | Origem e commit | Licença | Usado em |
|---|---|---|---|
| MacNativeGames extractor (leitura de PFS0/HFS0, cabeçalho NCA, tickets comuns, chave AES-CTR, ExeFS com hashes), na forma vendorizada pelo astral-chain-pc-recomp | https://github.com/ly05010419/MacNativeGames @ `b75be8cfa704df3701e86130c8ced268e79d6b11` (`games/totk/scripts/extract_exefs.py`), via https://github.com/captainj-sparrow/astral-chain-pc-recomp @ `3bbaf259ac099a321c78b81f5402f6070a77874a` (`tools/vendor/macnativegames/extract_exefs.py`), Copyright (c) 2026 MacNativeGames contributors | MIT | `tools/nx.py` |

O código próprio do projeto está sob a [licença MIT](LICENSE). A licença não concede nada sobre o jogo, que pertence
à Nintendo e à Koei Tecmo.

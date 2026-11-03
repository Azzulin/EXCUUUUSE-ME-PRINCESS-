# recomp/ — lifter ARM64 → C

Vazio de propósito até a Fase 1. Vai receber o `recomp/` do
[astral-chain-pc-recomp](../docs/referencias.md) (MIT, com atribuição em `THIRD_PARTY_NOTICES.md`), adaptado para os
módulos `main`, `subsdk0` e `sdk` do Age of Calamity 1.3.0. Ver [docs/arquitetura.md](../docs/arquitetura.md), seção 2.

Regras:

- O C gerado nunca é editado à mão: muda-se o gerador e gera-se de novo.
- Todo arquivo emitido carrega `GENERATED_MARKER` (definido em `tools/check_content.py`) e vai para `generated/`.
- `layout.py` é o único lugar que decide as bases dos módulos.
- Toda mudança no lifter passa pelos testes diferenciais contra Unicorn.

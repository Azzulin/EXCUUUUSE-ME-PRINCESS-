# recomp/ — lifter ARM64 → C

Trazido do [astral-chain-pc-recomp](../docs/referencias.md) (MIT, atribuição em `THIRD_PARTY_NOTICES.md`), que por
sua vez adaptou o lifter do LAS Recomp. Só `layout.py` mudou: o AoC não tem região fixa de RomFS.

```sh
# gera o C dos três módulos em generated/v130/ (~600 MB, ~3 min em 2 núcleos)
python3 recomp/gen.py --exefs build/v130/exefs --out generated/v130 --modules main,subsdk0,sdk
```

Regras:

- O C gerado nunca é editado à mão: muda-se o gerador e gera-se de novo.
- Todo arquivo emitido carrega `GENERATED_MARKER` (definido em `tools/check_content.py`) e vai para `generated/`.
- `layout.py` é o único lugar que decide as bases dos módulos.
- Toda mudança no lifter passa pelos testes diferenciais contra Unicorn (`tests/diff/`, `tests/jumptables_check.py`).
  Dependências de teste: `pip install numpy lz4 capstone unicorn`.

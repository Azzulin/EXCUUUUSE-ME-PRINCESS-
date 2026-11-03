#!/usr/bin/env python3
"""Fase 0: identifica e extrai o dump de Age of Calamity para build/ (ignorado pelo git).

Subcomandos:
    inventory  lista os pacotes (base, update, DLCs) achados em --game-dir, pelo conteúdo dos NCAs
    romfs-list lista os arquivos do RomFS da base e dos DLCs (só metadados) e grava build/v130/romfs-*.tsv
    romfs-index lista build/v130/romfs.bin (RomFS 1.3.0 mesclado) em romfs-v130.tsv e compara com a base
    hactool-home  prepara build/v130/tmp/hactool-home/.switch/{prod,title}.keys para o hactool mesclar o
               update (BKTR): title keys tiradas dos tickets dos NSPs; prod.keys sem comentários e com o
               NUL extra do Lockpick removido. Usado por tools/windows/merge_romfs.ps1.
    exefs      extrai o ExeFS do update 1.3.0 (ou da base, com --base-only) para build/v130/exefs/,
               verificando cada bloco pela tabela de hashes, e grava um manifesto com SHA-256

Exemplo (a partir da raiz do repositório):
    python3 tools/extract.py inventory --game-dir "Game Files" --keys "Game Files/prod.keys"
    python3 tools/extract.py exefs     --game-dir "Game Files" --keys "Game Files/prod.keys"

Lê os arquivos no lugar (não copia o NCA de 10 GB). As chaves ficam só em memória e nunca são impressas.
O mesclar do RomFS da base com o update (BKTR) vem num passo seguinte.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE_TID = "01002B00111A2000"
UPDATE_TID = "01002B00111A2800"
DLC_PREFIX = "01002B00111A3"


def scan(game_dir: Path, keys: dict) -> list[dict]:
    found = []
    for path in sorted(p for p in game_dir.rglob("*") if p.suffix.lower() in (".nsp", ".xci")):
        with path.open("rb") as f:
            kind, entries = nx.container_entries(f, path.stat().st_size)
            tickets = nx.common_tickets(f, entries)
            ncas = nx.nca_inventory(f, entries, keys)
        meta = [n for n in ncas if n.content_type == 1]
        package_tid = meta[0].title_id if meta else (ncas[0].title_id if ncas else "?")
        if package_tid == BASE_TID:
            role = "base"
        elif package_tid == UPDATE_TID:
            role = "update"
        elif package_tid.startswith(DLC_PREFIX):
            role = "dlc"
        else:
            role = "outro"
        found.append({"path": path, "container": kind, "role": role, "title_id": package_tid,
                      "ncas": ncas, "tickets": len(tickets)})
    return found


def describe(pkgs: list[dict]) -> None:
    for p in pkgs:
        print(f"[{p['role']:6s}] {p['title_id']}  {p['path'].name}")
        for n in p["ncas"]:
            secs = ", ".join(f"{i}:{n.section_kind(i)}" for i in n.sections())
            print(f"         {n.content_name:10s} {n.size / 2**20:10.1f} MiB  keygen 0x{n.key_generation:02x}"
                  f"  sdk {n.sdk_version:8s} seções [{secs}]")


def cmd_inventory(args, keys) -> int:
    pkgs = scan(args.game_dir, keys)
    describe(pkgs)
    roles = [p["role"] for p in pkgs]
    problems = []
    if roles.count("base") != 1:
        problems.append(f"esperada 1 base, achei {roles.count('base')}")
    if roles.count("update") != 1:
        problems.append(f"esperado 1 update, achei {roles.count('update')}")
    for msg in problems:
        print("PROBLEMA:", msg)
    return 1 if problems else 0


def cmd_exefs(args, keys) -> int:
    pkgs = scan(args.game_dir, keys)
    role = "base" if args.base_only else "update"
    chosen = [p for p in pkgs if p["role"] == role]
    nx.require(len(chosen) == 1, f"esperado exatamente 1 pacote '{role}' em {args.game_dir}")
    pkg = chosen[0]
    out = args.work / "exefs"
    nx.require(not out.exists() or args.force, f"{out} já existe (use --force para refazer)")
    with pkg["path"].open("rb") as f:
        _, entries = nx.container_entries(f, pkg["path"].stat().st_size)
        tickets = nx.common_tickets(f, entries)
        programs = [n for n in nx.nca_inventory(f, entries, keys) if n.content_type == 0]
        nx.require(len(programs) == 1, "esperado 1 NCA de programa")
        nca = programs[0]
        nx.require(nca.title_id == BASE_TID, f"NCA de programa de outro jogo ({nca.title_id})")
        files = nx.read_exefs(f, nca, nx.nca_ctr_key(nca, keys, tickets))
    out.mkdir(parents=True, exist_ok=True)
    listing = []
    for name, data in files:
        (out / name).write_bytes(data)
        listing.append({"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        print(f"  {name:10s} {len(data):>10d} B")
    manifest = {"source": pkg["path"].name, "role": role, "program_nca": nca.name, "sdk": nca.sdk_version,
                "key_generation": nca.key_generation,
                "integrity": "FS header, tabela de hashes e todos os blocos do ExeFS verificados; assinaturas RSA não",
                "files": listing}
    (args.work / "exefs-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"ExeFS em {out}")
    return 0


def cmd_romfs_list(args, keys) -> int:
    from collections import Counter
    pkgs = [p for p in scan(args.game_dir, keys) if p["role"] in ("base", "dlc")]
    args.work.mkdir(parents=True, exist_ok=True)
    for pkg in pkgs:
        with pkg["path"].open("rb") as f:
            _, entries = nx.container_entries(f, pkg["path"].stat().st_size)
            tickets = nx.common_tickets(f, entries)
            for nca in nx.nca_inventory(f, entries, keys):
                if nca.content_type not in (0, 5):
                    continue
                key = nx.nca_ctr_key(nca, keys, tickets)
                for i in nca.sections():
                    if nca.section_kind(i) != "romfs":
                        continue
                    files = nx.romfs_files(nx.SectionReader(f, nca, i, key))
                    tsv = args.work / f"romfs-{nca.title_id}.tsv"
                    tsv.write_text("".join(f"{size}\t{path}\n" for path, _o, size in files), encoding="utf-8")
                    total = sum(s for _p, _o, s in files)
                    kinds = Counter()
                    for path, _o, size in files:
                        base = path.rsplit("/", 1)[-1]
                        k = ("rdb-dlc" if ".rdb.bin3_" in base else "rdb-index" if base.endswith(".rdb")
                             else "rdb-data" if ".rdb.bin" in base else "rdb-file" if base.endswith(".file")
                             else base.rsplit(".", 1)[-1] if "." in base else "(sem ext)")
                        kinds[k] += size
                    print(f"[{pkg['role']}] {nca.title_id}: {len(files)} arquivos, {total / 2**30:.2f} GiB  → {tsv.name}")
                    for k, v in kinds.most_common(8):
                        print(f"      {k:12s} {v / 2**20:10.1f} MiB")
    return 0


def cmd_romfs_index(args, keys) -> int:
    image = args.work / "romfs.bin"
    with image.open("rb") as f:
        files = nx.romfs_image_files(f)
    (args.work / "romfs-v130.tsv").write_text("".join(f"{s}\t{p}\n" for p, _o, s in files), encoding="utf-8")
    base_tsv = args.work / f"romfs-{BASE_TID}.tsv"
    base = {}
    if base_tsv.exists():
        for line in base_tsv.read_text(encoding="utf-8").splitlines():
            size, path = line.split("\t", 1)
            base[path] = int(size)
    new = {p: s for p, _o, s in files}
    added = sorted(set(new) - set(base))
    removed = sorted(set(base) - set(new))
    changed = sorted(p for p in set(new) & set(base) if new[p] != base[p])
    total = sum(new.values())
    print(f"RomFS 1.3.0: {len(files)} arquivos, {total / 2**30:.2f} GiB (imagem {image.stat().st_size / 2**30:.2f} GiB)")
    if base:
        print(f"em relação à base 1.0.0: {len(added)} novos, {len(removed)} removidos, {len(changed)} com tamanho diferente")
        for label, items in (("novo", added), ("removido", removed), ("mudou", changed)):
            for path in items[:15]:
                print(f"   {label:8s} {path}  {base.get(path, 0) / 2**20:.1f} → {new.get(path, 0) / 2**20:.1f} MiB")
    return 0


def cmd_hactool_home(args, keys) -> int:
    import os
    import re
    tickets: dict[bytes, bytes] = {}
    for pkg in scan(args.game_dir, keys):
        if pkg["role"] not in ("base", "update"):
            continue
        with pkg["path"].open("rb") as f:
            _, entries = nx.container_entries(f, pkg["path"].stat().st_size)
            tickets.update(nx.common_tickets(f, entries))
    home = args.work / "tmp" / "hactool-home" / ".switch"
    home.mkdir(parents=True, exist_ok=True)
    lines = []
    for line in args.keys.read_text(encoding="utf-8", errors="replace").splitlines():
        body = line.split("#", 1)[0]
        if "=" not in body:
            continue
        name, value = (part.strip() for part in body.split("=", 1))
        if re.fullmatch(r"(?:mariko_)?master_kek_source_[0-9a-f]{2}", name.lower()) and len(value) == 34 \
                and value[-2:] == "00":
            value = value[:32]
        lines.append(f"{name} = {value}")
    for name, text in (("prod.keys", "\n".join(lines) + "\n"),
                       ("title.keys", "".join(f"{r.hex()} = {k.hex()}\n" for r, k in tickets.items()))):
        target = home / name
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as out:
            out.write(text)
    print(f"hactool-home pronto em {home.parent} ({len(lines)} chaves, {len(tickets)} title keys; valores não exibidos)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("inventory", "exefs", "romfs-list", "romfs-index", "hactool-home"))
    ap.add_argument("--game-dir", type=Path, default=ROOT / "Game Files")
    ap.add_argument("--keys", type=Path, default=ROOT / "Game Files" / "prod.keys")
    ap.add_argument("--work", type=Path, default=ROOT / "build" / "v130")
    ap.add_argument("--base-only", action="store_true", help="ExeFS da base 1.0.0 em vez do update")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    keys = nx.load_keys(args.keys)
    if args.command == "inventory":
        return cmd_inventory(args, keys)
    if args.command == "romfs-list":
        return cmd_romfs_list(args, keys)
    if args.command == "romfs-index":
        return cmd_romfs_index(args, keys)
    if args.command == "hactool-home":
        return cmd_hactool_home(args, keys)
    return cmd_exefs(args, keys)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as e:
        print("ERRO:", e)
        sys.exit(1)

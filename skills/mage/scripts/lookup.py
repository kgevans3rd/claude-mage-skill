#!/usr/bin/env python3
"""
lookup.py — query any table the module carries, and report what is loaded.

The other scripts wrap specific rules. This is the general door: it prints any
cited table, searches across all of them, and — with --status — says exactly
which rulebook values exist on this machine and where they came from.

    python3 lookup.py --status
    python3 lookup.py --list
    python3 lookup.py firearms
    python3 lookup.py --search paradox
    python3 lookup.py spheres --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap  # noqa: E402


def schema(mod=None):
    mod = mod or _bootstrap.module_dir()
    return json.loads((mod / "schema.json").read_text(encoding="utf-8"))


def all_specs():
    """[(table_id, spec, module name, book title)] across core and supplements."""
    out = []
    core = schema()
    for spec in core["tables"]:
        out.append((spec["id"], spec, _bootstrap.CORE, core["source"]["title"]))
    for name, mod in _bootstrap.supplement_dirs():
        sch = schema(mod)
        prefix = sch.get("system") or name
        for spec in sch["tables"]:
            out.append((f"{prefix}:{spec['id']}", spec, name, sch["source"]["title"]))
    return out


def headers_for(tid):
    for full, spec, _mod, _title in all_specs():
        if full == tid:
            return [c["name"] for c in spec["columns"]], spec
    return None, None


def show(tid, rows, heads):
    w = [max(len(h), max((len(str(r[i])) for r in rows), default=0))
         for i, h in enumerate(heads)]
    print("  ".join(h.ljust(w[i]) for i, h in enumerate(heads)))
    print("  ".join("-" * x for x in w))
    for r in rows:
        print("  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("table", nargs="?")
    ap.add_argument("--list", action="store_true", help="table ids and titles")
    ap.add_argument("--status", action="store_true", help="what is loaded, and from where")
    ap.add_argument("--search", help="find rows containing this text, across every table")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    have = set(_bootstrap.registry())

    if args.status:
        specs = all_specs()
        books = {}
        for full, spec, mod, title in specs:
            b = books.setdefault(mod, {"title": title, "cited": 0, "filled": 0, "missing": []})
            b["cited"] += 1
            if full in have:
                b["filled"] += 1
            else:
                b["missing"].append(full)
        for mod in _bootstrap.SUPPLEMENTS:
            if mod not in books:
                books[mod] = {"title": "(module not installed)", "cited": 0,
                              "filled": 0, "missing": []}
        if args.json:
            print(json.dumps(books, indent=2))
            return 0
        total_c = sum(b["cited"] for b in books.values())
        total_f = sum(b["filled"] for b in books.values())
        for mod, b in books.items():
            mark = "ok " if b["cited"] and b["filled"] == b["cited"] else "   "
            print(f"{mark}{mod:<16}{b['filled']:>3}/{b['cited']:<3} {b['title']}")
            for m in b["missing"]:
                print(f"      missing: {m}")
        print(f"\n{total_f}/{total_c} cited tables have values.")
        if total_f < total_c:
            print("\nFill a module from your own copy:")
            print("  python3 tools/fill_tables.py --module <dir> --pdf /path/to/book.pdf")
        else:
            print("Scripts can quote every book that is installed.")
        if "bookofshadows" not in books or not books["bookofshadows"]["filled"]:
            print("\nNote: Merits and Flaws are NOT in the core rulebook. They are in\n"
                  "The Book of Shadows; without that module they are unavailable.")
        return 0

    if args.list:
        cur = None
        for full, spec, mod, _title in all_specs():
            if mod != cur:
                cur = mod
                print(f"\n{mod}")
            mark = " " if full in have else "!"
            pages = spec.get("page_range") or spec.get("page")
            print(f" {mark} {full:<28}{spec['title']}  (p.{pages})")
        return 0

    if args.search:
        needle = args.search.lower()
        hits = 0
        for full, spec, _mod, _title in all_specs():
            if full not in have:
                continue
            rows = [r for r in _bootstrap.get(full)
                    if any(needle in str(c).lower() for c in r)]
            if rows:
                heads = [c["name"] for c in spec["columns"]]
                pages = spec.get("page_range") or spec.get("page")
                print(f"\n── {full}  ({spec['title']}, p.{pages})")
                show(full, rows, heads)
                hits += len(rows)
        print(f"\n{hits} row(s) matching {args.search!r}.")
        return 0 if hits else 1

    if not args.table:
        ap.print_help()
        return 2

    heads, spec = headers_for(args.table)
    if heads is None:
        print(f"error: no table {args.table!r}. Try --list.", file=sys.stderr)
        return 2
    rows = _bootstrap.get(args.table)
    if args.json:
        print(json.dumps([dict(zip(heads, r)) for r in rows], indent=2))
        return 0
    print(f"{spec['title']}  —  p.{spec.get('page_range') or spec.get('page')}\n")
    show(args.table, rows, heads)
    if spec.get("note"):
        print(f"\nnote: {spec['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(_bootstrap.run(main))

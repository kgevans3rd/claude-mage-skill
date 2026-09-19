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


def schema():
    return json.loads((_bootstrap.module_dir() / "schema.json").read_text(encoding="utf-8"))


def headers_for(tid, sch):
    for t in sch["tables"]:
        if t["id"] == tid:
            return [c["name"] for c in t["columns"]], t
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

    T = _bootstrap.tables()
    sch = schema()
    have = set(T.available())

    if args.status:
        cited = [t["id"] for t in sch["tables"]]
        missing = [t for t in cited if t not in have]
        src = sch["source"]
        info = {
            "module": str(_bootstrap.module_dir()),
            "book": f"{src['title']} ({src.get('edition')})",
            "page_offset": src.get("page_offset"),
            "text_layer": src.get("text_layer"),
            "store": T.source_note(),
            "cited": len(cited), "filled": len(have), "missing": missing,
        }
        if args.json:
            print(json.dumps(info, indent=2))
            return 0
        print(f"module    {info['module']}")
        print(f"book      {info['book']}")
        print(f"store     {info['store']}")
        print(f"tables    {info['filled']}/{info['cited']} filled")
        if missing:
            print(f"missing   {', '.join(missing)}")
            print("\nFill them from your own copy:")
            print(f"  python3 tools/fill_tables.py --module {_bootstrap.module_dir()} "
                  f"--pdf /path/to/rulebook.pdf")
        else:
            print("\nEvery cited table has a value. Scripts can quote the book.")
        return 0

    if args.list:
        for t in sch["tables"]:
            mark = " " if t["id"] in have else "!"
            print(f"{mark} {t['id']:<26}{t['title']}  (p.{t.get('page')})")
        return 0

    if args.search:
        needle = args.search.lower()
        hits = 0
        for t in sch["tables"]:
            if t["id"] not in have:
                continue
            rows = [r for r in T.get(t["id"])
                    if any(needle in str(c).lower() for c in r)]
            if rows:
                heads = [c["name"] for c in t["columns"]]
                print(f"\n── {t['id']}  ({t['title']}, p.{t.get('page')})")
                show(t["id"], rows, heads)
                hits += len(rows)
        print(f"\n{hits} row(s) matching {args.search!r}.")
        return 0 if hits else 1

    if not args.table:
        ap.print_help()
        return 2

    heads, spec = headers_for(args.table, sch)
    if heads is None:
        print(f"error: no table {args.table!r}. Try --list.", file=sys.stderr)
        return 2
    rows = T.get(args.table)
    if args.json:
        print(json.dumps([dict(zip(heads, r)) for r in rows], indent=2))
        return 0
    print(f"{spec['title']}  —  {sch['source']['title']}, p.{spec.get('page')}\n")
    show(args.table, rows, heads)
    if spec.get("note"):
        print(f"\nnote: {spec['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(_bootstrap.run(main))

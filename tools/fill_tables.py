#!/usr/bin/env python3
"""
fill_tables.py — write a module's tables.local.json from a validated extraction.

byo-rulebook's extract.py validates and reports; it deliberately stops short of
writing ("Nothing is written to the module until every table is OK"). The
runtime side, toolkit/tables.py, then reads tables.local.json. This is the step
between them: it runs extract.py's own pipeline, refuses unless every table came
back OK, and writes the store.

It is a separate file rather than a patch to extract.py because the toolkit is a
checkout that should stay pullable — a local edit there is a merge conflict
waiting to happen.

    python3 tools/fill_tables.py --module mage2e --pdf ~/books/rulebook.pdf
    python3 tools/fill_tables.py --module mage2e --pdf BOOK.pdf --force

--force writes despite failures, for the case where you want the OK tables
available while you work on the rest. Failed tables are omitted, never
half-written: a partly-filled table is a wrong table.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def find_toolkit(module_dir: Path) -> Path:
    """$GM_TOOLKIT, then <module>/.toolkit, then <module>/../_toolkit."""
    env = os.environ.get("GM_TOOLKIT", "").strip()
    tried = []
    if env:
        p = Path(env).expanduser()
        tried.append(f"$GM_TOOLKIT={p}")
        if (p / "toolkit" / "extract.py").is_file():
            return p / "toolkit"
        if (p / "extract.py").is_file():
            return p

    pointer = module_dir / ".toolkit"
    tried.append(str(pointer))
    if pointer.is_file():
        p = Path(pointer.read_text(encoding="utf-8").strip()).expanduser()
        if (p / "toolkit" / "extract.py").is_file():
            return p / "toolkit"
        if (p / "extract.py").is_file():
            return p

    sibling = module_dir.parent / "_toolkit"
    tried.append(str(sibling))
    if (sibling / "toolkit" / "extract.py").is_file():
        return sibling / "toolkit"

    sys.exit(
        "error: could not locate the byo-rulebook toolkit. Tried:\n  "
        + "\n  ".join(tried)
        + "\n\nInstall it with:\n"
        "  git clone https://github.com/kgevans3rd/byo-rulebook.git "
        f"{module_dir.parent / '_toolkit'}\n"
        "or set $GM_TOOLKIT to an existing checkout."
    )


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module", required=True, type=Path)
    ap.add_argument("--pdf", required=True, type=Path,
                    help="your own copy of the rulebook (.pdf, or .txt if already converted)")
    ap.add_argument("--out", type=Path, default=None,
                    help="override the output path (default: <module>/tables.local.json)")
    ap.add_argument("--force", action="store_true",
                    help="write the OK tables even if others failed")
    args = ap.parse_args()

    module_dir = args.module.resolve()
    if not (module_dir / "schema.json").is_file():
        sys.exit(f"error: no schema.json in {module_dir}")
    if not args.pdf.is_file():
        sys.exit(f"error: no such file: {args.pdf}")

    tk = find_toolkit(module_dir)
    sys.path.insert(0, str(tk))
    extract = load_module(tk / "extract.py", "byo_extract")

    schema = json.loads((module_dir / "schema.json").read_text(encoding="utf-8"))
    text = extract.ocr.normalise_text(extract.load_source_text(args.pdf))
    lines = text.splitlines()
    corrections = extract.load_corrections(module_dir)
    results = [extract.extract_table(lines, s, corrections) for s in schema["tables"]]

    ok = [r for r in results if r["status"] == extract.OK]
    bad = [r for r in results if r["status"] != extract.OK]

    for r in bad:
        first = r["problems"][0] if r["problems"] else r["status"]
        print(f"  not written: {r['id']:<26} {r['status']:<12} {first}", file=sys.stderr)

    if bad and not args.force:
        print(f"\n{len(bad)} table(s) did not validate; nothing written. "
              f"Fix them, or re-run with --force to store the {len(ok)} that did.",
              file=sys.stderr)
        return 1

    out = args.out or (module_dir / "tables.local.json")
    doc = {
        "_source": f"{schema['source']['title']} ({schema['source'].get('edition', '?')})"
                   f" via {args.pdf.name}",
        "_generated": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "_schema_version": schema.get("schema_version"),
        "_note": "Generated from the reader's own rulebook. Not for redistribution.",
        "tables": {r["id"]: r["rows"] for r in ok},
    }
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = sum(len(r["rows"]) for r in ok)
    print(f"wrote {out}: {len(ok)} tables, {rows} rows")
    if bad:
        print(f"({len(bad)} table(s) omitted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
extract_headed_entries.py — pull "Name (N pt Merit)" entries out of a text layer.

byo-rulebook's four parsers read tables: a heading, then rows beneath it. Some
books do not print their Merits and Flaws as a table at all — each entry is a
*heading* of its own, with a paragraph under it, spread over a whole chapter.
There is no anchor to walk down from, so none of the shipped parsers apply.

This is the missing shape. It lives here rather than in the toolkit because the
toolkit is a checkout that should stay pullable; a local edit there is a merge
conflict waiting to happen.

What the scan does to these headings, all of it seen in the reference book:

    Confidence (2 pt Merit)     preceded by a form feed, so ^ never matches
    Unobtrusive (I pt Merit)    the 1 read as a capital I
    Rose-Colored Mirrorshades   name and cost split across two lines
    (2 pt Flaw)
    Mr. tied Tape (4 pt Flaw)   "Red" misread as "tied" — prose corruption,
                                which no cell type can catch

The cost is coerced against the toolkit's `int` type, so "I pt" is repaired and
reported rather than silently accepted. Name corruption is not repairable here
and is left for a human; --report lists every entry so it can be eyeballed.

    python3 tools/extract_headed_entries.py --pdf BOOK.pdf --report
    python3 tools/extract_headed_entries.py --pdf BOOK.pdf --module technocracy \
        --table merits_flaws --out technocracy/corrections.local.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_toolkit(start: Path) -> Path:
    env = os.environ.get("GM_TOOLKIT", "").strip()
    cands = []
    if env:
        cands += [Path(env).expanduser() / "toolkit", Path(env).expanduser()]
    cands += [start / "_toolkit" / "toolkit", start / "_toolkit"]
    for c in cands:
        if (c / "ocr.py").is_file():
            return c
    sys.exit("error: could not find the byo-rulebook toolkit (set $GM_TOOLKIT or clone it to _toolkit/)")


TYPES = r"(?P<type>Merits?|Flaws?)"
COST = r"(?P<cost>[0-9IlOo]+(?:\s*-\s*[0-9IlOo]+)?)"
UNIT = r"(?:pt|pts|point|points)\.?"
NAME = r"(?P<name>[A-Z][A-Za-z0-9'’,.&/ -]{1,44}?)"

RE_ONE_LINE = re.compile(rf"^{NAME}\s*\(\s*{COST}\s*{UNIT}\s*{TYPES}\s*\)\s*$")
RE_COST_ONLY = re.compile(rf"^\(\s*{COST}\s*{UNIT}\s*{TYPES}\s*\)\s*$")
RE_NAME_ONLY = re.compile(r"^[A-Z][A-Za-z0-9'’,.&/ -]{1,44}$")
RE_PAGE = re.compile(r"^\s*(\d{1,3})\s*$")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--module", type=Path, help="module dir, for resolving the toolkit")
    ap.add_argument("--table", default="merits_flaws", help="table id to write under")
    ap.add_argument("--out", type=Path, help="corrections file to write")
    ap.add_argument("--report", action="store_true", help="print what was found and stop")
    ap.add_argument("--category", default="", help="value for the category column")
    args = ap.parse_args()

    root = (args.module.resolve().parent if args.module else HERE.parent)
    tk = find_toolkit(root)
    sys.path.insert(0, str(tk))
    import ocr  # noqa: E402
    import extract as EX  # noqa: E402

    raw = EX.load_source_text(args.pdf)
    # Form feeds glue a page break onto the first heading of the next page,
    # which defeats the ^ anchor. They carry the page number with them, so
    # split rather than strip.
    text = ocr.normalise_text(raw.replace("\f", "\n"))
    lines = [ln.rstrip() for ln in text.splitlines()]

    found, page, repairs, warnings = [], None, [], []
    for i, ln in enumerate(lines):
        s = ln.strip()
        m = RE_PAGE.match(s)
        if m:
            page = int(m.group(1))
            continue

        name = cost = typ = None
        m = RE_ONE_LINE.match(s)
        if m:
            name, cost, typ = m.group("name").strip(), m.group("cost"), m.group("type")
        else:
            m = RE_COST_ONLY.match(s)
            if m:
                prev = lines[i - 1].strip() if i else ""
                if RE_NAME_ONLY.match(prev):
                    name, cost, typ = prev, m.group("cost"), m.group("type")
                    warnings.append(f"{prev!r}: name and cost were on separate lines")
        if not name:
            continue

        lo, _, hi = cost.partition("-")
        parts, shown = [], []
        for part in ([lo, hi] if hi else [lo]):
            cell = ocr.coerce(part.strip(), "int")
            if not cell.ok:
                warnings.append(f"{name!r}: could not read cost {part!r}")
                shown = None
                break
            if cell.confidence == ocr.REPAIRED:
                repairs.append(f"{name}: cost {part!r} -> {cell.value}")
            shown.append(str(cell.value))
        if shown is None:
            continue

        found.append({"name": name, "cost": "-".join(shown),
                      "type": typ.rstrip("s").title(), "page": page,
                      "category": args.category})

    seen, uniq = set(), []
    for e in found:
        if e["name"].lower() in seen:
            warnings.append(f"{e['name']!r}: duplicate heading, kept the first")
            continue
        seen.add(e["name"].lower())
        uniq.append(e)

    if args.report or not args.out:
        for e in uniq:
            print(f"  p.{str(e['page'] or '?'):>4}  {e['name']:<34}{e['cost']:>5} pt {e['type']}")
        print(f"\n{len(uniq)} entries")
        if repairs:
            print("\nOCR repairs (confirm each):")
            for r in repairs:
                print(f"  ~ {r}")
        if warnings:
            print("\nwarnings:")
            for w in warnings:
                print(f"  ! {w}")
        if not args.out:
            return 0

    doc = {}
    if args.out.is_file():
        doc = json.loads(args.out.read_text(encoding="utf-8"))
    doc.setdefault("_note", "Machine-extracted from the owner's own PDF. Not for redistribution.")
    doc[args.table] = {
        "_source": f"{args.pdf.name}, extracted by tools/extract_headed_entries.py",
        "_note": "Costs coerced against the toolkit's int type; every repair is listed in _repairs.",
        "_repairs": repairs,
        "_warnings": warnings,
        "row_adds": [{"row": {k: str(e[k]) for k in ("name", "cost", "type", "category")}}
                     for e in uniq],
    }
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out}: {len(uniq)} rows under {args.table!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

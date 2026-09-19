#!/usr/bin/env python3
"""
render_pages.py — render the pages a module cites, as images to read by eye.

byo-rulebook's extractors read a PDF's text layer. This book has none: it is a
2003 Acrobat "Image Conversion" scan, and pdftotext over all 314 pages returns
zero characters. There is nothing to parse, so every table in this module is
declared `manual` and its values were entered by reading the page.

This is the tool for doing that reading, and for checking it later. It renders
exactly the pages schema.json cites, applying the module's page_offset, so you
can put the chart next to the values and confirm them.

    python3 tools/render_pages.py --module mage2e --pdf BOOK.pdf --all
    python3 tools/render_pages.py --module mage2e --pdf BOOK.pdf --table firearms
    python3 tools/render_pages.py --module mage2e --pdf BOOK.pdf --printed 262 --dpi 300

Needs poppler's pdftoppm. Output goes to --out (default: ./page-renders),
which the repository ignores — rendered pages are the book.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module", required=True, type=Path)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path("page-renders"))
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--table", action="append", default=[],
                    help="render only the page(s) this table id cites (repeatable)")
    ap.add_argument("--printed", action="append", type=int, default=[],
                    help="render a printed page number directly (repeatable)")
    ap.add_argument("--all", action="store_true", help="every cited page")
    args = ap.parse_args()

    if not shutil.which("pdftoppm"):
        sys.exit("error: need poppler's pdftoppm (apt install poppler-utils)")
    schema_path = args.module / "schema.json"
    if not schema_path.is_file():
        sys.exit(f"error: no schema.json in {args.module}")
    if not args.pdf.is_file():
        sys.exit(f"error: no such file: {args.pdf}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    offset = schema["source"].get("page_offset", 0)
    by_id = {t["id"]: t for t in schema["tables"]}

    wanted = {}          # printed page -> [table ids]
    if args.all or not (args.table or args.printed):
        for t in schema["tables"]:
            if t.get("page"):
                wanted.setdefault(t["page"], []).append(t["id"])
    for tid in args.table:
        if tid not in by_id:
            sys.exit(f"error: no table {tid!r}. Known: {', '.join(sorted(by_id))}")
        p = by_id[tid].get("page")
        if p:
            wanted.setdefault(p, []).append(tid)
    for p in args.printed:
        wanted.setdefault(p, []).append("(explicit)")

    args.out.mkdir(parents=True, exist_ok=True)
    for printed in sorted(wanted):
        pdf_page = printed + offset
        stem = args.out / f"p{printed:03d}_pdf{pdf_page:03d}"
        subprocess.run(
            ["pdftoppm", "-f", str(pdf_page), "-l", str(pdf_page), "-r", str(args.dpi),
             "-png", "-singlefile", str(args.pdf), str(stem)],
            check=True)
        print(f"{stem}.png   printed p.{printed} = PDF p.{pdf_page}   "
              f"[{', '.join(sorted(set(wanted[printed])))}]")

    print(f"\n{len(wanted)} page(s) rendered at {args.dpi} dpi into {args.out}/")
    print("These are pages of the book. Keep them out of version control.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

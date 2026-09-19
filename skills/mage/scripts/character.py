#!/usr/bin/env python3
"""
character.py — creation, validation and advancement for Mage 2nd Edition mages.

Creation, as the chart lays it out:

    Attributes   7/5/3 across Physical, Social, Mental, on top of the one free
                 dot every Attribute starts with
    Abilities    13/9/5 across Talents, Skills, Knowledges; none above 3 yet
    Backgrounds  7 dots
    Spheres      5 dots, plus a free dot in the Tradition's specialty Sphere
    Arete 1, Willpower 5, then 15 freebie points

Costs come from the module's freebie and experience tables, so a module filled
from a different printing changes the sums here without touching this file.

    python3 character.py steps
    python3 character.py traditions
    python3 character.py costs --freebie
    python3 character.py validate --file mage.json
    python3 character.py cost --trait Arete --current 2 --xp
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap  # noqa: E402

ATTRIBUTE_SPREAD = (7, 5, 3)
ABILITY_SPREAD = (13, 9, 5)
BACKGROUND_DOTS = 7
SPHERE_DOTS = 5
STARTING_ARETE = 1
STARTING_WILLPOWER = 5
FREEBIE_POINTS = 15
CREATION_ABILITY_CAP = 3
MAX_FLAW_POINTS = 7          # Book of Shadows p.30
MAX_FREEBIES = FREEBIE_POINTS + MAX_FLAW_POINTS
ATTRIBUTE_FLOOR = 1          # every Attribute starts with one free dot


def _rows(tid):
    return _bootstrap.get(tid)


def tradition_sphere(name):
    for t, s in _rows("traditions"):
        if t.lower() == name.lower():
            return s
    names = ", ".join(t for t, _ in _rows("traditions"))
    raise SystemExit(f"error: no Tradition {name!r}. Known: {names}")


def _cost_of(tid, trait, current=None):
    """Turn a cost cell ('5 per dot', 'current rating x 4') into a number."""
    for name, cell in _rows(tid):
        if name.lower() != trait.lower():
            continue
        c = cell.lower()
        m = re.match(r"^(\d+)\s+per dot$", c)
        if m:
            return int(m.group(1)), cell
        if c.startswith("current rating"):
            if current is None:
                raise SystemExit(f"error: {trait} costs '{cell}'; pass --current")
            mult = re.search(r"x\s*(\d+)", c)
            return current * (int(mult.group(1)) if mult else 1), cell
        m = re.match(r"^(\d+)$", c)
        if m:
            return int(m.group(1)), cell
        m = re.match(r"^(\d+) point per (\w+) dots$", c)
        if m:
            return None, cell           # priced per block, not per dot
        return None, cell
    names = ", ".join(n for n, _ in _rows(tid))
    raise SystemExit(f"error: no {trait!r} in that cost table. Known: {names}")



# ── Merits and Flaws ──────────────────────────────────────────────────────
# These are not in the core rulebook; they come from the supplements, so they
# are addressed through their namespaced ids and are simply absent if the
# reader has not filled those modules.

MF_TABLES = {"bos": "bos:merits_flaws", "tech": "tech:merits_flaws"}

# Pairs the books declare incompatible, stated inline in the prose rather than
# in any chart, so they are listed here rather than read from a table.
EXCLUSIONS = [
    ("Concentration", "Absent-Minded"),
    ("Reputation", "Notoriety"),
    ("Acute Senses", "Hard of Hearing"),
    ("Acute Senses", "Bad Sight"),
    ("Double-Jointed", "Lame"),
    ("Double-Jointed", "Paraplegic"),
    ("Ambidextrous", "One Arm"),
    ("Higher Purpose", "Driving Goal"),
]


def merits_flaws(book="all"):
    """[(name, cost, type, category, book)] from whichever supplements exist."""
    out = []
    for key, tid in MF_TABLES.items():
        if book not in ("all", key):
            continue
        try:
            rows = _bootstrap.get(tid)
        except Exception as exc:                      # noqa: BLE001
            if type(exc).__name__ != "TableUnavailable":
                raise
            continue
        out += [(r[0], r[1], r[2], r[3], key) for r in rows]
    if not out:
        raise SystemExit(
            "error: no Merits and Flaws are available. They are not in the core\n"
            "rulebook — fill the bookofshadows module from your own copy of\n"
            "The Book of Shadows, or the technocracy module from Guide to the Technocracy.")
    return out


def cost_bounds(cost):
    """'3' -> (3, 3); '1-5' -> (1, 5); anything odd -> (None, None)."""
    m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", cost or "")
    if not m:
        return (None, None)
    lo = int(m.group(1))
    return (lo, int(m.group(2)) if m.group(2) else lo)


BOOK_NAMES = {"bos": "Book of Shadows", "tech": "Guide to the Technocracy"}
BOOK_PRIORITY = ("bos", "tech")     # the general list wins a name clash


def _catalog():
    """({name_lower: row}, {name_lower: "where it appears"}).

    Several names appear in both supplements at different costs — Acute Senses
    is 1 point in the players guide and 1-3 in the Technocracy book. Letting
    whichever loaded last win would hand a Verbena the Technocracy's price
    without saying so, which is precisely the silent-wrong-rule failure this
    whole design is built to avoid. So the general list wins, and any clash is
    reported rather than resolved quietly.
    """
    by_name = {}
    for row in merits_flaws("all"):
        by_name.setdefault(row[0].lower(), []).append(row)
    catalog, ambiguous = {}, {}
    for key, rows in by_name.items():
        rows.sort(key=lambda r: BOOK_PRIORITY.index(r[4])
                  if r[4] in BOOK_PRIORITY else len(BOOK_PRIORITY))
        catalog[key] = rows[0]
        if len(rows) > 1:
            ambiguous[key] = ", ".join(
                f"{BOOK_NAMES.get(r[4], r[4])} {r[1]}pt" for r in rows)
    return catalog, ambiguous


def cmd_merits(args):
    want = "Flaw" if args.cmd == "flaws" else "Merit"
    rows = [r for r in merits_flaws(args.book)
            if want in r[2]]
    if args.category:
        rows = [r for r in rows if args.category.lower() in r[3].lower()]
    if args.name:
        rows = [r for r in rows if args.name.lower() in r[0].lower()]
    rows.sort(key=lambda r: (r[3], cost_bounds(r[1])[0] or 99, r[0]))
    if args.json:
        print(json.dumps([{"name": n, "cost": c, "type": t, "category": g, "book": b}
                          for n, c, t, g, b in rows], indent=2))
        return 0
    if not rows:
        print("nothing matched")
        return 1
    cat = None
    for n, c, t, g, b in rows:
        if g != cat:
            cat = g
            print(f"\n{g}")
        tag = "" if b == "bos" else f"  [{b}]"
        dual = "  (may be taken as either)" if t == "Merit or Flaw" else ""
        print(f"  {n:<36}{c:>12} pt{tag}{dual}")
    print(f"\n{len(rows)} {want.lower()}(s)")
    return 0


def cmd_steps(args):
    rows = _rows("chargen_priorities")
    if args.json:
        print(json.dumps([{"step": a, "allocation": b} for a, b in rows], indent=2))
        return 0
    w = max(len(a) for a, _ in rows)
    for a, b in rows:
        print(f"{a.ljust(w)}   {b}")
    print("\nAttributes are grouped Physical / Social / Mental and Abilities "
          "Talents / Skills / Knowledges;\nthe three numbers go to the categories "
          "in whatever order you prioritise them.")
    return 0


def cmd_validate(args):
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    problems, notes = [], []

    trad = data.get("tradition")
    free_sphere = None
    if trad:
        free_sphere = tradition_sphere(trad)
        notes.append(f"Tradition {trad} grants a free dot of {free_sphere}.")
    else:
        problems.append("no tradition named")

    attrs = data.get("attributes") or {}
    spent = []
    for cat in ("physical", "social", "mental"):
        got = attrs.get(cat) or {}
        if len(got) != 3:
            problems.append(f"{cat} should list 3 Attributes, found {len(got)}")
        over = sum(max(0, v - ATTRIBUTE_FLOOR) for v in got.values())
        spent.append(over)
        for k, v in got.items():
            if not ATTRIBUTE_FLOOR <= v <= 5:
                problems.append(f"Attribute {k}={v} is outside 1-5")
    if sorted(spent, reverse=True) != list(ATTRIBUTE_SPREAD):
        problems.append(
            f"Attribute dots above the free one are {sorted(spent, reverse=True)}, "
            f"expected {list(ATTRIBUTE_SPREAD)} in some order")

    abils = data.get("abilities") or {}
    aspent = []
    for cat in ("talents", "skills", "knowledges"):
        got = abils.get(cat) or {}
        aspent.append(sum(got.values()))
        for k, v in got.items():
            if v > CREATION_ABILITY_CAP:
                problems.append(
                    f"Ability {k}={v} exceeds the creation cap of {CREATION_ABILITY_CAP} "
                    "(raise it with freebie points instead)")
    if sorted(aspent, reverse=True) != list(ABILITY_SPREAD):
        problems.append(f"Ability dots are {sorted(aspent, reverse=True)}, "
                        f"expected {list(ABILITY_SPREAD)} in some order")

    bg = sum((data.get("backgrounds") or {}).values())
    if bg != BACKGROUND_DOTS:
        problems.append(f"Backgrounds total {bg}, expected {BACKGROUND_DOTS}")
    known_bg = {b.lower() for b, _ in _rows("backgrounds")}
    for b in (data.get("backgrounds") or {}):
        if b.lower() not in known_bg:
            problems.append(f"{b!r} is not a listed Background")

    spheres = data.get("spheres") or {}
    known_sph = {s.lower() for s, _, _ in _rows("spheres")}
    for s, v in spheres.items():
        if s.lower() not in known_sph:
            problems.append(f"{s!r} is not one of the nine Spheres")
        if not 1 <= v <= 5:
            problems.append(f"Sphere {s}={v} is outside 1-5")
    total_sph = sum(spheres.values())
    allowed = SPHERE_DOTS + (1 if free_sphere and free_sphere != "Any" else 0)
    if free_sphere and free_sphere != "Any" and free_sphere not in spheres:
        problems.append(f"{trad}'s free dot of {free_sphere} is not on the sheet")
    if total_sph != allowed:
        problems.append(f"Sphere dots total {total_sph}, expected {allowed} "
                        f"({SPHERE_DOTS} chosen + the Tradition's free dot)")
    arete = data.get("arete", STARTING_ARETE)
    for s, v in spheres.items():
        if v > arete:
            notes.append(f"{s} {v} is above Arete {arete} — legal, but the mage "
                         "can never roll enough successes to use it fully.")

    if data.get("arete", STARTING_ARETE) != STARTING_ARETE:
        notes.append(f"Arete is {data['arete']}, not the starting {STARTING_ARETE} "
                     "— assumed bought with freebie points.")
    if data.get("willpower", STARTING_WILLPOWER) < STARTING_WILLPOWER:
        problems.append(f"Willpower {data.get('willpower')} is below the starting "
                        f"{STARTING_WILLPOWER}")

    # Merits and Flaws are optional and live in the supplements; validate them
    # only if the sheet actually uses them.
    taken = (data.get("merits") or []) + (data.get("flaws") or [])
    if taken:
        try:
            catalog, ambiguous = _catalog()
        except SystemExit as e:
            problems.append(str(e).splitlines()[0])
            catalog, ambiguous = {}, {}
        if catalog:
            flaw_total = 0
            merit_total = 0
            chosen = {}
            for entry in taken:
                name = entry if isinstance(entry, str) else entry.get("name")
                pts = None if isinstance(entry, str) else entry.get("points")
                key = (name or "").lower()
                row = catalog.get(key)
                if row is None:
                    problems.append(f"{name!r} is not a listed Merit or Flaw")
                    continue
                if key in ambiguous:
                    notes.append(
                        f"{row[0]} appears in more than one book "
                        f"({ambiguous[key]}); using the {BOOK_NAMES[row[4]]} entry "
                        f"at {row[1]} points. Take the version from your character's own book.")
                lo, hi = cost_bounds(row[1])
                chosen[row[0]] = row
                if pts is None:
                    if lo != hi:
                        problems.append(
                            f"{row[0]} costs {row[1]} points — say which, "
                            f'e.g. {{"name": "{row[0]}", "points": {lo}}}')
                        continue
                    pts = lo
                if lo is not None and not (lo <= pts <= hi):
                    problems.append(f"{row[0]} is {row[1]} points; {pts} is outside that")
                    continue
                if "Flaw" in row[2] and entry in (data.get("flaws") or []):
                    flaw_total += pts
                else:
                    merit_total += pts

            if flaw_total > MAX_FLAW_POINTS:
                problems.append(
                    f"Flaws total {flaw_total} points; the cap is {MAX_FLAW_POINTS}")
            for a, b in EXCLUSIONS:
                if a in chosen and b in chosen:
                    problems.append(f"{a} and {b} are mutually exclusive")
            budget = FREEBIE_POINTS + min(flaw_total, MAX_FLAW_POINTS)
            notes.append(
                f"Freebie points: {FREEBIE_POINTS} base + {min(flaw_total, MAX_FLAW_POINTS)} "
                f"from Flaws = {budget} (ceiling {MAX_FREEBIES}); "
                f"{merit_total} spent on Merits, {budget - merit_total} left for traits.")
            if merit_total > budget:
                problems.append(
                    f"Merits cost {merit_total} freebie points but only {budget} are available")

    if args.json:
        print(json.dumps({"ok": not problems, "problems": problems, "notes": notes}, indent=2))
    else:
        name = data.get("name", Path(args.file).stem)
        print(f"{name} — {'OK' if not problems else str(len(problems)) + ' problem(s)'}")
        for p in problems:
            print(f"  ! {p}")
        for n in notes:
            print(f"  i {n}")
    return 0 if not problems else 1


def cmd_cost(args):
    tid = "xp_costs" if args.xp else "freebie_costs"
    n, cell = _cost_of(tid, args.trait, args.current)
    label = "experience points" if args.xp else "freebie points"
    if n is None:
        print(f"{args.trait}: {cell} ({label}) — not a flat per-dot price")
    else:
        print(f"{args.trait}: {cell} → {n} {label}"
              + (f" at current rating {args.current}" if args.current is not None else ""))
    return 0


def _table(args, tid, headers):
    rows = _rows(tid)
    if args.json:
        print(json.dumps([dict(zip(headers, r)) for r in rows], indent=2))
        return 0
    w = [max(len(h), max((len(str(r[i])) for r in rows), default=0))
         for i, h in enumerate(headers)]
    print("  ".join(h.ljust(w[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * x for x in w))
    for r in rows:
        print("  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("steps", help="the creation allocations")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_steps)

    v = sub.add_parser("validate", help="check a character JSON against the rules")
    v.add_argument("--file", required=True)
    v.add_argument("--json", action="store_true")
    v.set_defaults(fn=cmd_validate)

    c = sub.add_parser("cost", help="price one trait in freebie or experience points")
    c.add_argument("--trait", required=True)
    c.add_argument("--current", type=int, help="current rating, for 'current rating x N' prices")
    c.add_argument("--xp", action="store_true", help="use experience costs (default: freebie)")
    c.set_defaults(fn=cmd_cost)

    for nm in ("merits", "flaws"):
        m = sub.add_parser(nm, help=f"list {nm} from the supplements")
        m.add_argument("--category", help="Psychological, Mental, Supernatural, ...")
        m.add_argument("--name", help="substring match on the name")
        m.add_argument("--book", default="all", help="all | bos | tech")
        m.add_argument("--json", action="store_true")
        m.set_defaults(fn=cmd_merits, cmd=nm)

    for name, tid, heads in [
        ("traditions", "traditions", ["Tradition", "Specialty Sphere"]),
        ("backgrounds", "backgrounds", ["Background", "Covers"]),
        ("attributes", "attributes", ["Category", "Attribute"]),
        ("freebies", "freebie_costs", ["Trait", "Cost"]),
        ("experience", "xp_costs", ["Trait", "Cost"]),
    ]:
        t = sub.add_parser(name)
        t.add_argument("--json", action="store_true")
        t.set_defaults(fn=lambda a, tid=tid, heads=heads: _table(a, tid, heads))

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(_bootstrap.run(main))

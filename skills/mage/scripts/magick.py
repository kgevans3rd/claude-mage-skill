#!/usr/bin/env python3
"""
magick.py — casting, Paradox and the Spheres for Mage: The Ascension 2nd Ed.

Every rulebook value this uses is read from the module's tables at runtime
(see _bootstrap.py); nothing numeric is hard-coded here. If the module has not
been filled from the reader's own book, the first call raises with instructions
rather than guessing — a plausible-looking wrong difficulty is worse than a
refusal, because wrong rules are invisible for weeks of play.

The casting sequence, as the Casting Magick chart lays it out:

    difficulty = highest Sphere used + (3 coincidental / 4 vulgar /
                 5 vulgar before Sleepers), then modifiers (max +/-3),
                 floored at 3 and capped at 10
    roll Arete against it
    on a botch, Paradox = flat + per-dot x (dots in the highest Sphere)

    python3 magick.py cast --spheres Forces=3,Prime=2 --type vulgar-witnessed --arete 4
    python3 magick.py cast --spheres Life=3 --type coincidental --arete 3 --modifier -1
    python3 magick.py spheres Forces
    python3 magick.py spheres --all
    python3 magick.py paradox --type vulgar-witnessed --highest 3
    python3 magick.py difficulties
    python3 magick.py gauntlet
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap  # noqa: E402
from dice import roll_pool, describe, BOTCH, SUCCESS  # noqa: E402

MIN_DIFFICULTY = 3      # "minimum difficulty is 3" — Casting Magick chart
MAX_DIFFICULTY = 10     # "minimum difficulty 3, maximum 10" — Magick Difficulties
MAX_MODIFIER = 3        # "maximum +/-3"

TYPE_ALIASES = {
    "coincidental": "Coincidental",
    "vulgar": "Vulgar, without witnesses",
    "vulgar-unwitnessed": "Vulgar, without witnesses",
    "vulgar-witnessed": "Vulgar, with witnesses",
}
BOTCH_ALIASES = {
    "coincidental": "Coincidental botch",
    "vulgar": "Vulgar botch",
    "vulgar-unwitnessed": "Vulgar botch",
    "vulgar-witnessed": "Vulgar botch with Sleeper witnesses",
}


def _rows(tid):
    return _bootstrap.get(tid)


def find_rote(name):
    """Look up a named Effect. Exact match wins; otherwise substring."""
    rows = _rows("rotes")
    exact = [r for r in rows if r[0].lower() == name.lower()]
    hits = exact or [r for r in rows if name.lower() in r[0].lower()]
    if not hits:
        raise SystemExit(
            f"error: no Rote matching {name!r}. "
            f"List them with: magick.py rotes [Sphere] [--name <text>]")
    if len(hits) > 1:
        names = ", ".join(r[0] for r in hits[:8])
        raise SystemExit(f"error: {name!r} matches {len(hits)} Rotes: {names}"
                         + (" ..." if len(hits) > 8 else ""))
    return hits[0]


def rote_spheres(row, pick=None):
    """{sphere: rating} for a Rote, resolving a printed range like '2-3'."""
    name, sphere, rating, _page = row
    lo, _, hi = rating.partition("-")
    lo = int(lo)
    hi = int(hi) if hi else lo
    if pick is not None:
        if not lo <= pick <= hi:
            raise SystemExit(f"error: {name} is rating {rating}; {pick} is outside that")
        return {sphere: pick}, (lo != hi)
    return {sphere: lo}, (lo != hi)


def _lookup(tid, key, col=0):
    for row in _rows(tid):
        if row[col].lower() == key.lower():
            return row
    raise SystemExit(f"error: no row {key!r} in table {tid!r}")


def parse_spheres(text):
    """'Forces=3,Prime=2' -> {'Forces': 3, 'Prime': 2}, validated against the book."""
    known = {r[0].lower(): r[0] for r in _rows("spheres")}
    out = {}
    for part in (p.strip() for p in text.split(",") if p.strip()):
        name, _, rating = part.partition("=")
        name = name.strip()
        if name.lower() not in known:
            raise SystemExit(
                f"error: {name!r} is not one of the nine Spheres "
                f"({', '.join(sorted(set(known.values())))})")
        try:
            r = int(rating)
        except ValueError:
            raise SystemExit(f"error: Sphere rating for {name} must be a number, got {rating!r}")
        if not 1 <= r <= 5:
            raise SystemExit(f"error: Sphere rating for {name} must be 1-5, got {r}")
        out[known[name.lower()]] = r
    if not out:
        raise SystemExit("error: name at least one Sphere, e.g. --spheres Forces=3")
    return out


def casting_difficulty(spheres, effect_type, modifier=0):
    """Difficulty for an Effect, with the chart's floor, cap and modifier limit."""
    label = TYPE_ALIASES.get(effect_type)
    if label is None:
        raise SystemExit(f"error: --type must be one of {', '.join(sorted(TYPE_ALIASES))}")
    bonus = int(_lookup("casting_difficulty", label)[1])
    highest = max(spheres.values())
    if abs(modifier) > MAX_MODIFIER:
        raise SystemExit(f"error: the chart caps modifiers at +/-{MAX_MODIFIER}, got {modifier:+d}")
    raw = highest + bonus + modifier
    return {
        "highest_sphere": highest,
        "sphere_bonus": bonus,
        "effect_type": label,
        "modifier": modifier,
        "difficulty": max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, raw)),
        "unclamped": raw,
    }


def paradox_for_botch(effect_type, highest_sphere):
    label = BOTCH_ALIASES.get(effect_type)
    if label is None:
        raise SystemExit(f"error: --type must be one of {', '.join(sorted(BOTCH_ALIASES))}")
    row = _lookup("paradox_botch", label)
    flat, per = int(row[1]), int(row[2])
    return {"botch_type": label, "flat": flat, "per_sphere_dot": per,
            "highest_sphere": highest_sphere,
            "paradox": flat + per * highest_sphere}


def cmd_cast(args):
    rote = None
    if args.rote:
        if args.spheres:
            raise SystemExit("error: pass --rote or --spheres, not both")
        rote = find_rote(args.rote)
        spheres, ranged = rote_spheres(rote, args.rating)
        if ranged and args.rating is None and not args.json:
            print(f"note: {rote[0]} is printed as rating {rote[2]}; using "
                  f"{list(spheres.values())[0]}. Override with --rating.")
    elif args.spheres:
        spheres = parse_spheres(args.spheres)
    else:
        raise SystemExit("error: pass --spheres or --rote")
    diff = casting_difficulty(spheres, args.type, args.modifier)
    rng = random.Random(args.seed) if args.seed is not None else random
    r = roll_pool(args.arete, diff["difficulty"], willpower=args.willpower, rng=rng)

    out = {"spheres": spheres, **diff, "arete": args.arete, "roll": r}
    if rote:
        out["rote"] = {"name": rote[0], "sphere": rote[1],
                       "rating": rote[2], "page": rote[3]}
    if r["outcome"] == BOTCH:
        out["paradox"] = paradox_for_botch(args.type, diff["highest_sphere"])

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    sph = ", ".join(f"{k} {v}" for k, v in sorted(spheres.items()))
    if rote:
        print(f"Rote: {rote[0]}  —  {sph}  (p.{rote[3]})")
        print(f"Effect type: {diff['effect_type']}")
    else:
        print(f"Effect: {sph}  ({diff['effect_type']})")
    note = ""
    if diff["unclamped"] != diff["difficulty"]:
        note = f"  [clamped from {diff['unclamped']}]"
    mod = f" {diff['modifier']:+d}" if diff["modifier"] else ""
    print(f"Difficulty: highest Sphere {diff['highest_sphere']} "
          f"+ {diff['sphere_bonus']}{mod} = {diff['difficulty']}{note}")
    print(f"Arete {args.arete}: {describe(r)}")
    if r["outcome"] == SUCCESS:
        dd = _lookup("damage_duration", _successes_word(r["degree"]))
        print(f"  Damage: {dd[1]}   Duration: {dd[2]}")
    if "paradox" in out:
        p = out["paradox"]
        print(f"  PARADOX: {p['flat']} + {p['per_sphere_dot']} x {p['highest_sphere']} dots "
              f"= {p['paradox']} point{'s' if p['paradox'] != 1 else ''} ({p['botch_type']})")
        print("  The mage may spend a Willpower point to cancel the botch entirely.")
    return 0


_WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}


def _successes_word(n):
    return _WORDS.get(n, "Six+")


def cmd_rotes(args):
    rows = _rows("rotes")
    if args.sphere:
        rows = [r for r in rows if r[1].lower().startswith(args.sphere.lower())]
    if args.name:
        rows = [r for r in rows if args.name.lower() in r[0].lower()]
    if args.rating is not None:
        def covers(rating, want):
            lo, _, hi = rating.partition("-")
            return int(lo) <= want <= int(hi or lo)
        rows = [r for r in rows if covers(r[2], args.rating)]
    if args.json:
        print(json.dumps([{"name": r[0], "sphere": r[1], "rating": r[2], "page": int(r[3])}
                          for r in rows], indent=2))
        return 0
    if not rows:
        print("nothing matched")
        return 1
    cur = None
    for name, sphere, rating, page in sorted(rows, key=lambda r: (r[1], r[2], r[0])):
        if sphere != cur:
            cur = sphere
            print(f"\n{sphere}")
        lo = int(rating.partition("-")[0])
        dots = "\u25cf" * lo + "\u25cb" * (5 - lo)
        rng = f" ({rating})" if "-" in rating else ""
        print(f"  {dots}  {name}{rng}   p.{page}")
    print(f"\n{len(rows)} Effect(s)")
    return 0


def cmd_spheres(args):
    rows = _rows("spheres")
    if args.all or not args.sphere:
        names = sorted({r[0] for r in rows})
    else:
        names = [n for n in sorted({r[0] for r in rows})
                 if n.lower().startswith(args.sphere.lower())]
        if not names:
            raise SystemExit(f"error: no Sphere matching {args.sphere!r}")
    if args.json:
        data = {n: {int(r[1]): r[2] for r in rows if r[0] == n} for n in names}
        print(json.dumps(data, indent=2))
        return 0
    for n in names:
        print(f"\n{n}")
        for r in (row for row in rows if row[0] == n):
            dots = "●" * int(r[1]) + "○" * (5 - int(r[1]))
            print(f"  {dots}  {r[2]}")
    return 0


def _table(args, tid, headers):
    rows = _rows(tid)
    if args.json:
        print(json.dumps([dict(zip(headers, r)) for r in rows], indent=2))
        return 0
    w = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]
    print("  ".join(h.ljust(w[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * x for x in w))
    for r in rows:
        print("  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("cast", help="resolve an Effect end to end")
    c.add_argument("--spheres", help="e.g. Forces=3,Prime=2")
    c.add_argument("--rote", help="cast a named Effect from the book, e.g. \"Hermes Portal\"")
    c.add_argument("--rating", type=int,
                   help="for a Rote printed with a range, which rating to use")
    c.add_argument("--type", default="coincidental",
                   help="coincidental | vulgar | vulgar-witnessed")
    c.add_argument("--arete", type=int, required=True, help="the mage's Arete rating")
    c.add_argument("--modifier", type=int, default=0, help="situational modifier, max +/-3")
    c.add_argument("--willpower", action="store_true", help="spend Willpower for one success")
    c.add_argument("--seed", type=int)
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_cast)

    s = sub.add_parser("spheres", help="what each Sphere does at each rating")
    s.add_argument("sphere", nargs="?")
    s.add_argument("--all", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_spheres)

    ro = sub.add_parser("rotes", help="the named Effects of Chapter Eight")
    ro.add_argument("sphere", nargs="?", help="filter by Sphere")
    ro.add_argument("--rating", type=int, help="filter by required rating")
    ro.add_argument("--name", help="substring match on the name")
    ro.add_argument("--json", action="store_true")
    ro.set_defaults(fn=cmd_rotes)

    p = sub.add_parser("paradox", help="Paradox from a botched Effect")
    p.add_argument("--type", default="vulgar")
    p.add_argument("--highest", type=int, required=True, help="dots in the highest Sphere used")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=lambda a: (print(json.dumps(paradox_for_botch(a.type, a.highest), indent=2))
                                 if a.json else
                                 print(f"{paradox_for_botch(a.type, a.highest)['paradox']} "
                                       f"Paradox ({BOTCH_ALIASES[a.type]}, "
                                       f"highest Sphere {a.highest})")) or 0)

    for name, tid, heads in [
        ("difficulties", "magick_difficulty_mods", ["Activity", "Modifier"]),
        ("gauntlet", "gauntlet", ["Area", "Difficulty", "Successes"]),
        ("correspondence", "correspondence_ranges", ["Successes", "Range or connection"]),
        ("time", "time_ranges", ["Successes", "Timespan"]),
        ("duration", "damage_duration", ["Successes", "Damage", "Duration"]),
        ("degrees", "magick_success_degrees", ["Degree", "Threshold", "Outcome"]),
    ]:
        t = sub.add_parser(name, help=f"the {name} chart")
        t.add_argument("--json", action="store_true")
        t.set_defaults(fn=lambda a, tid=tid, heads=heads: _table(a, tid, heads))

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(_bootstrap.run(main))

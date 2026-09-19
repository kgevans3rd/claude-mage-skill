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
    return _bootstrap.tables().get(tid)


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
    spheres = parse_spheres(args.spheres)
    diff = casting_difficulty(spheres, args.type, args.modifier)
    rng = random.Random(args.seed) if args.seed is not None else random
    r = roll_pool(args.arete, diff["difficulty"], willpower=args.willpower, rng=rng)

    out = {"spheres": spheres, **diff, "arete": args.arete, "roll": r}
    if r["outcome"] == BOTCH:
        out["paradox"] = paradox_for_botch(args.type, diff["highest_sphere"])

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    sph = ", ".join(f"{k} {v}" for k, v in sorted(spheres.items()))
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
    c.add_argument("--spheres", required=True, help="e.g. Forces=3,Prime=2")
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

#!/usr/bin/env python3
"""
combat.py — the three-stage combat turn for Mage: The Ascension 2nd Edition.

    Stage One   Initiative   Wits + Alertness, difficulty 4. The winner
                             declares last and acts first.
    Stage Two   Attack       Dexterity + Firearms / Melee / Brawl.
                             A dodge is Dexterity + Dodge, and each of its
                             successes subtracts one from the attacker's.
    Stage Three Resolution   Roll damage (difficulty 6), then the target
                             soaks with Stamina (difficulty 6).

Weapon, armour and complication values come from the module's tables, never
from this file.

    python3 combat.py initiative --wits 3 --alertness 2
    python3 combat.py attack --pool 6 --weapon "Pistol, Lt." --kind firearms
    python3 combat.py attack --pool 7 --maneuver Kick --strength 3
    python3 combat.py soak --stamina 3 --damage 5
    python3 combat.py health --damage 3
    python3 combat.py weapons | python3 combat.py firearms | python3 combat.py armor
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap  # noqa: E402
from dice import roll_pool, describe  # noqa: E402

INITIATIVE_DIFFICULTY = 4
DAMAGE_DIFFICULTY = 6
SOAK_DIFFICULTY = 6
HAND_TO_HAND_DODGE = 6


def _rows(tid):
    return _bootstrap.tables().get(tid)


def _rng(seed):
    return random.Random(seed) if seed is not None else random


def find_weapon(name, kind):
    """Look a weapon up in whichever table its kind lives in."""
    tid = {"firearms": "firearms", "melee": "melee_weapons",
           "brawl": "brawling", "do": "do_strike"}.get(kind)
    if tid is None:
        raise SystemExit("error: --kind must be firearms, melee, brawl or do")
    rows = _rows(tid)
    hits = [r for r in rows if r[0].lower() == name.lower()]
    if not hits:
        hits = [r for r in rows if r[0].lower().startswith(name.lower())]
    if not hits:
        names = ", ".join(r[0] for r in rows)
        raise SystemExit(f"error: no {kind} entry {name!r}. Available: {names}")
    if len(hits) > 1:
        raise SystemExit(f"error: {name!r} matches {len(hits)}: "
                         + ", ".join(r[0] for r in hits))
    return tid, hits[0]


def resolve_damage(expr, strength=None, successes=0):
    """Turn a damage cell ('Strength +1', '4', '3 + successes') into a pool."""
    e = expr.strip().lower()
    if e.startswith("special"):
        return None, expr
    if "strength" in e:
        if strength is None:
            raise SystemExit(f"error: damage is {expr!r}; pass --strength")
        bonus = 0
        if "+" in e:
            bonus = int(e.split("+")[1].strip())
        return strength + bonus, f"Strength {strength} +{bonus}" if bonus else f"Strength {strength}"
    if "success" in e:
        base = int(e.split("+")[0].strip())
        return base + successes, f"{base} + {successes} successes"
    try:
        return int(e), expr
    except ValueError:
        return None, expr


def cmd_initiative(args):
    r = roll_pool(args.wits + args.alertness, INITIATIVE_DIFFICULTY, rng=_rng(args.seed))
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"Initiative (Wits {args.wits} + Alertness {args.alertness}, diff "
              f"{INITIATIVE_DIFFICULTY}): {describe(r)}")
        print("  The winner declares her action last and performs it first.")
    return 0


def cmd_attack(args):
    rng = _rng(args.seed)
    name = args.weapon or args.maneuver
    if not name:
        raise SystemExit("error: pass --weapon or --maneuver")
    kind = args.kind
    if args.maneuver and not args.weapon and kind == "firearms":
        kind = "brawl"
    tid, row = find_weapon(name, kind)

    if tid == "firearms":
        label, diff, dmg_expr = row[0], int(row[2]), row[3]
        extra = f"  range {row[4]}yd, rate {row[5]}, clip {row[6]}, conceal {row[7]}"
    else:
        label, diff, dmg_expr = row[0], int(row[1]), row[2]
        extra = ""

    diff += args.modifier
    diff = max(2, min(10, diff))
    atk = roll_pool(args.pool, diff, rng=rng)
    net = atk["degree"] if atk["outcome"] == "success" else 0
    net = max(0, net - args.dodge)

    out = {"weapon": label, "table": tid, "difficulty": diff,
           "attack": atk, "dodge_successes": args.dodge, "net_successes": net}

    if not args.json:
        print(f"{label} (difficulty {diff}){extra}")
        print(f"  Attack: {describe(atk)}")
        if args.dodge:
            print(f"  Dodge cancels {args.dodge} → {net} net success(es)")

    if net > 0:
        pool, shown = resolve_damage(dmg_expr, args.strength, net)
        if pool is None:
            out["damage"] = {"expression": dmg_expr, "note": "resolve by hand"}
            if not args.json:
                print(f"  Damage: {dmg_expr} — resolve by hand")
        else:
            if tid == "firearms":
                pool += net - 1          # extra successes add dice to the damage roll
                shown = f"{dmg_expr} +{net - 1} extra success(es)"
            dmg = roll_pool(pool, DAMAGE_DIFFICULTY, rng=rng)
            out["damage"] = {"expression": dmg_expr, "pool": pool, "roll": dmg}
            if not args.json:
                print(f"  Damage ({shown} = {pool}d10 vs {DAMAGE_DIFFICULTY}): {describe(dmg)}")
                print(f"  → {max(0, dmg['degree'])} Health Level(s) before soak")
    elif not args.json:
        print("  No damage.")

    if args.json:
        print(json.dumps(out, indent=2))
    return 0


def cmd_soak(args):
    pool = args.stamina + args.armor
    r = roll_pool(pool, SOAK_DIFFICULTY, rng=_rng(args.seed))
    soaked = max(0, r["degree"] if r["outcome"] == "success" else 0)
    through = max(0, args.damage - soaked)
    if args.json:
        print(json.dumps({"pool": pool, "roll": r, "soaked": soaked,
                          "damage_through": through}, indent=2))
    else:
        bits = f"Stamina {args.stamina}" + (f" + armour {args.armor}" if args.armor else "")
        print(f"Soak ({bits} = {pool}d10 vs {SOAK_DIFFICULTY}): {describe(r)}")
        print(f"  {args.damage} damage - {soaked} soaked = {through} Health Level(s) taken")
        if args.stamina and through > args.stamina:
            print(f"  STUNNED: damage exceeds Stamina {args.stamina}; the target cannot act next turn.")
    return 0


def cmd_health(args):
    rows = _rows("health_levels")
    heal = {r[0]: r[1] for r in _rows("healing_times")}
    taken = args.damage
    if args.json:
        print(json.dumps([{"level": r[0], "penalty": r[1], "effect": r[2],
                           "healing": heal.get(r[0])} for r in rows], indent=2))
        return 0
    for i, r in enumerate(rows):
        mark = ">" if i + 1 == taken else " "
        pen = r[1].rjust(4)
        print(f"{mark} {r[0]:<14}{pen}   {r[2]}")
    if taken:
        if taken > len(rows):
            print(f"\n{taken} Health Levels is past Incapacitated — the character is dead.")
        else:
            cur = rows[taken - 1]
            print(f"\nAt {taken} Health Level(s): {cur[0]}, dice pool {cur[1]}. "
                  f"Healing normally: {heal.get(cur[0], '?')}.")
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

    i = sub.add_parser("initiative")
    i.add_argument("--wits", type=int, required=True)
    i.add_argument("--alertness", type=int, default=0)
    i.add_argument("--seed", type=int)
    i.add_argument("--json", action="store_true")
    i.set_defaults(fn=cmd_initiative)

    a = sub.add_parser("attack")
    a.add_argument("--pool", type=int, required=True, help="Dexterity + the relevant Ability")
    a.add_argument("--weapon")
    a.add_argument("--maneuver")
    a.add_argument("--kind", default="firearms",
                   help="firearms | melee | brawl | do (default: firearms)")
    a.add_argument("--strength", type=int, help="needed for Strength-based damage")
    a.add_argument("--dodge", type=int, default=0, help="the target's dodge successes")
    a.add_argument("--modifier", type=int, default=0, help="difficulty modifier")
    a.add_argument("--seed", type=int)
    a.add_argument("--json", action="store_true")
    a.set_defaults(fn=cmd_attack)

    s = sub.add_parser("soak")
    s.add_argument("--stamina", type=int, required=True)
    s.add_argument("--armor", type=int, default=0, help="the armour's rating")
    s.add_argument("--damage", type=int, required=True)
    s.add_argument("--seed", type=int)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_soak)

    h = sub.add_parser("health")
    h.add_argument("--damage", type=int, default=0)
    h.add_argument("--json", action="store_true")
    h.set_defaults(fn=cmd_health)

    for name, tid, heads in [
        ("weapons", "melee_weapons", ["Weapon", "Diff", "Damage", "Conceal"]),
        ("brawling", "brawling", ["Maneuver", "Diff", "Damage"]),
        ("do", "do_strike", ["Maneuver", "Diff", "Damage"]),
        ("firearms", "firearms",
         ["Type", "Example", "Diff", "Dmg", "Range", "Rate", "Clip", "Con"]),
        ("armor", "armor", ["Class", "Rating", "Penalty"]),
        ("complications", "firefight_complications", ["Complication", "Difficulty", "Dice"]),
        ("dodges", "dodge_terrain", ["Diff", "Terrain"]),
    ]:
        t = sub.add_parser(name)
        t.add_argument("--json", action="store_true")
        t.set_defaults(fn=lambda a, tid=tid, heads=heads: _table(a, tid, heads))

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(_bootstrap.run(main))

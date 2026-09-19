#!/usr/bin/env python3
"""
dice.py — Storyteller d10 dice pools for Mage: The Ascension 2nd Edition.

The whole system is one roll: throw a pool of d10s, count how many meet the
difficulty, subtract the ones, and read the result. Everything else in the game
is a different way of assembling the pool.

The botch rule is implemented exactly as the book states it, which is not the
rule most tables play from memory:

    A "one" cancels a success; remove both dice. If more "ones" remain than
    successes, you botch. If nothing is left on either side, you simply failed.

So two successes against three ones is a BOTCH (degree 1), not a failure — a
roll can botch even though it rolled successes. Getting this wrong makes
magick far safer than the book intends, because Paradox is driven off botches.

    python3 dice.py 7 --difficulty 6
    python3 dice.py 5 --difficulty 8 --willpower
    python3 dice.py 6 --difficulty 6 --specialty
    python3 dice.py 8 --difficulty 7 --json

Difficulty defaults to 6 — "unless the Storyteller says otherwise, the standard
difficulty for a particular task is always a 6" (p.80).
"""

from __future__ import annotations

import argparse
import json
import random
import sys

STANDARD_DIFFICULTY = 6
MIN_DIFFICULTY = 2
MAX_DIFFICULTY = 10

BOTCH = "botch"
FAILURE = "failure"
SUCCESS = "success"


def roll_pool(pool, difficulty=STANDARD_DIFFICULTY, specialty=False,
              willpower=False, rng=None):
    """Roll `pool` d10s and resolve them. Returns a result dict."""
    rng = rng or random
    if pool < 0:
        raise ValueError("dice pool cannot be negative")
    if not MIN_DIFFICULTY <= difficulty <= MAX_DIFFICULTY:
        raise ValueError(f"difficulty must be {MIN_DIFFICULTY}-{MAX_DIFFICULTY}")

    dice = [rng.randint(1, 10) for _ in range(pool)]

    # A specialty lets a 10 be rolled again and counted afresh, so a single die
    # can yield several successes. Kept opt-in: it is a troupe-level option,
    # not part of the base roll.
    extra = []
    if specialty:
        pending = [d for d in dice if d == 10]
        while pending:
            again = [rng.randint(1, 10) for _ in pending]
            extra.extend(again)
            pending = [d for d in again if d == 10]

    all_dice = dice + extra
    successes = sum(1 for d in all_dice if d >= difficulty)
    # Only the originally-rolled dice can botch; a re-rolled specialty die that
    # comes up 1 adds nothing rather than punishing the specialty.
    ones = sum(1 for d in dice if d == 1)

    if willpower:
        successes += 1

    net = successes - ones
    if net > 0:
        outcome, degree = SUCCESS, net
    elif net < 0:
        outcome, degree = BOTCH, -net
    else:
        outcome, degree = FAILURE, 0

    return {
        "pool": pool,
        "difficulty": difficulty,
        "dice": dice,
        "specialty_rerolls": extra,
        "raw_successes": successes,
        "ones": ones,
        "net": net,
        "outcome": outcome,
        "degree": degree,
        "willpower_spent": bool(willpower),
    }


DEGREE_NAMES = {1: "Marginal", 2: "Moderate", 3: "Complete",
                4: "Exceptional", 5: "Phenomenal"}


def describe(r):
    """One-line human summary, for narration at the table."""
    shown = ", ".join(str(d) for d in r["dice"]) or "—"
    line = f"{r['pool']}d10 vs diff {r['difficulty']}: [{shown}]"
    if r["specialty_rerolls"]:
        line += f" +[{', '.join(str(d) for d in r['specialty_rerolls'])}]"
    if r["willpower_spent"]:
        line += " +1 Willpower"
    if r["outcome"] == SUCCESS:
        name = DEGREE_NAMES.get(r["degree"], "Phenomenal")
        line += f" → {r['degree']} success{'es' if r['degree'] != 1 else ''} ({name})"
    elif r["outcome"] == BOTCH:
        line += f" → BOTCH by {r['degree']}"
    else:
        line += " → failure"
    if r["ones"]:
        line += f"  [{r['ones']} one{'s' if r['ones'] != 1 else ''} cancelled]"
    return line


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pool", type=int, help="number of d10s")
    ap.add_argument("--difficulty", "-d", type=int, default=STANDARD_DIFFICULTY)
    ap.add_argument("--specialty", action="store_true",
                    help="re-roll 10s and count them again (optional troupe rule)")
    ap.add_argument("--willpower", action="store_true",
                    help="spend a Willpower point for one automatic success")
    ap.add_argument("--seed", type=int, help="seed the roll, for reproducible tests")
    ap.add_argument("--json", action="store_true", help="emit the full result as JSON")
    args = ap.parse_args(argv)

    rng = random.Random(args.seed) if args.seed is not None else random
    try:
        r = roll_pool(args.pool, args.difficulty, args.specialty, args.willpower, rng)
    except ValueError as e:
        sys.exit(f"error: {e}")

    print(json.dumps(r, indent=2) if args.json else describe(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())

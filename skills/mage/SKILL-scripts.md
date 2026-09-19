# Helper scripts

Every script reads its rulebook values from the `mage2e` module at runtime. If
a value is missing the script **refuses and says how to fill it** (exit code 3)
rather than guessing. Relay that message; do not substitute a remembered value.

All of them accept `--json` for machine-readable output, and the rolling ones
accept `--seed` so a result can be reproduced in a bug report.

---

## `lookup.py` — what is loaded, and any table

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/lookup.py --status      # run this first, once per session
python3 ${CLAUDE_SKILL_DIR}/scripts/lookup.py --list        # every cited table, ! = unfilled
python3 ${CLAUDE_SKILL_DIR}/scripts/lookup.py firearms
python3 ${CLAUDE_SKILL_DIR}/scripts/lookup.py bos:merits_flaws
python3 ${CLAUDE_SKILL_DIR}/scripts/lookup.py --search quintessence
```

Core tables have bare ids (`spheres`, `firearms`). Supplement tables are
namespaced by their book: `bos:` for the players guide, `tech:` for the
Technocracy guide. `--status` shows which modules are installed and filled;
`--search` covers all of them.

`--status` prints which book the values came from and how many tables are
filled. Anything printed by `lookup.py <table>` is quotable at the table,
because it came from the player's own copy.

---

## `dice.py` — the d10 pool

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/dice.py 7                 # difficulty 6 by default
python3 ${CLAUDE_SKILL_DIR}/scripts/dice.py 5 --difficulty 8
python3 ${CLAUDE_SKILL_DIR}/scripts/dice.py 5 --willpower     # +1 automatic success
python3 ${CLAUDE_SKILL_DIR}/scripts/dice.py 6 --specialty     # optional: re-roll 10s
```

Outcome is `success`, `failure` or `botch` with a degree. **Ones cancel
successes, and more ones than successes is a botch even when successes were
rolled** — that is the printed rule, and it is why magick is dangerous.

`--specialty` is an optional troupe rule, not part of the base roll, and is not
one of the module's cited tables.

---

## `magick.py` — Effects, Paradox, Spheres

```bash
# Resolve an Effect end to end
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py cast \
    --spheres Forces=3,Prime=2 --type vulgar-witnessed --arete 4 [--modifier -1] [--willpower]

# Rotes (the book's named Effects)
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py cast --rote "Hermes Portal" --type vulgar --arete 4
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py cast --rote "Alter State" --rating 5 --type coincidental --arete 5
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py rotes              # all 110
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py rotes Spirit
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py rotes --rating 2
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py rotes --name gauntlet

python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py spheres Forces    # or --all
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py paradox --type vulgar --highest 3
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py difficulties      # the modifier chart
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py gauntlet
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py correspondence
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py time
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py duration
python3 ${CLAUDE_SKILL_DIR}/scripts/magick.py degrees
```

`cast` does the whole sequence: difficulty from the highest Sphere plus the
Effect type, modifiers clamped to ±3 and the difficulty to 3–10, the Arete
roll, the damage/duration line on a success, and the Paradox owed on a botch.

`--rote` fills the Spheres from the book, so `--rote` and `--spheres` are
mutually exclusive. Lookup is exact-match first, then substring, and **refuses
rather than guessing** when a name is ambiguous — `--rote Time` matches five
Effects and errors instead of picking one. Three Effects print a rating range
(`Telekinetic Control` 2–3, `Alter State` 3–5, `Free the Mad Howlers` 3–4);
those default to the low end, say so, and take `--rating` to override.

`--type` is `coincidental`, `vulgar` or `vulgar-witnessed`. Choosing between
them is the Storyteller's call and the single most consequential ruling in the
game — it moves both the difficulty and the Paradox.

---

## `combat.py` — the three-stage turn

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/combat.py initiative --wits 3 --alertness 2
python3 ${CLAUDE_SKILL_DIR}/scripts/combat.py attack --pool 6 --weapon "Pistol, Lt."
python3 ${CLAUDE_SKILL_DIR}/scripts/combat.py attack --pool 7 --maneuver Kick --kind brawl --strength 3
python3 ${CLAUDE_SKILL_DIR}/scripts/combat.py attack --pool 6 --weapon Knife --kind melee --strength 2 --dodge 2
python3 ${CLAUDE_SKILL_DIR}/scripts/combat.py soak --stamina 3 --armor 2 --damage 5
python3 ${CLAUDE_SKILL_DIR}/scripts/combat.py health --damage 3
```

`--kind` picks the table: `firearms` (default), `melee`, `brawl`, `do`.
Strength-based damage needs `--strength`. `--dodge` subtracts the target's
dodge successes before damage is rolled.

Reference tables: `weapons`, `brawling`, `do`, `firearms`, `armor`,
`complications`, `dodges`.

`soak` warns when damage exceeds Stamina, which stuns the target for a turn.

---

## `character.py` — creation, validation, costs

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/character.py steps
python3 ${CLAUDE_SKILL_DIR}/scripts/character.py traditions
python3 ${CLAUDE_SKILL_DIR}/scripts/character.py backgrounds
python3 ${CLAUDE_SKILL_DIR}/scripts/character.py validate --file <sheet>.json
python3 ${CLAUDE_SKILL_DIR}/scripts/character.py cost --trait Spheres
python3 ${CLAUDE_SKILL_DIR}/scripts/character.py cost --trait Arete --current 2 --xp

# Merits and Flaws (supplements only — the core book has none)
python3 ${CLAUDE_SKILL_DIR}/scripts/character.py merits
python3 ${CLAUDE_SKILL_DIR}/scripts/character.py merits --category Supernatural
python3 ${CLAUDE_SKILL_DIR}/scripts/character.py flaws --book tech
python3 ${CLAUDE_SKILL_DIR}/scripts/character.py flaws --name mentor
```

`--book` is `all` (default), `bos` or `tech`. Where a name appears in both
books at different costs, the players guide entry wins and the clash is
reported rather than resolved silently.

`validate` checks the 7/5/3 and 13/9/5 spreads (allowing for the free dot in
each Attribute), the creation cap of 3 on Abilities, the 7 Background dots, the
5 Sphere dots plus the Tradition's free one, and that named Spheres and
Backgrounds actually exist. It exits 1 with a list when something is wrong.

If the sheet has `merits` or `flaws`, it also checks every entry exists, that
Flaws stay within the 7-point cap, that variable-cost entries name a value
inside their range, that Merits fit the freebie budget (15 + Flaws, ceiling 22),
and that no mutually exclusive pair is taken. Entries are plain names, or
`{"name": "Past Life", "points": 3}` where the cost is a range.

`templates/example-character.json` is a complete, valid sheet to copy.

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | fine |
| 1 | validation failed — the output says what |
| 2 | bad arguments |
| 3 | a rulebook table is not filled on this machine |

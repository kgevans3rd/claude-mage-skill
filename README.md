# Mage: The Ascension 2nd Edition — a Claude Code Storyteller skill

Run persistent **Mage: The Ascension (2nd Edition)** chronicles in Claude Code,
the way [`claude-dnd-skill`](https://github.com/neuralinitiative/claude-dnd-skill)
runs D&D 5e — but without shipping a line of White Wolf's rules.

The rules live in a [`byo-rulebook`](https://github.com/kgevans3rd/byo-rulebook)
module that cites the book by page. You point it at **your own copy** and it
fills in the values locally, outside version control. What this repository
contains is the shape of the game and the code that runs it.

```
mage2e/            core rulebook — 29 cited tables, no values
bookofshadows/     players guide — Merits and Flaws (not in the core book)
technocracy/       Technocracy sourcebook — 26 more Merits and Flaws
skills/mage/       the Claude Code skill: Storyteller prompt, scripts, templates
tools/             fill a module from your book; render or extract cited pages
tests/             31 tests; the rules-logic third runs with no book at all
```

One module per book, because a module is scoped to one printing: its title,
page offset and text layer all belong to that edition. Core table ids stay bare
(`spheres`); a supplement's are namespaced (`bos:merits_flaws`).

## Why it is built this way

D&D has an SRD, so `claude-dnd-skill` can ship `dnd5e_srd.json` outright. Mage
has no such licence: the book's own copyright page denies reproduction. A skill
that embedded its tables would be redistributing them.

So this one cites instead. `system.md` says *"the firearms table is on printed
page 263"*, `schema.json` says what shape that table has and what must be true
of it, and the values arrive from the reader's own PDF into a git-ignored file.
The module is publishable precisely because the numbers are not in it.

The defaults are structural rather than advisory: `.gitignore` excludes `*.pdf`,
`*.local.json` and rendered pages, and the module carries its own `.gitignore`
so the values do not travel even if the directory is copied out.

## Install

```bash
git clone <this repo> mage-ascension && cd mage-ascension

# 1. the toolkit (a checkout, not a copy — so it stays pullable)
git clone https://github.com/kgevans3rd/byo-rulebook.git _toolkit

# 2. your own copies of the books (any subset — each is independent)
python3 tools/fill_tables.py --module mage2e        --pdf ~/books/mage-2e.pdf
python3 tools/fill_tables.py --module bookofshadows --pdf ~/books/book-of-shadows.pdf
python3 tools/fill_tables.py --module technocracy   --pdf ~/books/technocracy.pdf

# 3. check
python3 skills/mage/scripts/lookup.py --status
python3 -m unittest discover -s tests
```

Then add the plugin to Claude Code (`.claude-plugin/marketplace.json` is at the
repository root) and invoke `/mage`.

Needs Python 3.8+ and poppler (`pdftotext`, `pdftoppm`). No third-party
packages.

### If your scan has no text layer

Mine did not — 314 pages of 2003 image scan, zero extractable characters — so
every table is declared `manual` and its values were entered by reading
rendered pages. `tools/render_pages.py` renders exactly the pages the schema
cites, applying the page offset, so you can check any value against the chart:

```bash
python3 tools/render_pages.py --module mage2e --pdf BOOK.pdf --table firearms
```

`mage2e/README.md` explains this in full, including the three tables where the
page was genuinely ambiguous and what was done about each.

The Technocracy guide is the exception: its scan *does* carry a text layer, so
`tools/extract_headed_entries.py` machine-reads its entries and coerces every
cost against the toolkit's `int` type — which is what caught the two whose
"1 pt" the OCR had read as "I pt".

### Merits and Flaws are not in the core rulebook

Checked against the core book's own index, not assumed: the M column runs
*Methodologies → Mistridge*, the F column *First Cabal → Foci*. They live in
**The Book of Shadows** (111 entries) and, for Union agents, **Guide to the
Technocracy** (26 more). Without those modules the skill says so rather than
inventing them.

## Using it

```
/mage                        guided menu
/mage new <chronicle>        create a chronicle
/mage load <chronicle>       load and recap
/mage character new          walk mage creation
/mage cast                   resolve an Effect
/mage combat                 run the three-stage turn
```

The scripts work standalone too:

```bash
python3 skills/mage/scripts/magick.py cast \
    --spheres Forces=3,Prime=2 --type vulgar-witnessed --arete 4

Effect: Forces 3, Prime 2  (Vulgar, with witnesses)
Difficulty: highest Sphere 3 + 5 = 8
Arete 4: 4d10 vs diff 8: [6, 3, 7, 1] → BOTCH by 1  [1 one cancelled]
  PARADOX: 2 + 2 x 3 dots = 8 points (Vulgar botch with Sleeper witnesses)
  The mage may spend a Willpower point to cancel the botch entirely.
```

```bash
python3 skills/mage/scripts/combat.py attack --pool 6 --weapon "Pistol, Lt."
python3 skills/mage/scripts/character.py merits --category Supernatural
python3 skills/mage/scripts/character.py validate --file mage.json
python3 skills/mage/scripts/lookup.py --search quintessence
```

## Two design decisions worth knowing about

**Nothing is defaulted.** Ask for a value the module does not have and the
script refuses, with instructions, and exits 3. It never falls back on a
remembered number. A plausible-looking wrong difficulty is worse than an error,
because wrong rules stay invisible for weeks of play. The skill prompt tells
Claude the same thing: run the script, never quote from memory.

**The botch rule is the printed one.** Ones cancel successes, and *more ones
than successes is a botch even when successes were rolled* — two successes
against three ones botches. Most tables play it as "a botch is a 1 with no
successes", which makes magick markedly safer than the book intends, since
Paradox is driven off botches. There is a test for it.

## Relationship to claude-dnd-skill

This is a parallel skill in the same shape — `skills/<name>/SKILL.md`, scripts,
templates, a plugin manifest — not a patch to it. `claude-dnd-skill`'s
`ruleset` field selects between D&D 5e 2014 and 2024 and its engine assumes d20
throughout; Mage is a d10 dice-pool game with no AC, no hit points and no
initiative order in the 5e sense. Sharing a codebase would mean special-casing
both. Installed side by side, `/dm:dnd` and `/mage` coexist.

What it does borrow is the layout and the conventions, so anything learned from
one repository applies to the other.

## Licence

AGPL-3.0-or-later, matching both upstream projects.

*Mage: The Ascension* is a trademark of Paradox Interactive. This is an
unofficial, unaffiliated tool that ships none of the game's text or tables and
requires you to own the book.

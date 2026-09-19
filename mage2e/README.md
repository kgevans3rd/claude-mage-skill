# mage2e — Mage: The Ascension 2nd Edition, as a byo-rulebook module

This directory ships the **structure** of Mage 2nd Edition — what each table
is, which printed page it is on, and what must be true of it — and none of the
publisher's values. Those come from your own copy of the book and land in files
this repository never commits.

```
schema.json               29 tables: what they are, where, how to check them
system.md                 the rules, with {{mage:table:*}} citations
corrections.local.json    the values, hand-entered from your copy   (ignored)
tables.local.json         the runtime store the scripts read        (ignored)
```

## Why every locator is `manual`

byo-rulebook's parsers read a PDF's **text layer**. The reference scan of this
book does not have one:

```
$ pdftotext "Mage the ascension 2nd ed.pdf" - | wc -c
0
```

314 pages, produced in 2003 by "Acrobat 5.0 Image Conversion Plug-in", never
run through OCR. There is no text to parse, mis-parse or repair — `dot_leader`,
`bare_column`, `linearised_matrix` and `wrapped_pairs` all have nothing to bite
on. So every table here is declared `manual`, which is the toolkit's documented
path for exactly this case, and the values are supplied through
`corrections.local.json` as `row_adds`. The schema's invariants then validate
them as they would any parsed table — and they do run:

```
$ python3 _toolkit/toolkit/extract.py --module mage2e --pdf BOOK.pdf
mage: extracted 314 lines from Mage the ascension 2nd ed.pdf
applying manual corrections from mage2e/corrections.local.json
...
OK: 29
```

If you later obtain an OCR'd copy of the same printing, the citations here are
already correct and the locators can be upgraded table by table.

## Page numbers

`page` fields are **printed** page numbers. `source.page_offset` is 17, so:

```
PDF page = printed page + 17
```

This was calibrated against the numbers the book prints on itself (PDF 19 is
printed 2; PDF 22 is printed 5) and checked at both ends rather than taken from
the table of contents, which is where page citations usually go wrong.

To put a chart next to its values:

```bash
python3 ../tools/render_pages.py --module . --pdf BOOK.pdf --table firearms
```

## What the scan cost, and where to be careful

Three tables are marked `extraction_risk: high`. All three have since been
**confirmed against the printed page by the book's owner (2026-09-19)**, and
their `why` notes in `corrections.local.json` record both what was ambiguous and
who resolved it. The risk flag stays because the page would defeat a parser just
as thoroughly next time — it describes the scan, not the confidence in the values.

- **`health_levels`** — seven level labels against five printed dice penalties.
  Bruised and Incapacitated have blank cells for different reasons. **Resolved**:
  Incapacitated is `n/a`, confirmed by the owner; Bruised is `0`, carried by the
  effect line printed beside it ("no action penalties") rather than by the blank
  cell. Stored as `n/a` and not `0` so nothing downstream reads "incapacitated"
  as "unimpaired".
- **`firefight_complications`** — sixteen rows, fifteen entries in the Dice
  column. The gap is at *Multiple shots*, and it is visible only as whitespace
  in a column printed on a tilted graphic. **Resolved 2026-09-19**: confirmed
  against the printed page by the book's owner — Multiple shots takes a
  difficulty modifier only (`+1/extra shot`), and the rows below it read
  Full-auto `+3`/`+10`, Three-round burst `+1`/`+3`, Spray `5 +1/yard`/`+10`.
  The table keeps `extraction_risk: high` because the page would defeat a
  parser just as thoroughly next time; the values themselves are no longer in
  doubt.
- **`time_ranges`** — the five-success row prints a bare `100` with no unit,
  between `50 years` and `500 years`. **Resolved**: confirmed by the owner as
  `100 years`. The unit was dropped in the printing, not in the transcription.

Two errata in this printing are recorded as printed, with the correction in the
note rather than applied silently:

- The creation chart heads its third step "Step Three: Select Attributes",
  repeating step two's heading; the 13/9/5 split on the same line shows
  Abilities is meant.
- "No Attribute higher than 3 at this stage", printed under the Abilities step,
  is the Ability cap.

## What is not here

**Merits and Flaws are not in this book at all** — not an omission in this
module. The core rulebook's own index runs *Methodologies → Mistridge* with no
"Merits" and *First Cabal → Foci* with no "Flaws". They are in the players
guide; see the `bookofshadows/` module.

Also absent: Rotes, the full Ability list with dot-by-dot descriptions,
Charms, spirit statistics and the bestiary. The 29 tables cover the mechanical
core — resolution, creation, advancement, magick, Paradox, combat and injury —
which is what the scripts need to run a game. Adding more is a matter of
appending to `schema.json` and `corrections.local.json`; nothing in the code
needs to change.

## Filling it from your own copy

```bash
git clone https://github.com/kgevans3rd/byo-rulebook.git ../_toolkit
python3 ../tools/fill_tables.py --module . --pdf /path/to/your/rulebook.pdf
python3 ../_toolkit/toolkit/check_placeholders.py --module .
```

## Licence

The module (schema, prose, notes) is AGPL-3.0-or-later, matching byo-rulebook.
The rulebook values are White Wolf's and are not distributed with it.

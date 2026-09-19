# bookofshadows — The Book of Shadows: The Mage Players Guide

Structure and citations only. The values come from your own copy and land in
git-ignored files beside this one.

## Why this module exists

**Merits and Flaws are not in the Mage 2nd Edition core rulebook.** This is easy
to get wrong, so it was checked against the core book's own index rather than
assumed: the M column runs *Methodologies → Mistridge* with no "Merits", and the
F column runs *First Cabal → Foci* with no "Flaws". They are here instead,
across printed pages 29–46.

That is also why this is a separate module rather than extra tables bolted onto
`mage2e/`. A byo-rulebook module is scoped to one book: its title, its page
offset and its text layer are all properties of a single printing. Merging two
books into one schema makes every citation ambiguous.

## Page numbers

`page_offset` is **1**: PDF page = printed page + 1.

Calibrated from the page numbers the book prints on itself — PDF 31 carries
printed 30, PDF 47 carries printed 46 — and *not* from the contents page, which
would have given 2 and put every citation one page out. This is the failure
byo-rulebook warns about, and it showed up here on the first try.

## What was read, and what was not

The 111 entries carry **name, cost, type and category** only. Each entry's
effect is a paragraph of the book's prose; reproducing 18 pages of it would be
redistributing the book, so look the entry up on the cited page.

The scan is image-only — `pdftotext` over all 210 pages returns zero characters,
exactly as with the core rulebook — so the entries were read off rendered pages:

```bash
python3 ../tools/render_pages.py --module . --pdf BOOK.pdf --printed 36
```

## Two entries worth knowing about

- **Spirit Magnet** is the only one that can be taken as either a Merit (3–7)
  or a Flaw (2–6). Its `type` column says `Merit or Flaw`, and its `cost`
  carries both ranges, which is why `cost` is a label rather than an int.
- **Magical Prohibition or Imperative** (2–7) is priced by the Storyteller
  against the severity of the *geas* and its consequence, not picked off a list.

## Names that clash with the Technocracy module

`Acute Senses` and `Iron Will` appear in both supplements at different costs.
The skill resolves the clash in favour of this book — the general list — and
says so rather than silently applying whichever loaded last. See
`_catalog()` in `skills/mage/scripts/character.py`.

## The rule that constrains everything

Flaws are capped at **seven points**, which puts a hard ceiling of **22** on
freebie points (the base 15 plus at most 7 bought back). `character.py validate`
enforces both.

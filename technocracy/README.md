# technocracy — Guide to the Technocracy

Structure and citations only. The values come from your own copy.

## The one scan with a text layer

Of the three books in this repository, this is the only one whose PDF carries
extractable text — about 825,000 characters, against zero for the core rulebook
and zero for the players guide. So its 26 Merits and Flaws are **machine-read**
rather than transcribed by eye:

```bash
python3 ../tools/extract_headed_entries.py --pdf BOOK.pdf --report
```

## Why a new extractor rather than one of the four parsers

byo-rulebook's parsers all read *tables*: an anchor heading, then rows beneath
it. These entries are not a table. Each is a heading of its own —
`Confidence (2 pt Merit)` — with a paragraph under it, spread across a chapter.
There is no anchor to walk down from, so `dot_leader`, `bare_column`,
`linearised_matrix` and `wrapped_pairs` all have nothing to bite on.

`tools/extract_headed_entries.py` handles that shape. It lives in this
repository rather than in the toolkit because the toolkit is a checkout that
should stay pullable; a local edit there is a merge conflict waiting to happen.

## What the text layer did to these headings

Every one of these was seen in this book, and each is in the schema's note:

| Printed | Text layer | Caught by |
|---|---|---|
| `Confidence (2 pt Merit)` | preceded by a form feed, so `^` never matched | splitting on `\f` |
| `Unobtrusive (1 pt Merit)` | `(I pt Merit)` — the 1 read as capital I | the `int` cell type |
| `Technobabbler (1 pt Flaw)` | `(I pt Flaw)` | the `int` cell type |
| `Rose-Colored Mirrorshades (2 pt Flaw)` | name and cost on separate lines | two-line fallback |
| `Faulty Enhancements (2-5 pt Flaw)` | name and cost on separate lines | two-line fallback |
| `Mr. Red Tape (4 pt Flaw)` | `Mr. tied Tape` — `Red` misread | **a human** |

The last one is the point byo-rulebook makes about prose corruption: a misread
*word* inside a label has no declared type, so nothing validates it. It was
found by rendering PDF page 171 and reading the heading, and the repair is
recorded with its reason in `corrections.local.json`.

The first two are the point about cell types. `I pt` would sail past any
validator that only asks "is this a number?" — it is not a number at all, which
is exactly why declaring the cell as `int` catches it.

## Page numbers

`page_offset` is **1**: PDF page = printed page + 1, confirmed by locating a
known heading on PDF 171 (printed 170).

## Scope

These are *additional* to the players guide's general list, for agents of the
Union. Three entries (category `Construct`) come from the cyborg chapter at
printed p.130 and apply to characters who were built rather than born.

`Acute Senses` and `Iron Will` also appear in the players guide at different
costs; the skill prefers the players guide entry and reports the clash.

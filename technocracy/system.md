# Guide to the Technocracy

A **bring-your-own-rulebook** module for the Technocracy sourcebook. Structure
and citations only; the values come from your own copy.

Citations are to **printed** page numbers. In the reference scan, PDF page =
printed page + 1.

## Merits and Flaws

These are *additional* to the players guide's general list, written for agents
of the Union: bureaucratic standing, conditioning, and the particular costs of
being a construct rather than a person.

{{tech:table:merits_flaws@p.130,164-170}}

Three entries in the `Construct` category come from the cyborg chapter rather
than the character chapter, and apply to characters who were built rather than
born. The book notes that any obvious construct takes the **Construct** Flaw,
and that most take two or more Flaws besides.

Several names duplicate the players guide — *Acute Senses*, *Iron Will* — at
Technocracy-specific costs. Take the one from the book your character belongs
to; do not stack them.

## How these were extracted

Unlike the core rulebook and the players guide, this scan has a usable text
layer, so these rows were machine-read rather than transcribed by eye:

```bash
python3 tools/extract_headed_entries.py --pdf BOOK.pdf --report
```

The entries are headings with prose beneath, not a table, so none of the
toolkit's four parsers apply. The extractor handles that shape and coerces each
cost against the toolkit's `int` type — which is what caught the two entries
whose "1 pt" the OCR had read as "I pt". One name needed a human: the text
layer's *Mr. tied Tape* is *Mr. Red Tape* on the page, and a misread word
inside a label is exactly the corruption no cell type can see.

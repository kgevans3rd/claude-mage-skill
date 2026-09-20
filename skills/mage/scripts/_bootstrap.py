#!/usr/bin/env python3
"""
_bootstrap.py — find the byo-rulebook toolkit and bind this skill to its module.

A module is a separate project from the toolkit, so it has to locate one rather
than vendor a copy; copies drift, and every fix then has to be applied twice.
Resolution order, first hit wins:

  1. $GM_TOOLKIT          explicit, wins everywhere; use it in CI
  2. <module>/.toolkit    a one-line pointer file, git-ignored, because where a
                          checkout lives is a property of the machine
  3. <module>/../_toolkit the sibling layout, for a self-contained install

Failure names all three and refuses to start. A skill that silently half-works
without its rulebook values is worse than one that will not run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # skills/mage/scripts
SKILL_DIR = HERE.parent                            # skills/mage
REPO_ROOT = SKILL_DIR.parent.parent                # repository root

# The core rulebook, then the supplements. Each is a separate byo-rulebook
# module because a module is scoped to one book: its title, its page offset and
# its text layer are all properties of that printing, and merging two books
# into one schema would make every citation ambiguous.
#
# Core table ids stay bare ('spheres'); a supplement's are prefixed with its
# schema "system" value ('bos:merits_flaws'), because the two supplements both
# define merits_flaws and silently shadowing one with the other is exactly the
# kind of wrong-rules-for-weeks failure this design exists to prevent.
CORE = "mage2e"
SUPPLEMENTS = ("bookofshadows", "technocracy")


def module_dir() -> Path:
    """The core system module this skill reads its rulebook values from."""
    env = os.environ.get("MAGE_MODULE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return REPO_ROOT / CORE


def supplement_dirs():
    """Every supplement module present on this machine, in declared order.

    Looked for beside the CORE module rather than under REPO_ROOT, so that
    $MAGE_MODULE moves the whole set. Installed as a plugin, this skill runs
    from a git clone that by design carries no rulebook values, and the reader
    points $MAGE_MODULE at their own filled copy; deriving supplements from
    REPO_ROOT instead would resolve the core book and quietly find no Merits,
    Flaws or Rotes, which reads as "not installed" rather than "wrong path".
    """
    roots, seen = [], set()
    for root in (module_dir().parent, REPO_ROOT):
        if root not in seen:
            seen.add(root)
            roots.append(root)
    out = []
    for name in SUPPLEMENTS:
        for root in roots:
            d = root / name
            if (d / "schema.json").is_file():
                out.append((name, d))
                break
    return out


def _candidates(mod: Path):
    env = os.environ.get("GM_TOOLKIT", "").strip()
    if env:
        yield "$GM_TOOLKIT", Path(env).expanduser()
    yield str(mod / ".toolkit"), None              # resolved below
    yield str(mod.parent / "_toolkit"), mod.parent / "_toolkit"


def toolkit_dir(mod: Path) -> Path:
    tried = []
    env = os.environ.get("GM_TOOLKIT", "").strip()
    if env:
        p = Path(env).expanduser()
        tried.append(f"$GM_TOOLKIT={p}")
        for cand in (p / "toolkit", p):
            if (cand / "tables.py").is_file():
                return cand

    pointer = mod / ".toolkit"
    tried.append(str(pointer))
    if pointer.is_file():
        p = Path(pointer.read_text(encoding="utf-8").strip()).expanduser()
        for cand in (p / "toolkit", p):
            if (cand / "tables.py").is_file():
                return cand

    sibling = mod.parent / "_toolkit"
    tried.append(str(sibling))
    for cand in (sibling / "toolkit", sibling):
        if (cand / "tables.py").is_file():
            return cand

    sys.exit(
        "error: could not locate the byo-rulebook toolkit. Tried:\n  "
        + "\n  ".join(tried)
        + "\n\nInstall it with:\n"
        f"  git clone https://github.com/kgevans3rd/byo-rulebook.git {mod.parent / '_toolkit'}\n"
        "or set $GM_TOOLKIT to an existing checkout."
    )


_bound = None


def tables():
    """Return the toolkit's `tables` module, bound to this skill's module dir."""
    global _bound
    if _bound is not None:
        return _bound
    mod = module_dir()
    if not (mod / "schema.json").is_file():
        sys.exit(f"error: no system module at {mod} (set $MAGE_MODULE to override)")
    tk = toolkit_dir(mod)
    sys.path.insert(0, str(tk))
    import tables as T  # noqa: E402
    T.bind(mod)
    _bound = T
    return T


EXIT_UNAVAILABLE = 3


def run(main_fn, argv=None):
    """Run a script's main(), turning a missing-table error into guidance.

    toolkit/tables.py raises TableUnavailable with instructions for filling the
    module. Letting that reach the terminal as a traceback wastes the message —
    the whole point of refusing is that the refusal tells you what to do.
    """
    try:
        return main_fn(argv) if argv is not None else main_fn()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:                      # noqa: BLE001
        if type(exc).__name__ != "TableUnavailable":
            raise
        print(str(exc).rstrip(), file=sys.stderr)
        print("\n  Nothing was rolled. Fill the module and try again.", file=sys.stderr)
        return EXIT_UNAVAILABLE


# ── Supplement modules ────────────────────────────────────────────────────
# toolkit/tables.py is a singleton: bind() points it at one module and every
# later get() reads that one. Rather than fight it, bind each module in turn,
# snapshot what it loaded, and rebind the core at the end. The snapshot is
# taken once and cached, so the rebinding happens exactly once per process.

_registry = None
_prefix_of = {}


def _schema(mod: Path) -> dict:
    import json
    return json.loads((mod / "schema.json").read_text(encoding="utf-8"))


def registry() -> dict:
    """{table_id: rows} across the core and every supplement present.

    Core ids are bare; a supplement's are prefixed with its schema "system".
    """
    global _registry
    if _registry is not None:
        return _registry

    T = tables()                       # binds and loads the core
    merged = dict(T.load())
    _prefix_of.clear()

    for name, mod in supplement_dirs():
        prefix = _schema(mod).get("system") or name
        try:
            T.bind(mod)
            for tid, rows in T.load().items():
                merged[f"{prefix}:{tid}"] = rows
                _prefix_of[f"{prefix}:{tid}"] = name
        finally:
            T.bind(module_dir())       # always leave the core bound
    T.load(refresh=True)

    _registry = merged
    return _registry


def get(table_id: str):
    """A table from the core or any supplement, by its (possibly prefixed) id."""
    reg = registry()
    if table_id in reg:
        return reg[table_id]
    T = tables()
    raise T.TableUnavailable(
        f"\n  The '{table_id}' table is not available on this machine.\n"
        f"\n  Known tables: {', '.join(sorted(reg)) or '(none)'}\n"
        f"\n  Supplement tables are prefixed with their book's namespace,\n"
        f"  e.g. 'bos:merits_flaws'. Fill a module from your own copy with:\n"
        f"      python3 tools/fill_tables.py --module <dir> --pdf /path/to/book.pdf\n")


def sources() -> list:
    """[(module name, schema title, table count)] for everything loaded."""
    reg = registry()
    out = [(CORE, _schema(module_dir())["source"]["title"],
            sum(1 for k in reg if ":" not in k))]
    for name, mod in supplement_dirs():
        prefix = _schema(mod).get("system") or name
        out.append((name, _schema(mod)["source"]["title"],
                    sum(1 for k in reg if k.startswith(prefix + ":"))))
    return out

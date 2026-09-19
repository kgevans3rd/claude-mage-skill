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


def module_dir() -> Path:
    """The system module this skill reads its rulebook values from."""
    env = os.environ.get("MAGE_MODULE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return REPO_ROOT / "mage2e"


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

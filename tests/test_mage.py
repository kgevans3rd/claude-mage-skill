#!/usr/bin/env python3
"""
Tests for the Mage 2e skill.

Split deliberately in two. The dice tests are pure and must pass on a clean
checkout with no rulebook values at all — they are the rules logic. The
table-driven tests skip themselves when the module is unfilled, because on a
fresh clone it will be, and a suite that fails for the expected reason teaches
people to ignore it.

    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "mage" / "scripts"))

import _bootstrap                                     # noqa: E402
from dice import roll_pool, BOTCH, FAILURE, SUCCESS   # noqa: E402


class Fixed:
    """A deterministic stand-in for random, handing out a scripted sequence."""

    def __init__(self, values):
        self.values = list(values)

    def randint(self, a, b):
        return self.values.pop(0)


class TestBotchRule(unittest.TestCase):
    """The printed rule, which is not the one most tables play from memory."""

    def test_ones_cancel_successes(self):
        r = roll_pool(4, 6, rng=Fixed([1, 7, 8, 2]))
        self.assertEqual(r["outcome"], SUCCESS)
        self.assertEqual(r["degree"], 1)          # 2 successes - 1 one

    def test_more_ones_than_successes_botches_even_with_successes(self):
        # The case everyone gets wrong: successes were rolled, and it is still
        # a botch. Paradox depends on this.
        r = roll_pool(5, 6, rng=Fixed([1, 1, 1, 7, 8]))
        self.assertEqual(r["outcome"], BOTCH)
        self.assertEqual(r["degree"], 1)

    def test_equal_ones_and_successes_is_plain_failure(self):
        r = roll_pool(4, 6, rng=Fixed([1, 7, 2, 3]))
        self.assertEqual(r["outcome"], FAILURE)
        self.assertEqual(r["degree"], 0)

    def test_no_successes_no_ones_is_failure_not_botch(self):
        r = roll_pool(3, 6, rng=Fixed([2, 3, 4]))
        self.assertEqual(r["outcome"], FAILURE)

    def test_ones_alone_botch(self):
        r = roll_pool(3, 6, rng=Fixed([1, 3, 4]))
        self.assertEqual(r["outcome"], BOTCH)
        self.assertEqual(r["degree"], 1)

    def test_willpower_adds_one_success_before_cancellation(self):
        r = roll_pool(3, 6, willpower=True, rng=Fixed([1, 3, 4]))
        self.assertEqual(r["outcome"], FAILURE)   # 1 success - 1 one = 0

    def test_tens_always_count(self):
        r = roll_pool(2, 10, rng=Fixed([10, 9]))
        self.assertEqual(r["degree"], 1)

    def test_specialty_rerolls_tens_but_reroll_ones_do_not_punish(self):
        r = roll_pool(1, 6, specialty=True, rng=Fixed([10, 1]))
        self.assertEqual(r["ones"], 0)
        self.assertEqual(r["outcome"], SUCCESS)

    def test_difficulty_bounds_rejected(self):
        with self.assertRaises(ValueError):
            roll_pool(5, 11)
        with self.assertRaises(ValueError):
            roll_pool(5, 1)

    def test_empty_pool_is_a_failure_not_a_crash(self):
        r = roll_pool(0, 6, rng=Fixed([]))
        self.assertEqual(r["outcome"], FAILURE)


def module_filled():
    try:
        T = _bootstrap.tables()
        return len(T.available()) > 0
    except SystemExit:
        return False


@unittest.skipUnless(module_filled(),
                     "module has no rulebook values on this machine — fill it first")
class TestAgainstTheBook(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.T = _bootstrap.tables()
        cls.schema = json.loads(
            (_bootstrap.module_dir() / "schema.json").read_text(encoding="utf-8"))

    def test_every_cited_table_is_present_and_the_right_size(self):
        for spec in self.schema["tables"]:
            with self.subTest(table=spec["id"]):
                rows = self.T.get(spec["id"])
                self.assertTrue(rows, f"{spec['id']} is empty")
                for inv in spec.get("invariants", []):
                    if inv.startswith("rows:"):
                        self.assertEqual(len(rows), int(inv.split(":")[1]))

    def test_every_row_has_the_declared_number_of_columns(self):
        for spec in self.schema["tables"]:
            want = len(spec["columns"])
            for row in self.T.get(spec["id"]):
                self.assertEqual(len(row), want, f"{spec['id']}: {row}")

    def test_casting_difficulty_rises_with_exposure(self):
        import magick
        coin = magick.casting_difficulty({"Forces": 3}, "coincidental")["difficulty"]
        vulg = magick.casting_difficulty({"Forces": 3}, "vulgar")["difficulty"]
        seen = magick.casting_difficulty({"Forces": 3}, "vulgar-witnessed")["difficulty"]
        self.assertLess(coin, vulg)
        self.assertLess(vulg, seen)

    def test_difficulty_is_clamped_to_the_charts_range(self):
        import magick
        low = magick.casting_difficulty({"Mind": 1}, "coincidental", -3)
        self.assertGreaterEqual(low["difficulty"], magick.MIN_DIFFICULTY)
        high = magick.casting_difficulty({"Life": 5}, "vulgar-witnessed", 3)
        self.assertLessEqual(high["difficulty"], magick.MAX_DIFFICULTY)
        self.assertEqual(high["unclamped"], 13)      # and it records what it clamped

    def test_modifier_beyond_the_cap_is_refused(self):
        import magick
        with self.assertRaises(SystemExit):
            magick.casting_difficulty({"Forces": 2}, "vulgar", 4)

    def test_paradox_scales_with_sphere_and_exposure(self):
        import magick
        a = magick.paradox_for_botch("coincidental", 3)["paradox"]
        b = magick.paradox_for_botch("vulgar", 3)["paradox"]
        c = magick.paradox_for_botch("vulgar-witnessed", 3)["paradox"]
        self.assertLess(a, b)
        self.assertLess(b, c)

    def test_nine_spheres_each_with_five_ratings(self):
        rows = self.T.get("spheres")
        names = {r[0] for r in rows}
        self.assertEqual(len(names), 9)
        for n in names:
            self.assertEqual(sorted(int(r[1]) for r in rows if r[0] == n), [1, 2, 3, 4, 5])

    def test_every_tradition_specialty_is_a_real_sphere(self):
        spheres = {r[0] for r in self.T.get("spheres")} | {"Any"}
        for trad, sph in self.T.get("traditions"):
            self.assertIn(sph, spheres, f"{trad} -> {sph}")

    def test_example_character_validates(self):
        import character
        sheet = ROOT / "skills" / "mage" / "templates" / "example-character.json"

        class A:
            file = str(sheet)
            json = True
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            character.cmd_validate(A())
        self.assertTrue(json.loads(buf.getvalue())["ok"], buf.getvalue())

    def test_health_levels_penalties_never_improve_going_down(self):
        seen = 0
        for level, penalty, _ in self.T.get("health_levels"):
            if penalty in ("n/a", "—", ""):
                continue
            self.assertLessEqual(int(penalty), seen)
            seen = int(penalty)


if __name__ == "__main__":
    unittest.main()

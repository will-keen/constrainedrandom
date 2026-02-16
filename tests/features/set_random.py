"""
Test the set_random() API on RandObj.
"""

import random
import unittest

from constrainedrandom import RandObj


class SetRandomAfterInit(unittest.TestCase):
    """
    Test that set_random works when called after __init__ and after adding vars.
    """

    def test_set_random_after_init(self):
        """Create RandObj without random, add vars, call set_random, verify randomization works."""
        r = RandObj()
        r.add_rand_var("a", domain=range(100))
        r.add_rand_var("b", bits=8)

        # Set a seeded random instance after construction
        rng = random.Random(42)
        r.set_random(rng)

        # Should be able to randomize successfully
        r.randomize()
        self.assertIn(r.a, range(100))
        self.assertIn(r.b, range(256))


class SetRandomPropagatesToRandVars(unittest.TestCase):
    """
    Test that set_random propagates the random instance to all RandVar objects.
    """

    def test_set_random_propagates_to_rand_vars(self):
        """Verify each RandVar gets the new random instance."""
        r = RandObj()
        r.add_rand_var("x", domain=range(10))
        r.add_rand_var("y", bits=4)
        r.add_rand_var("z", domain=(1, 2, 3))

        rng = random.Random(99)
        r.set_random(rng)

        # Check that the RandObj itself has the new random
        self.assertIs(r._random, rng)

        # Check that every RandVar has the new random
        for name, rand_var in r._random_vars.items():
            self.assertIs(
                rand_var._random,
                rng,
                f"RandVar '{name}' did not get the new random instance",
            )


class SetRandomReproducible(unittest.TestCase):
    """
    Test that using set_random with the same seed produces the same results.
    """

    def test_set_random_reproducible(self):
        """Same random seed via set_random should produce same results."""

        def make_and_randomize(seed):
            r = RandObj()
            r.add_rand_var("a", domain=range(100))
            r.add_rand_var("b", bits=8)
            r.add_rand_var("c", domain=(10, 20, 30, 40, 50))
            r.set_random(random.Random(seed))
            results = []
            for _ in range(50):
                r.randomize()
                results.append(r.get_results())
            return results

        results_a = make_and_randomize(0)
        results_b = make_and_randomize(0)
        self.assertEqual(
            results_a, results_b, "Results should be identical for the same seed"
        )

        # Different seed should produce different results
        results_c = make_and_randomize(1)
        self.assertNotEqual(
            results_a, results_c, "Results should differ for different seeds"
        )


class SetRandomOverridesInitRandom(unittest.TestCase):
    """
    Test that set_random overrides the random instance passed to __init__.
    """

    def test_set_random_overrides_init_random(self):
        """Create with one random, set_random with another, verify the new one is used."""
        rng_init = random.Random(0)
        rng_override = random.Random(1)

        # Create with rng_init
        r = RandObj(rng_init)
        r.add_rand_var("val", domain=range(1000))

        # Collect results with original random
        r_orig = RandObj(random.Random(0))
        r_orig.add_rand_var("val", domain=range(1000))
        orig_results = []
        for _ in range(20):
            r_orig.randomize()
            orig_results.append(r_orig.get_results())

        # Now override with a different random
        r.set_random(rng_override)

        # Collect results with overridden random
        r_expected = RandObj(random.Random(1))
        r_expected.add_rand_var("val", domain=range(1000))
        expected_results = []
        for _ in range(20):
            r_expected.randomize()
            expected_results.append(r_expected.get_results())

        # Collect results from the object that had set_random called
        override_results = []
        for _ in range(20):
            r.randomize()
            override_results.append(r.get_results())

        # The overridden results should match seed 1, not seed 0
        self.assertEqual(
            override_results,
            expected_results,
            "set_random should cause results to match the new seed",
        )
        self.assertNotEqual(
            override_results,
            orig_results,
            "set_random should override the original random instance",
        )


class SetRandomNoneResets(unittest.TestCase):
    """
    Test that set_random(None) resets to default random module behavior.
    """

    def test_set_random_none_resets(self):
        """set_random(None) should reset to default random module behavior."""
        rng = random.Random(42)
        r = RandObj(rng)
        r.add_rand_var("a", domain=range(100))
        r.add_rand_var("b", bits=8)

        # Verify it starts with our custom random
        self.assertIs(r._random, rng)

        # Reset to None
        r.set_random(None)

        # Verify self._random is now None
        self.assertIsNone(r._random)

        # Verify all RandVars also have None
        for name, rand_var in r._random_vars.items():
            self.assertIsNone(
                rand_var._random,
                f"RandVar '{name}' should have None after set_random(None)",
            )

        # Should still be able to randomize (uses global random module)
        random.seed(123)
        r.randomize()
        self.assertIn(r.a, range(100))
        self.assertIn(r.b, range(256))

        # Verify determinism with global seed
        random.seed(123)
        r2 = RandObj()
        r2.add_rand_var("a", domain=range(100))
        r2.add_rand_var("b", bits=8)
        r2.randomize()
        self.assertEqual(r.a, r2.a)
        self.assertEqual(r.b, r2.b)

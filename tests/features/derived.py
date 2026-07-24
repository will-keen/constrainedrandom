# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Will Keen

'''
Test derived variables.
'''

import unittest
from random import Random

from constrainedrandom import RandObj
from constrainedrandom.internal.randvar import RandVar
from .. import testutils


class DerivedScalar(testutils.RandObjTestBase):
    '''
    Test a derived variable computed from one other variable.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', fn=lambda a: a + 1, rand_var_args=('a',))
        return r

    def check(self, results):
        seen_a = set()
        seen_b = set()
        for result in results:
            self.assertIn(result['a'], range(10), "Base variable wrongly randomized")
            self.assertEqual(result['b'], result['a'] + 1, "Derived value incorrect")
            seen_a.add(result['a'])
            seen_b.add(result['b'])
        self.assertGreaterEqual(len(seen_a), 8, "Base variable did not produce enough distinct values")
        self.assertGreaterEqual(len(seen_b), 8, "Derived variable did not produce enough distinct values")


class DerivedChain(testutils.RandObjTestBase):
    '''
    Test a chain of derived variables (a derived variable depending on
    another derived variable).
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', fn=lambda a: a * 2, rand_var_args=('a',))
        r.add_rand_var('c', fn=lambda b: b + 1, rand_var_args=('b',))
        return r

    def check(self, results):
        seen_a = set()
        seen_c = set()
        for result in results:
            self.assertEqual(result['b'], result['a'] * 2, "Derived value incorrect")
            self.assertEqual(result['c'], result['b'] + 1, "Chained derived value incorrect")
            seen_a.add(result['a'])
            seen_c.add(result['c'])
        self.assertGreaterEqual(len(seen_a), 8, "Base variable did not produce enough distinct values")
        self.assertGreaterEqual(len(seen_c), 8, "End-of-chain derived variable did not produce enough distinct values")


class DerivedCombinedArgs(testutils.RandObjTestBase):
    '''
    Test a derived variable that combines static ``args`` with ``rand_var_args``.
    ``fn`` is called as ``fn(*args, *rand_var_arg_values)``.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('d', fn=lambda scale, a: scale * a, args=(10,), rand_var_args=('a',))
        return r

    def check(self, results):
        seen_d = set()
        for result in results:
            self.assertEqual(result['d'], 10 * result['a'], "Derived value incorrect")
            seen_d.add(result['d'])
        self.assertGreaterEqual(len(seen_d), 8, "Derived variable did not produce enough distinct values")


class DerivedConstrained(testutils.RandObjTestBase):
    '''
    Test a constraint on a derived variable. The constraint must be
    satisfied by re-randomizing the variable it is derived from.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', fn=lambda a: a + 1, rand_var_args=('a',))
        def b_gt_5(b):
            return b > 5
        r.add_constraint(b_gt_5, ('b',))
        return r

    def check(self, results):
        seen_b = set()
        for result in results:
            self.assertEqual(result['b'], result['a'] + 1, "Derived value incorrect")
            self.assertGreater(result['b'], 5, "Constraint on derived variable not respected")
            seen_b.add(result['b'])
        # The constraint allows b in 6..10. Check the observed solutions cover most of the space.
        self.assertGreaterEqual(len(seen_b), 4, "Constrained derived variable did not produce enough distinct values")


class DerivedTmpConstraint(testutils.RandObjTestBase):
    '''
    A temporary single-variable constraint on a derived variable. As for a
    base constraint, it must be satisfied by re-randomizing the variable it
    is derived from.
    '''

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', fn=lambda a: a + 1, rand_var_args=('a',))
        return r

    def check(self, results):
        for result in results:
            self.assertEqual(result['b'], result['a'] + 1, "Derived value incorrect")

    def get_tmp_constraints(self):
        def b_gt_5(b):
            return b > 5
        return [(b_gt_5, ('b',))]

    def tmp_check(self, results):
        for result in results:
            self.assertEqual(result['b'], result['a'] + 1, "Derived value incorrect")
            self.assertGreater(result['b'], 5, "Temporary constraint on derived variable not respected")


class DerivedMultiVar(testutils.RandObjTestBase):
    '''
    Test a multi-variable constraint relating a derived variable and a
    random variable.
    '''

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', fn=lambda a: a + 1, rand_var_args=('a',))
        r.add_rand_var('x', domain=range(20))
        def x_gt_b(x, b):
            return x > b
        r.add_constraint(x_gt_b, ('x', 'b'))
        return r

    def check(self, results):
        seen_x = set()
        seen_b = set()
        for result in results:
            self.assertEqual(result['b'], result['a'] + 1, "Derived value incorrect")
            self.assertGreater(result['x'], result['b'], "Constraint not respected")
            seen_x.add(result['x'])
            seen_b.add(result['b'])
        self.assertGreaterEqual(len(seen_x), 12, "Constrained variable did not produce enough distinct values")
        self.assertGreaterEqual(len(seen_b), 8, "Derived variable did not produce enough distinct values")


class DerivedListLength(testutils.RandObjTestBase):
    '''
    Test a derived variable used as the length of a random list.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('l', fn=lambda a: a + 1, rand_var_args=('a',))
        r.add_rand_var('list', domain=range(2), rand_length='l')
        return r

    def check(self, results):
        seen_lengths = set()
        for result in results:
            self.assertEqual(result['l'], result['a'] + 1, "Derived value incorrect")
            self.assertEqual(len(result['list']), result['l'],
                             "List length does not match its derived length variable")
            for element in result['list']:
                self.assertIn(element, range(2), "List element wrongly randomized")
            seen_lengths.add(result['l'])
        self.assertGreaterEqual(len(seen_lengths), 8, "List length did not produce enough distinct values")


class DerivedFromList(testutils.RandObjTestBase):
    '''
    Test a derived variable computed from a random-length list. This is the
    reverse dependency of DerivedListLength: here the derived variable must be
    computed after the list, whereas there it must be computed before it.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(1, 5))
        r.add_rand_var('mylist', domain=range(10), rand_length='a')
        r.add_rand_var('total', fn=lambda lst: sum(lst), rand_var_args=('mylist',))
        return r

    def check(self, results):
        seen_total = set()
        for result in results:
            self.assertEqual(len(result['mylist']), result['a'], "List length incorrect")
            self.assertEqual(result['total'], sum(result['mylist']), "Derived value incorrect")
            seen_total.add(result['total'])
        self.assertGreaterEqual(len(seen_total), 8, "Derived variable did not produce enough distinct values")


class DerivedChainThroughList(testutils.RandObjTestBase):
    '''
    A derived variable sets a list's length, and another derived variable is
    computed from that list. A constraint on the root input must re-randomize
    the whole chain. A temporary constraint on the end of the chain must
    re-randomize back to the root.
    '''

    ITERATIONS = 200

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(1, 5))
        r.add_rand_var('d', fn=lambda a: a + 1, rand_var_args=('a',))
        r.add_rand_var('lst', domain=range(10), rand_length='d')
        r.add_rand_var('total', fn=lambda lst: sum(lst), rand_var_args=('lst',))
        r.add_rand_var('y', domain=range(1, 5))
        r.add_constraint(lambda a, y: a + y == 5, ('a', 'y'))
        return r

    def check(self, results):
        for result in results:
            self.assertEqual(result['a'] + result['y'], 5, "Constraint not respected")
            self.assertEqual(result['d'], result['a'] + 1, "Derived length incorrect")
            self.assertEqual(len(result['lst']), result['d'], "List length does not match its derived length")
            self.assertEqual(result['total'], sum(result['lst']), "Derived value from list incorrect")

    def get_tmp_constraints(self):
        def total_gt_10(total):
            return total > 10
        return [(total_gt_10, ('total',))]

    def tmp_check(self, results):
        self.check(results)
        for result in results:
            self.assertGreater(result['total'], 10, "Temporary constraint on end of chain not respected")


class DerivedListLengthReverseAlpha(testutils.RandObjTestBase):
    '''
    A derived length variable whose name sorts before the variable it is
    computed from. Alphabetical order would compute it first, before its input
    has a value, so this only works if randomization follows dependency order.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('z', domain=range(1, 5))
        r.add_rand_var('a', fn=lambda z: z, rand_var_args=('z',))
        r.add_rand_var('m', domain=range(10), rand_length='a')
        return r

    def check(self, results):
        seen_lengths = set()
        for result in results:
            self.assertEqual(result['a'], result['z'], "Derived value incorrect")
            self.assertEqual(len(result['m']), result['z'], "List length does not match its derived length variable")
            seen_lengths.add(result['z'])
        self.assertGreaterEqual(len(seen_lengths), 4, "List length did not produce enough distinct values")


class DerivedListLengthConstrained(testutils.RandObjTestBase):
    '''
    A constraint on a derived length variable, satisfied by the naive solver.
    The naive solver must recompute the derived length and resize its list on
    each attempt.
    '''

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('l', fn=lambda a: a + 1, rand_var_args=('a',))
        r.add_rand_var('list', domain=range(2), rand_length='l')
        r.add_rand_var('x', domain=range(20))
        r.add_constraint(lambda x, l: x > l, ('x', 'l'))
        return r

    def check(self, results):
        seen_lengths = set()
        for result in results:
            self.assertEqual(result['l'], result['a'] + 1, "Derived value incorrect")
            self.assertEqual(len(result['list']), result['l'], "List length does not match its derived length variable")
            self.assertGreater(result['x'], result['l'], "Constraint on derived length not respected")
            seen_lengths.add(result['l'])
        self.assertGreaterEqual(len(seen_lengths), 4, "Constrained derived length did not produce enough distinct values")


class DerivedListLengthInputConstrained(testutils.RandObjTestBase):
    '''
    A list whose length is a derived variable, with the constraint on the
    derived variable's input rather than on the derived variable itself.
    The naive solver must re-randomize the list whenever its length is
    recomputed.
    '''

    ITERATIONS = 200

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('x', domain=range(1, 5))
        r.add_rand_var('y', domain=range(1, 5))
        r.add_rand_var('d', fn=lambda x: x + 1, rand_var_args=('x',))
        r.add_rand_var('lst', domain=range(10), rand_length='d')
        r.add_constraint(lambda x, y: x + y == 5, ('x', 'y'))
        return r

    def check(self, results):
        for result in results:
            self.assertEqual(result['x'] + result['y'], 5, "Constraint not respected")
            self.assertEqual(result['d'], result['x'] + 1, "Derived value incorrect")
            self.assertEqual(len(result['lst']), result['d'],
                             "List length does not match its derived length variable")


class WithValuesDerivedLength(testutils.RandObjTestBase):
    '''
    Give a concrete value to a list whose length is a derived variable. As for
    an ordinary length variable, the length follows the pinned list, so
    with_values overrides the value the function would otherwise compute.
    '''

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('l', fn=lambda a: a + 1, rand_var_args=('a',))
        r.add_rand_var('mylist', domain=range(2), rand_length='l')
        return r

    def check(self, results):
        for result in results:
            self.assertEqual(result['l'], result['a'] + 1, "Derived value incorrect")
            self.assertEqual(len(result['mylist']), result['l'], "List length incorrect")

    def get_tmp_values(self):
        return {'mylist': [0, 1, 0]}

    def tmp_check(self, results):
        for result in results:
            self.assertEqual(result['mylist'], [0, 1, 0], "Temp value not respected")
            self.assertEqual(result['l'], 3, "Derived length did not follow the pinned list")
        self.assertTrue(any(result['l'] != result['a'] + 1 for result in results),
                        "Pinned list never overrode the value fn would compute")


class DerivedChainCSP(testutils.RandObjTestBase):
    '''
    A chain of derived variables whose input is solved by the constraint
    solver. The naive solver is disabled so the constraint solver handles
    the derived variables.
    '''

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.set_solver_mode(naive=False)
        r.add_rand_var('x', domain=range(1, 5))
        r.add_rand_var('y', domain=range(1, 5))
        r.add_rand_var('b', fn=lambda x: x * 2, rand_var_args=('x',))
        r.add_rand_var('c', fn=lambda b: b + 1, rand_var_args=('b',))
        r.add_constraint(lambda x, y: x + y == 5, ('x', 'y'))
        return r

    def check(self, results):
        seen_c = set()
        for result in results:
            self.assertEqual(result['x'] + result['y'], 5, "Constraint not respected")
            self.assertEqual(result['b'], result['x'] * 2, "Derived value incorrect")
            self.assertEqual(result['c'], result['b'] + 1, "Chained derived value incorrect")
            seen_c.add(result['c'])
        self.assertGreaterEqual(len(seen_c), 3, "End-of-chain derived variable did not produce enough distinct values")


class DerivedConstrainedCSP(testutils.RandObjTestBase):
    '''
    A constraint on a derived variable with the naive solver disabled. The
    inputs are constrained so that the deferred check always passes.
    '''

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.set_solver_mode(naive=False)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('x', domain=range(1, 5))
        r.add_rand_var('b', fn=lambda a: a + 1, rand_var_args=('a',))
        # a + x == 10 forces a into 6..9, so b > 5 always holds.
        r.add_constraint(lambda a, x: a + x == 10, ('a', 'x'))
        r.add_constraint(lambda b: b > 5, ('b',))
        return r

    def check(self, results):
        seen_b = set()
        for result in results:
            self.assertEqual(result['a'] + result['x'], 10, "Constraint not respected")
            self.assertEqual(result['b'], result['a'] + 1, "Derived value incorrect")
            self.assertGreater(result['b'], 5, "Constraint on derived variable not respected")
            seen_b.add(result['b'])
        self.assertGreaterEqual(len(seen_b), 3, "Constrained derived variable did not produce enough distinct values")


class DerivedRandVarErrors(unittest.TestCase):
    '''
    ``RandVar`` raises if ``set_rand_var_args`` is called on a non-derived
    variable, or if a derived variable is randomized before it is called.
    ``RandObj`` validates before reaching these paths, so they are tested on
    a ``RandVar`` directly. A plain ``TestCase`` suffices as they do not call
    ``randomize()``.
    '''

    def make_randvar(self, **kwargs):
        return RandVar(
            name='x',
            max_iterations=100,
            max_domain_size=1 << 10,
            disable_naive_list_solver=False,
            **kwargs,
        )

    def test_set_rand_var_args_on_non_derived(self):
        var = self.make_randvar(domain=range(10))
        with self.assertRaisesRegex(RuntimeError, 'not marked as derived'):
            var.set_rand_var_args({'a': 1})

    def test_randomize_before_set_rand_var_args(self):
        var = self.make_randvar(fn=lambda a: a + 1, rand_var_args=('a',))
        with self.assertRaisesRegex(RuntimeError, 'before set_rand_var_args'):
            var.randomize([], False)


class DerivedStochastic(unittest.TestCase):
    '''
    Test a derived variable whose function itself uses randomness.

    Uses a plain ``TestCase`` rather than a ``RandObjTestBase``: the function
    must draw from the object's own generator, which the base test's deepcopy
    check cannot preserve. Repeatability is verified directly here instead.
    '''

    def make_randobj(self, seed):
        rand = Random(seed)
        r = RandObj(rand)
        r.add_rand_var('a', domain=range(1, 10))
        def randrange_a(a):
            return rand.randrange(a)
        r.add_rand_var('b', fn=randrange_a, rand_var_args=('a',))
        return r

    def results(self, seed):
        r = self.make_randobj(seed)
        out = []
        for _ in range(100):
            r.randomize()
            out.append((r.a, r.b))
        return out

    def test_in_range(self):
        for a, b in self.results(0):
            self.assertIn(a, range(1, 10))
            self.assertIn(b, range(a), "Derived value out of range")

    def test_spread(self):
        seen_a = set()
        seen_b = set()
        for a, b in self.results(0):
            seen_a.add(a)
            seen_b.add(b)
        self.assertGreaterEqual(len(seen_a), 7, "Base variable did not produce enough distinct values")
        self.assertGreaterEqual(len(seen_b), 6, "Derived variable did not produce enough distinct values")

    def test_repeatable(self):
        self.assertEqual(self.results(0), self.results(0),
                         "Results not repeatable for the same seed")

    def test_seeds_differ(self):
        self.assertNotEqual(self.results(0), self.results(1),
                            "Results identical for different seeds")

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Will Keen

"""
Test derived variables.
"""

import unittest
from random import Random

from constrainedrandom import RandObj
from constrainedrandom.internal.randvar import RandVar

from .. import testutils


class DerivedScalar(testutils.RandObjTestBase):
    """
    Test a derived variable computed from one other variable.
    """

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
            self.assertIn(result['a'], range(10), 'Base variable out of domain')
            self.assertEqual(result['b'], result['a'] + 1, 'Derived value incorrect')
            seen_a.add(result['a'])
            seen_b.add(result['b'])
        self.assertGreaterEqual(
            len(seen_a), 8, 'Base variable did not produce enough distinct values'
        )
        self.assertGreaterEqual(
            len(seen_b), 8, 'Derived variable did not produce enough distinct values'
        )


class DerivedChain(testutils.RandObjTestBase):
    """
    Test a chain of derived variables.
    """

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
            self.assertEqual(result['b'], result['a'] * 2, 'Derived value incorrect')
            self.assertEqual(result['c'], result['b'] + 1, 'Chained derived value incorrect')
            seen_a.add(result['a'])
            seen_c.add(result['c'])
        self.assertGreaterEqual(
            len(seen_a), 8, 'Base variable did not produce enough distinct values'
        )
        self.assertGreaterEqual(
            len(seen_c),
            8,
            'Last derived variable in the chain did not produce enough distinct values',
        )


class DerivedCombinedArgs(testutils.RandObjTestBase):
    """
    Test a derived variable with both ``args`` and ``rand_var_args``.
    """

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('d', fn=lambda scale, a: scale * a, args=(10,), rand_var_args=('a',))
        return r

    def check(self, results):
        seen_d = set()
        for result in results:
            self.assertEqual(result['d'], 10 * result['a'], 'Derived value incorrect')
            seen_d.add(result['d'])
        self.assertGreaterEqual(
            len(seen_d), 8, 'Derived variable did not produce enough distinct values'
        )


class DerivedConstrained(testutils.RandObjTestBase):
    """
    Test a constraint on a derived variable.
    """

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
            self.assertEqual(result['b'], result['a'] + 1, 'Derived value incorrect')
            self.assertGreater(result['b'], 5, 'Constraint on derived variable not respected')
            seen_b.add(result['b'])
        # The constraint allows b in 6..10. Check most of those values are observed.
        self.assertGreaterEqual(
            len(seen_b), 4, 'Constrained derived variable did not produce enough distinct values'
        )


class DerivedTmpConstraint(testutils.RandObjTestBase):
    """
    Test a temporary constraint on a derived variable.
    """

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', fn=lambda a: a + 1, rand_var_args=('a',))
        return r

    def check(self, results):
        for result in results:
            self.assertEqual(result['b'], result['a'] + 1, 'Derived value incorrect')

    def get_tmp_constraints(self):
        def b_gt_5(b):
            return b > 5

        return [(b_gt_5, ('b',))]

    def tmp_check(self, results):
        for result in results:
            self.assertEqual(result['b'], result['a'] + 1, 'Derived value incorrect')
            self.assertGreater(
                result['b'], 5, 'Temporary constraint on derived variable not respected'
            )


class DerivedMultiVar(testutils.RandObjTestBase):
    """
    Test a multi-variable constraint relating a derived variable and a
    random variable.
    """

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
            self.assertEqual(result['b'], result['a'] + 1, 'Derived value incorrect')
            self.assertGreater(result['x'], result['b'], 'Constraint not respected')
            seen_x.add(result['x'])
            seen_b.add(result['b'])
        self.assertGreaterEqual(
            len(seen_x), 12, 'Constrained variable did not produce enough distinct values'
        )
        self.assertGreaterEqual(
            len(seen_b), 8, 'Derived variable did not produce enough distinct values'
        )


class DerivedListLength(testutils.RandObjTestBase):
    """
    Test a derived variable used as the length of a random list.
    """

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
            self.assertEqual(result['l'], result['a'] + 1, 'Derived value incorrect')
            self.assertEqual(
                len(result['list']),
                result['l'],
                'List length does not match its derived length variable',
            )
            for element in result['list']:
                self.assertIn(element, range(2), 'List element out of domain')
            seen_lengths.add(result['l'])
        self.assertGreaterEqual(
            len(seen_lengths), 8, 'List length did not produce enough distinct values'
        )


class DerivedFromList(testutils.RandObjTestBase):
    """
    Test a derived variable computed from a random-length list.
    """

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
            self.assertEqual(len(result['mylist']), result['a'], 'List length incorrect')
            self.assertEqual(result['total'], sum(result['mylist']), 'Derived value incorrect')
            seen_total.add(result['total'])
        self.assertGreaterEqual(
            len(seen_total), 8, 'Derived variable did not produce enough distinct values'
        )


class DerivedChainThroughList(testutils.RandObjTestBase):
    """
    Test a derived variable that sets a list's length, and another derived
    variable computed from that list.
    """

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
            self.assertEqual(result['a'] + result['y'], 5, 'Constraint not respected')
            self.assertEqual(result['d'], result['a'] + 1, 'Derived length incorrect')
            self.assertEqual(
                len(result['lst']), result['d'], 'List length does not match its derived length'
            )
            self.assertEqual(
                result['total'], sum(result['lst']), 'Derived value from list incorrect'
            )

    def get_tmp_constraints(self):
        def total_gt_10(total):
            return total > 10

        return [(total_gt_10, ('total',))]

    def tmp_check(self, results):
        self.check(results)
        for result in results:
            self.assertGreater(
                result['total'], 10, 'Temporary constraint on end of chain not respected'
            )


class DerivedListLengthReverseAlpha(testutils.RandObjTestBase):
    """
    Test a derived length variable whose name sorts before the name of its input.
    """

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
            self.assertEqual(result['a'], result['z'], 'Derived value incorrect')
            self.assertEqual(
                len(result['m']),
                result['z'],
                'List length does not match its derived length variable',
            )
            seen_lengths.add(result['z'])
        self.assertGreaterEqual(
            len(seen_lengths), 4, 'List length did not produce enough distinct values'
        )


class DerivedListLengthConstrained(testutils.RandObjTestBase):
    """
    Test a constraint on a derived length variable.
    """

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('l', fn=lambda a: a + 1, rand_var_args=('a',))
        r.add_rand_var('list', domain=range(2), rand_length='l')
        r.add_rand_var('x', domain=range(20))
        r.add_constraint(lambda x, length: x > length, ('x', 'l'))
        return r

    def check(self, results):
        seen_lengths = set()
        for result in results:
            self.assertEqual(result['l'], result['a'] + 1, 'Derived value incorrect')
            self.assertEqual(
                len(result['list']),
                result['l'],
                'List length does not match its derived length variable',
            )
            self.assertGreater(
                result['x'], result['l'], 'Constraint on derived length not respected'
            )
            seen_lengths.add(result['l'])
        self.assertGreaterEqual(
            len(seen_lengths),
            4,
            'Constrained derived length did not produce enough distinct values',
        )


class DerivedListLengthInputConstrained(testutils.RandObjTestBase):
    """
    Test a constraint on the input of a derived length variable.
    """

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
            self.assertEqual(result['x'] + result['y'], 5, 'Constraint not respected')
            self.assertEqual(result['d'], result['x'] + 1, 'Derived value incorrect')
            self.assertEqual(
                len(result['lst']),
                result['d'],
                'List length does not match its derived length variable',
            )


class WithValuesDerivedLength(testutils.RandObjTestBase):
    """
    Test giving a concrete value to a list whose length is a derived variable.
    """

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('l', fn=lambda a: a + 1, rand_var_args=('a',))
        r.add_rand_var('mylist', domain=range(2), rand_length='l')
        return r

    def check(self, results):
        for result in results:
            self.assertEqual(result['l'], result['a'] + 1, 'Derived value incorrect')
            self.assertEqual(len(result['mylist']), result['l'], 'List length incorrect')

    def get_tmp_values(self):
        return {'mylist': [0, 1, 0]}

    def tmp_check(self, results):
        for result in results:
            self.assertEqual(result['mylist'], [0, 1, 0], 'Temp value not respected')
            self.assertEqual(result['l'], 3, 'Derived length not set from the given list')
        self.assertTrue(
            any(result['l'] != result['a'] + 1 for result in results),
            'Given list never overrode the value fn would compute',
        )


class DerivedChainCSP(testutils.RandObjTestBase):
    """
    Test a chain of derived variables with the naive solver disabled.
    """

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
            self.assertEqual(result['x'] + result['y'], 5, 'Constraint not respected')
            self.assertEqual(result['b'], result['x'] * 2, 'Derived value incorrect')
            self.assertEqual(result['c'], result['b'] + 1, 'Chained derived value incorrect')
            seen_c.add(result['c'])
        self.assertGreaterEqual(
            len(seen_c),
            3,
            'Last derived variable in the chain did not produce enough distinct values',
        )


class DerivedConstrainedCSP(testutils.RandObjTestBase):
    """
    Test a constraint on a derived variable with the naive solver disabled.
    """

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
            self.assertEqual(result['a'] + result['x'], 10, 'Constraint not respected')
            self.assertEqual(result['b'], result['a'] + 1, 'Derived value incorrect')
            self.assertGreater(result['b'], 5, 'Constraint on derived variable not respected')
            seen_b.add(result['b'])
        self.assertGreaterEqual(
            len(seen_b), 3, 'Constrained derived variable did not produce enough distinct values'
        )


class DerivedTwoInputs(testutils.RandObjTestBase):
    """
    Test a derived variable of two inputs.
    """

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', domain=range(10))
        r.add_rand_var('d', fn=lambda a, b: a * 10 + b, rand_var_args=('a', 'b'))
        return r

    def check(self, results):
        seen_d = set()
        for result in results:
            self.assertEqual(result['d'], result['a'] * 10 + result['b'], 'Derived value incorrect')
            seen_d.add(result['d'])
        self.assertGreaterEqual(
            len(seen_d), 50, 'Derived variable did not produce enough distinct values'
        )


class DerivedTwoInputsOneConstrained(DerivedTwoInputs):
    """
    Test a derived variable of two inputs with a constraint on one of them.
    """

    def get_randobj(self, *args):
        r = super().get_randobj(*args)
        r.add_constraint(lambda a: a > 5, ('a',))
        return r

    def check(self, results):
        seen_b = set()
        seen_d = set()
        for result in results:
            self.assertEqual(result['d'], result['a'] * 10 + result['b'], 'Derived value incorrect')
            self.assertGreater(result['a'], 5, 'Constraint not respected')
            seen_b.add(result['b'])
            seen_d.add(result['d'])
        self.assertGreaterEqual(
            len(seen_b), 9, 'Unconstrained input did not produce enough distinct values'
        )
        self.assertGreaterEqual(
            len(seen_d), 30, 'Derived variable did not produce enough distinct values'
        )


class DerivedTwoInputsConstrained(testutils.RandObjTestBase):
    """
    Test a constraint on a derived variable of two inputs.
    """

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', domain=range(10))
        r.add_rand_var('x', domain=range(1, 5))
        r.add_rand_var('d', fn=lambda a, b: a * 10 + b, rand_var_args=('a', 'b'))
        # a + x == 10 forces a into 6..9, so d >= 50 always holds.
        r.add_constraint(lambda a, x: a + x == 10, ('a', 'x'))
        r.add_constraint(lambda d: d >= 50, ('d',))
        return r

    def check(self, results):
        seen_a = set()
        seen_b = set()
        for result in results:
            self.assertEqual(result['d'], result['a'] * 10 + result['b'], 'Derived value incorrect')
            self.assertEqual(result['a'] + result['x'], 10, 'Constraint not respected')
            self.assertGreaterEqual(result['d'], 50, 'Constraint on derived variable not respected')
            seen_a.add(result['a'])
            seen_b.add(result['b'])
        self.assertGreaterEqual(
            len(seen_a), 3, 'First input did not produce enough distinct values'
        )
        self.assertGreaterEqual(
            len(seen_b), 8, 'Second input did not produce enough distinct values'
        )


class DerivedTwoInputsConstrainedSparse(DerivedTwoInputsConstrained):
    """
    The same problem with the naive solver disabled.
    """

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = super().get_randobj(*args)
        r.set_solver_mode(naive=False)
        return r


class DerivedTwoInputsConstrainedThorough(DerivedTwoInputsConstrained):
    """
    The same problem with only the thorough solver enabled.
    """

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = super().get_randobj(*args)
        r.set_solver_mode(naive=False, sparse=False)
        return r


class DerivedTwoInputsWithValues(DerivedTwoInputs):
    """
    Test a derived variable of two inputs, one given a concrete value.
    """

    def get_tmp_values(self):
        return {'b': 3}

    def tmp_check(self, results):
        for result in results:
            self.assertEqual(result['b'], 3, 'Temp value not respected')
            self.assertEqual(result['d'], result['a'] * 10 + 3, 'Derived value incorrect')


class DerivedRepeatedInput(testutils.RandObjTestBase):
    """
    Test the same input named twice in ``rand_var_args``.
    """

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('d', fn=lambda x, y: x * 10 + y, rand_var_args=('a', 'a'))
        return r

    def check(self, results):
        for result in results:
            self.assertEqual(result['d'], result['a'] * 11, 'Derived value incorrect')


class DerivedDiamond(testutils.RandObjTestBase):
    """
    Test two derived variables sharing an input, and a third derived from both.
    """

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('x', domain=range(1, 5))
        r.add_rand_var('b', fn=lambda a: a * 2, rand_var_args=('a',))
        r.add_rand_var('c', fn=lambda a: a + 1, rand_var_args=('a',))
        r.add_rand_var('d', fn=lambda b, c: b + c, rand_var_args=('b', 'c'))
        r.add_constraint(lambda a, x: a + x == 10, ('a', 'x'))
        return r

    def check(self, results):
        seen_d = set()
        for result in results:
            self.assertEqual(result['a'] + result['x'], 10, 'Constraint not respected')
            self.assertEqual(result['b'], result['a'] * 2, 'Derived value incorrect')
            self.assertEqual(result['c'], result['a'] + 1, 'Derived value incorrect')
            self.assertEqual(
                result['d'],
                result['a'] * 3 + 1,
                'Derived value at the end of the diamond incorrect',
            )
            seen_d.add(result['d'])
        self.assertGreaterEqual(
            len(seen_d), 3, 'Derived variable did not produce enough distinct values'
        )


class DerivedDiamondSparse(DerivedDiamond):
    """
    The same problem with the naive solver disabled.
    """

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = super().get_randobj(*args)
        r.set_solver_mode(naive=False)
        return r


class DerivedDiamondThorough(DerivedDiamond):
    """
    The same problem with only the thorough solver enabled.
    """

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = super().get_randobj(*args)
        r.set_solver_mode(naive=False, sparse=False)
        return r


class DerivedMixedInputs(testutils.RandObjTestBase):
    """
    Test a derived variable whose inputs are a plain variable, a random-length
    list and another derived variable.
    """

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('n', domain=range(1, 4))
        r.add_rand_var('lst', domain=range(5), rand_length='n')
        r.add_rand_var('e', fn=lambda a: a + 1, rand_var_args=('a',))
        r.add_rand_var(
            'd', fn=lambda a, lst, e: a * 100 + sum(lst) * 10 + e, rand_var_args=('a', 'lst', 'e')
        )
        return r

    def check(self, results):
        for result in results:
            self.assertEqual(len(result['lst']), result['n'], 'List length incorrect')
            self.assertEqual(result['e'], result['a'] + 1, 'Derived value incorrect')
            self.assertEqual(
                result['d'],
                result['a'] * 100 + sum(result['lst']) * 10 + result['e'],
                'Derived value from mixed inputs incorrect',
            )


class DerivedChainTwoInputs(testutils.RandObjTestBase):
    """
    Test a chain of derived variables, each of two inputs.
    """

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', domain=range(10))
        r.add_rand_var('c', fn=lambda a, b: a + b, rand_var_args=('a', 'b'))
        r.add_rand_var('d', fn=lambda c, a: c * a, rand_var_args=('c', 'a'))
        r.add_rand_var('e', fn=lambda d, c: d - c, rand_var_args=('d', 'c'))
        return r

    def check(self, results):
        for result in results:
            a, b = result['a'], result['b']
            self.assertEqual(result['c'], a + b, 'First derived value incorrect')
            self.assertEqual(result['d'], (a + b) * a, 'Second derived value incorrect')
            self.assertEqual(result['e'], (a + b) * a - (a + b), 'Third derived value incorrect')


class DerivedRandVarErrors(unittest.TestCase):
    """
    Test the errors ``RandVar`` raises for misuse of ``set_rand_var_args``.
    """

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
    """
    Test a derived variable whose function itself uses randomness.
    """

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
            self.assertIn(b, range(a), 'Derived value out of range')

    def test_spread(self):
        seen_a = set()
        seen_b = set()
        for a, b in self.results(0):
            seen_a.add(a)
            seen_b.add(b)
        self.assertGreaterEqual(
            len(seen_a), 7, 'Base variable did not produce enough distinct values'
        )
        self.assertGreaterEqual(
            len(seen_b), 6, 'Derived variable did not produce enough distinct values'
        )

    def test_repeatable(self):
        self.assertEqual(
            self.results(0), self.results(0), 'Results not repeatable for the same seed'
        )

    def test_seeds_differ(self):
        self.assertNotEqual(
            self.results(0), self.results(1), 'Results identical for different seeds'
        )

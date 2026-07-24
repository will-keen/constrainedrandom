# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Will Keen

'''
Test ordering hints.
'''

import unittest
from random import Random

from constrainedrandom import RandObj
from .. import testutils


class MultiOrder(testutils.RandObjTestBase):
    '''
    Test a problem that benefits greatly from being solved in a certain order.
    '''

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var("a", domain=range(100), order=0)
        r.add_rand_var("b", domain=range(100), order=1)
        def mul_lt1000(a, b):
            return a * b < 1000
        r.add_constraint(mul_lt1000, ('a', 'b'))
        r.add_rand_var("c", domain=range(100), order=2)
        def sum_lt100(a, b, c):
            return a + b + c < 100
        r.add_constraint(sum_lt100, ('a', 'b', 'c'))
        return r

    def check(self, results):
        for result in results:
            self.assertLess(result['a'] * result['b'], 1000, f'Check failed for {result=}')
            self.assertLess(result['a'] + result['b'] + result['c'], 100, f'Check failed for {result=}')


class OrderIgnoredByNaive(unittest.TestCase):
    '''
    Ordering hints must not affect the naive solver. Two ``RandObj`` instances
    that differ only in their ``order`` hints must produce identical results for
    the same seed when the naive solver is used.

    This compares two separate ``RandObj`` instances, so it cannot use
    ``RandObjTestBase``, which tests a single instance.
    '''

    def results(self, order_a, order_b, constrained):
        r = RandObj(Random(0))
        r.add_rand_var('a', domain=range(100), order=order_a)
        r.add_rand_var('b', domain=range(100), order=order_b)
        if constrained:
            # An easy constraint the naive solver always satisfies, so the
            # problem never reaches the CSP solver.
            r.add_constraint(lambda a, b: a < b, ('a', 'b'))
        out = []
        for _ in range(100):
            r.randomize()
            out.append(r.get_results())
        return out

    def test_order_ignored_no_constraints(self):
        testutils.assertListOfDictsEqual(
            self, self.results(0, 1, False), self.results(1, 0, False),
            "Ordering hints changed naive randomization results")

    def test_order_ignored_with_constraint(self):
        testutils.assertListOfDictsEqual(
            self, self.results(0, 1, True), self.results(1, 0, True),
            "Ordering hints changed naive randomization results")

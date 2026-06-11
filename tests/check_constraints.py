# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Will Keen

'''
Test check_constraints function from utils.
'''

import unittest

from constrainedrandom.utils import check_constraints


def x_lt_y(x, y):
    return x < y

def x_nonzero(x):
    return x != 0


class CheckConstraintsTests(unittest.TestCase):
    '''
    Test the ``check_constraints`` function from ``utils``.
    '''

    CONSTRAINTS = [
        (x_lt_y, ('x', 'y')),
        (x_nonzero, ('x',)),
    ]

    def test_satisfied(self):
        self.assertTrue(check_constraints(self.CONSTRAINTS, {'x': 1, 'y': 2}))

    def test_unsatisfied(self):
        # First constraint fails.
        self.assertFalse(check_constraints(self.CONSTRAINTS, {'x': 2, 'y': 1}))
        # Second constraint fails.
        self.assertFalse(check_constraints(self.CONSTRAINTS, {'x': 0, 'y': 1}))

    def test_no_constraints(self):
        self.assertTrue(check_constraints([], {'x': 1}))

    def test_early_exit(self):
        # Constraints after the first failing one must not be called.
        def fails(x):
            return False
        def must_not_run(x):
            self.fail("constraint evaluated after an earlier one failed")
        constraints = [(fails, ('x',)), (must_not_run, ('x',))]
        self.assertFalse(check_constraints(constraints, {'x': 1}))

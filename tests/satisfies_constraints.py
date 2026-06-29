# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Will Keen

'''
Test satisfies_constraints method of RandVar.
'''

import unittest

from constrainedrandom.internal.randvar import RandVar
from constrainedrandom.utils import unique


def make_var(**kwargs) -> RandVar:
    return RandVar(
        name='x',
        max_iterations=100,
        max_domain_size=1 << 10,
        disable_naive_list_solver=False,
        **kwargs,
    )


class SatisfiesConstraintsTests(unittest.TestCase):
    '''
    Test the ``satisfies_constraints`` method of ``RandVar``.
    '''

    def test_no_constraints(self):
        self.assertEqual(make_var(domain=range(10)).satisfies_constraints(0), True)

    def test_scalar(self):
        var = make_var(domain=range(10), constraints=[lambda v: v < 5])
        self.assertEqual(var.satisfies_constraints(3), True)
        self.assertEqual(var.satisfies_constraints(7), False)

    def test_scalar_multiple_constraints(self):
        var = make_var(domain=range(20), constraints=[lambda v: v > 5, lambda v: v < 15])
        self.assertEqual(var.satisfies_constraints(10), True)
        self.assertEqual(var.satisfies_constraints(3), False)
        self.assertEqual(var.satisfies_constraints(18), False)

    def test_fixed_length_element_constraint(self):
        var = make_var(domain=range(10), length=3, constraints=[lambda v: v != 7])
        self.assertEqual(var.satisfies_constraints([1, 2, 3]), True)
        self.assertEqual(var.satisfies_constraints([1, 7, 3]), False)

    def test_fixed_length_list_constraint(self):
        var = make_var(domain=range(10), length=3,
                       list_constraints=[unique])
        self.assertEqual(var.satisfies_constraints([1, 2, 3]), True)
        self.assertEqual(var.satisfies_constraints([1, 1, 2]), False)

    def test_element_and_list_constraints(self):
        var = make_var(domain=range(10), length=3, constraints=[lambda v: v != 7],
                       list_constraints=[unique])
        self.assertEqual(var.satisfies_constraints([1, 2, 3]), True)
        # element constraint violated
        self.assertEqual(var.satisfies_constraints([1, 7, 3]), False)
        # list constraint violated
        self.assertEqual(var.satisfies_constraints([1, 1, 2]), False)

    def test_rand_length_element_constraint(self):
        var = make_var(domain=range(10), rand_length='n', constraints=[lambda v: v != 7])
        # any length is allowed by satisfies_constraints
        self.assertEqual(var.satisfies_constraints([1, 2, 3, 4, 5]), True)
        self.assertEqual(var.satisfies_constraints([1, 7]), False)

    def test_rand_length_list_constraint(self):
        var = make_var(domain=range(10), rand_length='n',
                       list_constraints=[lambda lst: sum(lst) < 10])
        self.assertEqual(var.satisfies_constraints([1, 2, 3]), True)
        self.assertEqual(var.satisfies_constraints([5, 6]), False)

    def test_scalar_given_list(self):
        var = make_var(domain=range(10), length=3, constraints=[lambda v: v != 7])
        self.assertEqual(var.satisfies_constraints(5), False)

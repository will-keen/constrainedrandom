# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Will Keen

'''
Test value_in_domain method of RandVar.
'''

import unittest

from enum import Enum, IntEnum

from constrainedrandom.internal.randvar import RandVar


def make_var(**kwargs) -> RandVar:
    return RandVar(
        name='x',
        max_iterations=100,
        max_domain_size=1 << 10,
        disable_naive_list_solver=False,
        **kwargs,
    )


class ValueInDomainTests(unittest.TestCase):
    '''
    Test the ``value_in_domain`` method of ``RandVar``.
    '''

    def test_range(self):
        var = make_var(domain=range(0, 10))
        self.assertEqual(var.value_in_domain(0), True)
        self.assertEqual(var.value_in_domain(9), True)
        self.assertEqual(var.value_in_domain(10), False)
        self.assertEqual(var.value_in_domain(-1), False)
        self.assertEqual(var.value_in_domain("A"), False)
        self.assertEqual(var.value_in_domain(1.1), False)

    def test_range_with_step(self):
        var = make_var(domain=range(0, 10, 2))
        self.assertEqual(var.value_in_domain(4), True)
        self.assertEqual(var.value_in_domain(5), False)
        self.assertEqual(var.value_in_domain(-1), False)
        self.assertEqual(var.value_in_domain("A"), False)
        self.assertEqual(var.value_in_domain(1.1), False)

    def test_list(self):
        var = make_var(domain=[2, 3, 5, 7])
        self.assertEqual(var.value_in_domain(5), True)
        self.assertEqual(var.value_in_domain(4), False)
        self.assertEqual(var.value_in_domain("A"), False)

    def test_tuple(self):
        var = make_var(domain=(2, 3, 5, 7))
        self.assertEqual(var.value_in_domain(7), True)
        self.assertEqual(var.value_in_domain(0), False)
        self.assertEqual(var.value_in_domain("A"), False)

    def test_dist_scalar_keys(self):
        var = make_var(domain={0: 50, 1: 50})
        self.assertEqual(var.value_in_domain(0), True)
        self.assertEqual(var.value_in_domain(1), True)
        self.assertEqual(var.value_in_domain(2), False)
        self.assertEqual(var.value_in_domain(0.5), False)

    def test_dist_range_key(self):
        var = make_var(domain={0: 50, range(1, 4): 50})
        self.assertEqual(var.value_in_domain(0), True)
        self.assertEqual(var.value_in_domain(2), True)
        self.assertEqual(var.value_in_domain(4), False)
        self.assertEqual(var.value_in_domain(0.5), False)

    def test_dist_non_int_key(self):
        var = make_var(domain={0: 50, 'foo': 50})
        self.assertEqual(var.value_in_domain('foo'), True)
        self.assertEqual(var.value_in_domain('bar'), False)
        self.assertEqual(var.value_in_domain(0), True)
        self.assertEqual(var.value_in_domain(1), False)

    def test_bits(self):
        var = make_var(bits=4)
        self.assertEqual(var.value_in_domain(15), True)
        self.assertEqual(var.value_in_domain(16), False)
        self.assertEqual(var.value_in_domain(-1), False)
        self.assertEqual(var.value_in_domain("A"), False)

    def test_bits_large(self):
        var = make_var(bits=64)
        self.assertEqual(var.value_in_domain(5), True)
        self.assertEqual(var.value_in_domain(-1), False)
        self.assertEqual(var.value_in_domain(1 << 64), False)
        self.assertEqual(var.value_in_domain("A"), False)

    def test_enum(self):
        class MyEnum(Enum):
            A = 1
            B = 2
            C = 3
        var = make_var(domain=MyEnum)
        self.assertEqual(var.value_in_domain(MyEnum.A), True)
        self.assertEqual(var.value_in_domain(MyEnum.B), True)
        self.assertEqual(var.value_in_domain(MyEnum.C), True)
        self.assertEqual(var.value_in_domain(0), False)
        self.assertEqual(var.value_in_domain(1), False)
        self.assertEqual(var.value_in_domain("A"), False)

    def test_intenum(self):
        class MyIntEnum(IntEnum):
            A = 1
            B = 2
            C = 3
        var = make_var(domain=MyIntEnum)
        self.assertEqual(var.value_in_domain(MyIntEnum.A), True)
        self.assertEqual(var.value_in_domain(MyIntEnum.B), True)
        self.assertEqual(var.value_in_domain(MyIntEnum.C), True)
        self.assertEqual(var.value_in_domain(0), False)
        self.assertEqual(var.value_in_domain(1), True)
        self.assertEqual(var.value_in_domain("A"), False)

    def test_fixed_length_list(self):
        var = make_var(domain=range(10), length=3)
        self.assertEqual(var.value_in_domain([1, 2, 3]), True)
        # wrong length
        self.assertEqual(var.value_in_domain([1, 2]), False)
        # bad element
        self.assertEqual(var.value_in_domain([1, 2, 99]), False)
        # not a list
        self.assertEqual(var.value_in_domain(5), False)

    def test_rand_length_list(self):
        var = make_var(domain=range(10), rand_length='n')
        # any length
        self.assertEqual(var.value_in_domain([1, 2, 3, 4]), True)
        self.assertEqual(var.value_in_domain([]), True)
        # bad element
        self.assertEqual(var.value_in_domain([1, 99]), False)
        # not a list
        self.assertEqual(var.value_in_domain(5), False)

    def test_scalar_given_list(self):
        self.assertEqual(make_var(domain=range(10)).value_in_domain([1, 2]), False)
        self.assertEqual(make_var(bits=4).value_in_domain([1, 2]), False)
        self.assertEqual(make_var(domain={0: 50, 1: 50}).value_in_domain([0, 1]), False)

# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Test error cases.
'''

from random import Random

from constrainedrandom import RandObj, RandomizationError

from .basic import MultiSum
from .. import testutils


class ImpossibleThorough(MultiSum):
    '''
    Test the thorough solver for a problem that will always fail.

    The thorough solver almost always converges, so it's very
    hard to construct a problem 'too hard' for it.
    Instead, make it impossible and only enable the thorough
    solver.
    '''

    EXPECTED_ERROR_RAND = RandomizationError

    def get_randobj(self, *args):
        randobj = super().get_randobj(*args)
        # Only use thorough solver.
        randobj.set_solver_mode(naive=False, sparse=False)
        # Make problem impossible so that numbers can't sum to 41.
        def mod_2(z):
            return z % 2 == 0
        randobj.add_constraint(mod_2, ('x',))
        randobj.add_constraint(mod_2, ('y',))
        randobj.add_constraint(mod_2, ('z',))
        # Setting max domain size to 1 makes this run a bit quicker.
        randobj._max_domain_size = 1
        return randobj


class ImpossibleOneVar(testutils.RandObjTestBase):
    '''
    Test an impossible constraint problem with one variable.
    '''

    EXPECTED_ERROR_RAND = RandomizationError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        def eq_zero(x):
            return x == 0
        randobj.add_rand_var('a', domain=[1,], constraints=[eq_zero,])
        return randobj


class ImpossibleComplexVar(testutils.RandObjTestBase):
    '''
    Test an impossible constraint problem with one variable, where
    the variable state space is too large to fail on creation.
    '''

    EXPECTED_ERROR_RAND = RandomizationError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        def eq_minus_one(x):
            return x == -1
        randobj.add_rand_var('a', bits=64, constraints=[eq_minus_one,])
        return randobj


class ImpossibleMultiVar(testutils.RandObjTestBase):
    '''
    Test an impossible constraint problem with multiple variables.
    '''

    EXPECTED_ERROR_RAND = RandomizationError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        def lt_5(x):
            return x < 5
        randobj.add_rand_var('a', domain=range(10), constraints=[lt_5,])
        randobj.add_rand_var('b', domain=range(10), constraints=[lt_5,])
        def sum_gt_10(x, y):
            return x + y > 10
        randobj.add_constraint(sum_gt_10, ('a', 'b'))
        return randobj


class NegativeLength(testutils.RandObjTestBase):
    '''
    Test a random list with negative length.
    '''

    EXPECTED_ERROR_INIT = ValueError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.add_rand_var('bad_list', bits=1, length=-1)
        return randobj


class NegativeRandLength(testutils.RandObjTestBase):
    '''
    Test a random list with negative random length.
    '''

    EXPECTED_ERROR_RAND = ValueError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.add_rand_var('bad_length', domain=range(-10,-1))
        randobj.add_rand_var('bad_list', bits=1, rand_length='bad_length')
        return randobj


class DerivedNoFn(testutils.RandObjTestBase):
    '''
    Test that a derived variable requires fn.
    '''

    EXPECTED_ERROR_INIT = ValueError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.add_rand_var('a', domain=range(10))
        randobj.add_rand_var('b', rand_var_args=('a',))
        return randobj


class DerivedUnknownArg(testutils.RandObjTestBase):
    '''
    Test that rand_var_args must name existing variables.
    '''

    EXPECTED_ERROR_INIT = ValueError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.add_rand_var('b', fn=lambda z: z, rand_var_args=('nonexistent',))
        return randobj


class DerivedSelfReference(testutils.RandObjTestBase):
    '''
    Test that a derived variable cannot name itself in rand_var_args. It does
    not exist yet when it is added, so this is the same error as any unknown name.
    '''

    EXPECTED_ERROR_INIT = ValueError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.add_rand_var('b', fn=lambda b: b + 1, rand_var_args=('b',))
        return randobj


class DerivedWithLength(testutils.RandObjTestBase):
    '''
    Test that a derived variable is rejected as a fixed-length list.
    '''

    EXPECTED_ERROR_INIT = RuntimeError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.add_rand_var('a', domain=range(10))
        randobj.add_rand_var('b', fn=lambda a: a + 1, rand_var_args=('a',), length=3)
        return randobj


class DerivedWithRandLength(testutils.RandObjTestBase):
    '''
    Test that a derived variable is rejected as a random-length list.
    '''

    EXPECTED_ERROR_INIT = RuntimeError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.add_rand_var('n', domain=range(1, 4))
        randobj.add_rand_var('a', domain=range(10))
        randobj.add_rand_var('b', fn=lambda a: a + 1, rand_var_args=('a',), rand_length='n')
        return randobj


class RandLengthListAsLength(testutils.RandObjTestBase):
    '''
    Test that a random-length list is rejected as the
    length of another random list.
    '''

    EXPECTED_ERROR_INIT = ValueError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.add_rand_var('length', domain=range(1, 5))
        randobj.add_rand_var('list_a', bits=4, rand_length='length')
        randobj.add_rand_var('list_b', bits=4, rand_length='list_a')
        return randobj


class RandLengthErrorMessages(testutils.RandObjTestBase):
    '''
    Test that rand_length errors name the offending rand_length
    variable, not the variable being added, and that the object
    remains usable after the failed calls.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        with self.assertRaisesRegex(ValueError, "'missing'"):
            randobj.add_rand_var('listvar', bits=4, rand_length='missing')
        randobj.add_rand_var('list_a', bits=4, length=4)
        with self.assertRaisesRegex(ValueError, "'list_a'"):
            randobj.add_rand_var('list_b', bits=4, rand_length='list_a')
        randobj.add_rand_var('a', domain=range(10))
        return randobj

    def check(self, results):
        for result in results:
            self.assertIn(result['a'], range(10))


class EmptyListDependent(testutils.RandObjTestBase):
    '''
    Test a random length list which is empty
    but depended on by another variable.
    '''

    EXPECTED_ERROR_RAND = RandomizationError

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.add_rand_var('length', domain=[0])
        randobj.add_rand_var('list', bits=4, rand_length='length')
        randobj.add_rand_var('list_member', bits=4)
        def in_list_c(x, y):
            return x in y
        randobj.add_constraint(in_list_c, ('list_member', 'list'))
        return randobj


class DerivedLengthCSP(testutils.RandObjTestBase):
    '''
    Test that a derived variable used as a list length is rejected when the
    problem reaches the constraint solver, which cannot revise a derived length.
    The naive solver is disabled to force the constraint solver.
    '''

    EXPECTED_ERROR_RAND = RandomizationError
    EXPECTED_ERROR_RAND_MSG = "constraint solver for a derived variable"

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.set_solver_mode(naive=False)
        randobj.add_rand_var('a', domain=range(10))
        randobj.add_rand_var('l', fn=lambda a: a + 1, rand_var_args=('a',))
        randobj.add_rand_var('list', domain=range(2), rand_length='l')
        randobj.add_rand_var('x', domain=range(20))
        randobj.add_constraint(lambda x, l: x > l, ('x', 'l'))
        return randobj


class DerivedConstraintUnsatisfiableCSP(testutils.RandObjTestBase):
    '''
    A constraint on a derived variable that no input can satisfy, with the
    naive solver disabled. The constraint solver recomputes the derived
    variable from its solution and checks the constraint, so ``randomize``
    must raise rather than return a value that violates it.
    '''

    EXPECTED_ERROR_RAND = RandomizationError
    EXPECTED_ERROR_RAND_MSG = "names a derived variable"

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.set_solver_mode(naive=False)
        randobj.add_rand_var('a', domain=range(10))
        randobj.add_rand_var('b', fn=lambda a: a + 1, rand_var_args=('a',))
        randobj.add_constraint(lambda b: b > 100, ('b',))
        return randobj


class AddConstraintUnknownVar(testutils.RandObjTestBase):
    '''
    Test that a failed add_constraint leaves the object usable.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        randobj = RandObj(*args)
        randobj.add_rand_var('a', domain=range(10))
        def eq(a, b):
            return a == b
        self.assertRaises(KeyError, randobj.add_constraint, eq, ('a', 'b'))
        return randobj

    def check(self, results):
        for result in results:
            self.assertIn(result['a'], range(10))

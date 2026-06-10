# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Test temporary constraints and values.
'''

from random import Random

from constrainedrandom import RandObj
from . import basic
from .. import testutils


class TempConstraint(testutils.RandObjTestBase):
    '''
    Test using a simple temporary constraint.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        return r

    def check(self, results):
        seen_gt_4 = False
        for result in results:
            self.assertIn(result['a'], range(10))
            if result['a'] >= 5:
                seen_gt_4 = True
        self.assertTrue(seen_gt_4, "Temporary constraint followed when not given")

    def get_tmp_constraints(self):
        def tmp_constraint(a):
            return a < 5
        return [(tmp_constraint, ('a',))]

    def tmp_check(self, results):
        for result in results:
            self.assertIn(result['a'], range(5))


class TempMultiConstraint(testutils.RandObjTestBase):
    '''
    Test using a temporary multi-variable constraint.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', domain=range(100))
        return r

    def check(self, results):
        seen_tmp_constraint_false = False
        for result in results:
            self.assertIn(result['a'], range(10))
            self.assertIn(result['b'], range(100))
            if result['a'] * result['b'] >= 200 and result['a'] >= 5:
                seen_tmp_constraint_false = True
        self.assertTrue(seen_tmp_constraint_false, "Temporary constraint followed when not given")

    def get_tmp_constraints(self):
        def a_mul_b_lt_200(a, b):
            return a * b < 200
        return [(a_mul_b_lt_200, ('a', 'b'))]

    def tmp_check(self, results):
        for result in results:
            # Do normal checks
            self.assertIn(result['a'], range(10))
            self.assertIn(result['b'], range(100))
            # Also check the temp constraint is followed
            self.assertLess(result['a'] * result['b'], 200)


class MixedTempConstraints(testutils.RandObjTestBase):
    '''
    Test using a temporary multi-variable constraint, with a single-variable constraint.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', domain=range(100))
        return r

    def check(self, results):
        seen_tmp_constraint_false = False
        for result in results:
            self.assertIn(result['a'], range(10))
            self.assertIn(result['b'], range(100))
            if result['a'] * result['b'] >= 200 and result['a'] >= 5:
                seen_tmp_constraint_false = True
        self.assertTrue(seen_tmp_constraint_false, "Temporary constraint followed when not given")

    def tmp_check(self, results):
        for result in results:
            # Do normal checks
            self.assertIn(result['a'], range(5))
            self.assertIn(result['b'], range(100))
            # Also check the temp constraint is followed
            self.assertLess(result['a'] * result['b'], 200)

    def get_tmp_constraints(self):
        def a_lt_5(a):
            return a < 5
        def a_mul_b_lt_200(a, b):
            return a * b < 200
        return [(a_lt_5, ('a',)), (a_mul_b_lt_200, ('a', 'b'))]


class TrickyTempConstraints(basic.MultiSum):
    '''
    Force use of MultiVarProblem with a difficult problem, and
    also use temporary constraints.
    '''

    ITERATIONS = 30

    def check(self, results):
        # Normal checks
        super().check(results)
        # Check that we see x and y sum to greater than 50 when
        # the temporary constraint isn't in place.
        # Temp constraint not respected - check for at least one instance
        # where all conditions are not respected.
        temp_constraint_respected = True
        for result in results:
            if result['x'] + result['y'] >= 50 and \
                result['x'] % 2 != 0 and \
                (result['y'] + result['z']) % 3 != 0:
                temp_constraint_respected = False
        self.assertFalse(
            temp_constraint_respected,
            "Temp constraint should not be followed when not applied"
        )

    def get_tmp_constraints(self):
        # Use a few extra temporary constraints to make the problem even harder
        tmp_constraints = []

        def tmp_abs_sum_xy_lt50(x, y):
            return abs(x) + abs(y) < 50
        tmp_constraints.append((tmp_abs_sum_xy_lt50, ('x', 'y')))

        def tmp_x_mod2(x):
            return x % 2 == 0
        tmp_constraints.append((tmp_x_mod2, ('x',)))

        def tmp_yz_mod3(y, z):
            return (y + z) % 3 == 0
        tmp_constraints.append((tmp_yz_mod3, ('y', 'z')))

        return tmp_constraints

    # Check that the temp constraint is respected
    def tmp_check(self, results):
        # Normal checks
        super().check(results)
        # Temp constraint respected
        for result in results:
            self.assertLess(result['x'] + result['y'], 50, "Temp constraint not respected")
            self.assertTrue(result['x'] % 2 == 0, "Temp constraint not respected")
            self.assertTrue((result['y'] + result['z']) % 3 == 0, "Temp constraint not respected")


class WithValues(testutils.RandObjTestBase):
    '''
    Basic test for with_values.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', domain=range(100))
        return r

    def check(self, results):
        # Ensure we see the temporary value violated at least once
        non_52_seen = False
        for result in results:
            self.assertIn(result['a'], range(10))
            self.assertIn(result['b'], range(100))
            if result['b'] != 52:
                non_52_seen = True
        self.assertTrue(non_52_seen, "Temporary value used when it shouldn't be")

    def get_tmp_values(self):
        return {'b': 52}

    def tmp_check(self, results):
        for result in results:
            self.assertIn(result['a'], range(10))
            self.assertEqual(result['b'], 52)


class WithValuesWithConstraints(testutils.RandObjTestBase):
    '''
    Test how with_values and with_constraints interact.
    '''

    ITERATIONS = 1000

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', domain=range(100))
        return r

    def check(self, results):
        seen_tmp_constraint_false = False
        seen_tmp_value_false = False
        for result in results:
            self.assertIn(result['a'], range(10))
            self.assertIn(result['b'], range(100))
            if result['a'] * result['b'] >= 200 and result['a'] >= 5:
                seen_tmp_constraint_false = True
            if result['a'] != 3:
                seen_tmp_value_false = True
        self.assertTrue(seen_tmp_constraint_false, "Temporary constraint followed when not given")
        self.assertTrue(seen_tmp_value_false, "Temporary value followed when not given")

    def get_tmp_constraints(self):
        def a_lt_5(a):
            return a < 5
        def a_mul_b_lt_200(a, b):
            return a * b < 200
        return [(a_lt_5, ('a',)), (a_mul_b_lt_200, ('a', 'b'))]

    def get_tmp_values(self):
        return {'a': 3}

    def tmp_check(self, results):
        for result in results:
            # Do normal checks
            self.assertIn(result['a'], range(5))
            self.assertIn(result['b'], range(100))
            # Also check the temp constraint is followed
            self.assertLess(result['a'] * result['b'], 200)
            # Check the temp value has been followed
            self.assertEqual(result['a'], 3)


class WithValuesAllConstrainedVars(testutils.RandObjTestBase):
    '''
    Test with_values when values are given for all constrained variables.
    '''

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('a', domain=range(10))
        r.add_rand_var('b', domain=range(10))
        # Unconstrained, so that results still differ between seeds
        # when both constrained variables are given values.
        r.add_rand_var('c', domain=range(100))
        def sum_gt_5(a, b):
            return a + b > 5
        r.add_constraint(sum_gt_5, ('a', 'b'))
        # Skip the naive solver so the values reach MultiVarProblem.
        r.set_solver_mode(naive=False)
        return r

    def check(self, results):
        for result in results:
            self.assertIn(result['a'], range(10))
            self.assertIn(result['b'], range(10))
            self.assertGreater(result['a'] + result['b'], 5)

    def get_tmp_values(self):
        return {'a': 5, 'b': 5}

    def tmp_check(self, results):
        for result in results:
            self.assertEqual(result['a'], 5)
            self.assertEqual(result['b'], 5)


class WithValuesRandLengthList(testutils.RandObjTestBase):
    '''
    Test that a list given in with_values keeps its value
    while its length variable is re-randomized.
    '''

    ITERATIONS = 100

    def get_randobj(self, *args):
        r = RandObj(*args)
        r.add_rand_var('length', domain=range(1, 4))
        r.add_rand_var('listvar', bits=4, rand_length='length')
        # Unconstrained, so that results still differ between seeds
        # when the list is given a value.
        r.add_rand_var('c', domain=range(100))
        def length_matches(length, listvar):
            return length == len(listvar)
        r.add_constraint(length_matches, ('length', 'listvar'))
        return r

    def check(self, results):
        for result in results:
            self.assertEqual(result['length'], len(result['listvar']), "Length incorrect")

    def get_tmp_values(self):
        return {'listvar': [3, 6]}

    def tmp_check(self, results):
        for result in results:
            self.assertEqual(result['listvar'], [3, 6], "Temp value not respected")
            self.assertEqual(result['length'], 2, "Length incorrect")


class TrickyTempValues(basic.MultiSum):
    '''
    Force use of MultiVarProblem with a difficult problem, and
    also use temporary constraints and temporary values.
    '''

    ITERATIONS = 50

    # Check that we see x and y sum to greater than 50 when
    # the temporary constraint isn't in place
    def check(self, results):
        # Normal checks
        super().check(results)
        # Temp constraint not respected - check for at least one instance
        # where all conditions are not respected
        temp_constraint_respected = True
        temp_value_respected = True
        for result in results:
            if result['x'] + result['y'] >= 50 and \
                (result['x'] % 2 == 1 or \
                    (result['y'] + result['z']) % 2 == 0):
                temp_constraint_respected = False
            if result['x'] != 6:
                temp_value_respected = False
        self.assertFalse(
            temp_constraint_respected,
            "Temp constraint should not be followed when not applied"
        )
        self.assertFalse(
            temp_value_respected,
            "Temp value should not be followed when not applied"
        )

    def get_tmp_constraints(self):
        # Use a few extra temporary constraints to make the problem even harder
        tmp_constraints = []

        def tmp_abs_sum_xy_lt50(x, y):
            return abs(x) + abs(y) < 50
        tmp_constraints.append((tmp_abs_sum_xy_lt50, ('x', 'y')))

        def tmp_x_mod2(x):
            return x % 2 == 0
        tmp_constraints.append((tmp_x_mod2, ('x',)))

        def tmp_yz_mod3(y, z):
            return (y + z) % 2 == 1
        tmp_constraints.append((tmp_yz_mod3, ('y', 'z')))

        return tmp_constraints

    def get_tmp_values(self):
        return {'x': 6}

    # Check that the temp constraint is respected
    def tmp_check(self, results):
        # Normal checks
        super().check(results)
        # Temp constraint respected
        for result in results:
            self.assertLess(result['x'] + result['y'], 50, "Temp constraint not respected")
            self.assertTrue(result['x'] % 2 == 0, "Temp constraint not respected")
            self.assertTrue((result['y'] + result['z']) % 2 == 1, "Temp constraint not respected")
            self.assertEqual(result['x'], 6, "Temp value not respected")

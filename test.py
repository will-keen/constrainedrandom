''' Basic tests on functionality and performance. '''

import timeit
import unittest

from constrainedrandom import Random, RandObj

class RandObjTests(unittest.TestCase):
    '''
    Container for unit tests for constrainedrandom.RandObj
    '''

    def _test(self, problem, iterations, check):
        '''
        Reusable test function to run a problem for a number of iterations and perform checks.
        '''
        results = []
        start_time = timeit.default_timer()
        for _ in range(iterations):
            problem.randomize()
            results.append(dict(problem.__dict__))
        end_time = timeit.default_timer()
        time_taken = end_time - start_time
        hz = iterations/time_taken
        print(f'{self._testMethodName} took {time_taken:.4g}s for {iterations} iterations ({hz:.1f}Hz)')
        check(results)

    def setUp(self):
        # Use a random generator for every test with a fixed seed.
        self.random = Random(0)

    def test_basic(self):
        '''
        Test all basic single random variable features
        '''
        r = RandObj(self.random)
        r.add_rand_var("foo", domain=range(100))
        r.add_rand_var("bar", domain=(1,2,3,))
        r.add_rand_var("baz", bits=4)
        r.add_rand_var("bob", domain={0: 9, 1: 1})
        def not_3(foo):
            return foo != 3
        r.add_rand_var("dan", domain=range(5), constraints=not_3)
        def custom_fn(arg):
            return arg + 1
        r.add_rand_var("joe", fn=custom_fn, args=(1,))
        def check(results):
            for result in results:
                self.assertLessEqual(0, result['foo'])
                self.assertLess(result['foo'], 100)
                self.assertIn(result['bar'], (1,2,3,))
                self.assertLessEqual(0, result['baz'])
                self.assertLess(result['baz'], (1 << 4))
                self.assertIn(result['bob'], (0,1))
                self.assertIn(result['dan'], (0,1,2,4))
                self.assertEqual(result['joe'], 2)
        self._test(r, 1000, check)

    def test_multi_basic(self):
        '''
        Test a basic multi-variable constraint (easy to randomly fulfill the constraint)
        '''
        r = RandObj(self.random)
        r.add_rand_var("a", range(10))
        r.add_rand_var("b", range(10))
        r.add_rand_var("c", range(5,10))
        def abc(a, b, c):
            return a < b < c
        r.add_multi_var_constraint(abc, ("a","b","c"))
        def check(results):
            for result in results:
                self.assertLess(result['a'], result['b'], f'Check failed for {result=}')
                self.assertLess(result['b'], result['c'], f'Check failed for {result=}')
        self._test(r, 100, check)

    def test_multi_plusone(self):
        '''
        Test a slightly trickier multi-variable constraint (much less likely to just randomly get it right)
        '''
        r = RandObj(self.random)
        r.add_rand_var("x", range(100), order=0)
        r.add_rand_var("y", range(100), order=1)
        def plus_one(x, y):
            return y == x + 1
        r.add_multi_var_constraint(plus_one, ("x", "y"))
        def check(results):
            for result in results:
                self.assertEqual(result['y'], result['x'] + 1, f'Check failed for {result=}')
        self._test(r, 100, check)

    def test_multi_sum(self):
        '''
        Test a much trickier multi-variable constraint
        '''
        r = RandObj(self.random)
        def nonzero(x):
            return x != 0
        r.add_rand_var("x", range(-100, 100), order=0, constraints=(nonzero,))
        r.add_rand_var("y", range(-100, 100), order=1, constraints=(nonzero,))
        r.add_rand_var("z", range(-100, 100), order=1, constraints=(nonzero,))
        def sum_41(x, y, z):
            return x + y + z == 41
        r.add_multi_var_constraint(sum_41, ("x", "y", "z"))
        def check(results):
            for result in results:
                self.assertEqual(result['x'] + result['y'] + result['z'], 41, f'Check failed for {result=}')
                self.assertNotEqual(result['x'], 0, f'Check failed for {result=}')
        self._test(r, 10, check)

    def test_multi_order(self):
        '''
        Test a problem that benefits greatly from being solved in a certain order.
        '''
        r = RandObj(self.random)
        r.add_rand_var("a", range(100), order=0)
        r.add_rand_var("b", range(100), order=1)
        def mul_lt1000(a, b):
            return a * b < 1000
        r.add_multi_var_constraint(mul_lt1000, ('a', 'b'))
        r.add_rand_var("c", range(100), order=2)
        def sum_lt100(a, b, c):
            return a + b + c < 100
        r.add_multi_var_constraint(sum_lt100, ('a', 'b', 'c'))
        def check(results):
            for result in results:
                self.assertLess(result['a'] * result['b'], 1000, f'Check failed for {result=}')
                self.assertLess(result['a'] + result['b'] + result['c'], 100, f'Check failed for {result=}')
        self._test(r, 100, check)

    def test_dist(self):
        '''
        Test a distribution
        '''
        r = RandObj(self.random)
        r.add_rand_var("dist", {0: 25, 1 : 25, range(2,5): 50})
        def check(results):
            count_zeroes = 0
            count_ones = 0
            count_two_plus = 0
            for result in results:
                val = result['dist']
                if val == 0:
                    count_zeroes += 1
                elif val == 1:
                    count_ones += 1
                elif 2 <= val < 5:
                    count_two_plus += 1
                else:
                    self.fail("too high!")
            # Check it's roughly the right distribution
            self.assertTrue(225 <= count_zeroes <= 275)
            self.assertTrue(225 <= count_ones <= 275)
            self.assertTrue(475 <= count_two_plus <= 525)
        self._test(r, 1000, check)


if __name__ == "__main__":
    unittest.main()

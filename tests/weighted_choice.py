# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Will Keen

'''
Test weighted_choice function from random.
'''

import unittest
from random import Random

from constrainedrandom import weighted_choice


class WeightedChoiceTests(unittest.TestCase):
    '''
    Test the ``weighted_choice`` function from ``random``.
    '''

    def test_return_value(self):
        # Must return a value, not a list.
        value = weighted_choice({0: 50, 1: 50}, Random(0))
        self.assertIn(value, (0, 1))

# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

"""
Test bitwise operations.
"""

import unittest

from constrainedrandom.bits import get_bitslice, set_bitslice


class BitsliceTests(unittest.TestCase):
    def test_get_bitslice(self):
        print('Testing get_bitslice...')
        self.assertEqual(get_bitslice(0xDEADBEEF, 11, 8), 0xE)
        self.assertEqual(get_bitslice(0xDEADBEEF, 3, 0), 0xF)
        self.assertEqual(get_bitslice(0xDEADBEEF, 4, 0), 0xF)
        self.assertEqual(get_bitslice(0xDEADBEEF, 6, 1), 0x37)
        self.assertEqual(get_bitslice(0xDEADBEEF, 19, 12), 0xDB)
        self.assertEqual(get_bitslice(0xDEADBEEF, 31, 0), 0xDEADBEEF)
        self.assertEqual(get_bitslice(0xDEADBEEF, 32, 0), 0xDEADBEEF)
        self.assertEqual(get_bitslice(0xDEADBEEF, 0, 0), 0x1)
        self.assertEqual(get_bitslice(0xDEADBEEF, 4, 4), 0x0)
        self.assertEqual(get_bitslice(0xDEADBEEF, 34, 32), 0x0)
        print('... done testing get_bitslice.')

    def test_set_bitslice(self):
        print('Testing set_bitslice...')
        self.assertEqual(set_bitslice(0xF00, 1, 0, 2), 0xF02)
        self.assertEqual(set_bitslice(0xF00, 3, 2, 2), 0xF08)
        self.assertEqual(set_bitslice(0xF00, 2, 1, 2), 0xF04)
        self.assertEqual(set_bitslice(0xF00, 11, 8, 0), 0x0)
        self.assertEqual(set_bitslice(0xF00, 11, 8, 3), 0x300)
        self.assertEqual(set_bitslice(0xF00, 12, 11, 3), 0x1F00)
        self.assertEqual(set_bitslice(0, 12, 11, 3), 0x1800)
        self.assertEqual(set_bitslice(0, 15, 0, 0xDEADBEEF), 0xBEEF)
        self.assertEqual(set_bitslice(0, 31, 16, 0xDEADBEEF), 0xBEEF0000)
        self.assertEqual(set_bitslice(0xCAFEF00D, 15, 0, 0xDEADBEEF), 0xCAFEBEEF)
        self.assertEqual(set_bitslice(0xCAFEF00D, 31, 16, 0xDEADBEEF), 0xBEEFF00D)
        print('... done testing set_bitslice.')

    def test_errors(self):
        print('Testing bitslice errors...')
        # lo > hi
        self.assertRaises(ValueError, get_bitslice, 0xDEADBEEF, 3, 5)
        self.assertRaises(ValueError, set_bitslice, 0xDEADBEEF, 3, 5, 3)
        print('... done testing bitslice errors.')

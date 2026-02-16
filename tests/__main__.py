# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

"""
Test all supported features.

Test for determinism within one thread, record performance.
"""

import tests
from tests import (
    bits,
    check_constraints,
    determinism,
    is_pure,
    satisfies_constraints,
    value_in_domain,
    weighted_choice,
)
from tests.features import basic, classes, derived, errors, order, rand_list, set_random, temp, user
from tests.main import main

TEST_MODULES = [
    bits,
    check_constraints,
    determinism,
    is_pure,
    satisfies_constraints,
    value_in_domain,
    weighted_choice,
    basic,
    classes,
    derived,
    errors,
    order,
    rand_list,
    set_random,
    temp,
    user,
]

if __name__ == '__main__':
    main(tests, TEST_MODULES)

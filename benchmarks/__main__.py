# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

'''
Benchmark against pyvsc library for equivalent testcases.
'''

import benchmarks
from benchmarks.pyvsc import basic, in_keyword, ldinstr, randlist
from tests.main import main

BENCHMARK_MODULES = [basic, in_keyword, ldinstr, randlist]

if __name__ == "__main__":
    main(benchmarks, BENCHMARK_MODULES)

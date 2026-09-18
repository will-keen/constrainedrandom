import sys
import unittest
from types import ModuleType
from typing import Iterable

from . import testutils
from .perf_utils import dump_perf_data
from .test_args import get_argparser


def main(package: ModuleType, test_modules: Iterable[ModuleType]) -> None:
    """
    Shared main function for testing and benchmarks.

    Runs every test in ``test_modules`` unless test names are given on the
    command line. Names are resolved relative to ``package``, so
    ``features.basic.MultiSum`` selects one test class from ``tests``.

    :param package: The package the test modules belong to.
    :param test_modules: The modules to load tests from.
    """
    parser = get_argparser()
    args, extra = parser.parse_known_args()
    testutils.RandObjTestBase.TEST_LENGTH_MULTIPLIER = args.length_mul
    # Reconstruct argv
    argv = [sys.argv[0]] + extra
    prefix = package.__name__ + '.'
    default_tests = [module.__name__[len(prefix) :] for module in test_modules]
    result = unittest.main(module=package, defaultTest=default_tests, argv=argv, exit=False).result
    if args.perf:
        dump_perf_data(args.perf_results_file, args.perf_results_tag)
    retcode = 0 if result.wasSuccessful() else 1
    sys.exit(retcode)

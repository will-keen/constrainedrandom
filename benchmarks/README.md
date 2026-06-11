# Benchmarks

These benchmarks are intended as developer-facing. They contain checks to ensure that performance has not degraded.

## Extra requirements

You need to install [`pyvsc`](https://pyvsc.readthedocs.io/en/latest/introduction.html) in order to run the benchmarks. This is not included in `constrainedrandom`'s core dependencies to avoid making installation size bigger than necessary. Install it with the `benchmarks` optional dependency group:

```bash
pip install -e ".[benchmarks]"
```

Note that `pyvsc` depends on `pyboolector`, which does not provide packages for all platforms (e.g. there is no macOS arm64 support). On unsupported platforms, run the benchmarks in a container, e.g.:

```bash
docker run --platform linux/amd64 -v "$PWD":/work -w /work python:3.12 \
    bash -c "pip install -e '.[benchmarks]' && python -m benchmarks"
```

## Running

To run, from the root of constrainedrandom:

```
python3 -m benchmarks
```

## Defining new benchmarks

Benchmark test cases should inherit from `benchmarks.benchmark_utils.BenchmarkTestCase`.

Each test case should implement a `get_randobjs()` method. This returns a dictionary of the random objects to be tested. Each should implement the `randomize()` function and be equivalent.

Each test case should also implement a `check_perf()` method, so that the expected results are defined in an executable, checkable manner.

## Shared framework

The benchmarks use a shared testing framework with the unit tests. However, they are kept separate so that users don't have to install `pyvsc` to ensure basic functionality of constrainedrandom.

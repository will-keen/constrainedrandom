# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

Randomization is repeatable for a given seed within a minor version of
`constrainedrandom`: a patch release does not change the values produced for a
given seed. A release that does change them increments at least the minor
version and says so under **Changed**.

## [Unreleased]

Results with the same problem and same seed may differ from 1.2.2. The entries under **Changed** say for which problems.

### Added
- Derived variables: `add_rand_var(..., fn=..., rand_var_args=(...))` computes a variable's value from other variables.
- `randomize(with_values=...)` validates the given values against domains and constraints. Pass `check_with_values=False` to skip.

### Changed
- `range` domains use their `step`. Seeded results change for stepped ranges.
- `weighted_choice` returns the chosen value rather than a single-element list.
- The naive solver calls the random generator once less per attempt. Seeded results change for problems with multi-variable constraints.
- Variables are randomized in the order they were added. Seeded results change for objects whose variables were added in non-alphabetical order.
- `python -m tests` selects tests by package-relative name, e.g. `features.basic.BasicFeatures`.

### Fixed
- Constraining a random-length list no longer holds its length constant.
- `randomize(with_values=...)` no longer raises `IndexError` when every constrained variable is given a value.
- A list given in `with_values` is no longer overwritten when its length variable is re-randomized.
- `functools.partial` objects and other callables are no longer rejected as constraints.
- A failed `add_constraint` no longer leaves the object unusable.
- Using a random-length list as another variable's `rand_length` now raises an error.
- Failure messages no longer omit debug information.
- The CSP solve order is rebuilt when a random-length list's length changes, so results no longer depend on earlier randomizations. Seeded results change for problems with random-length lists that reach the CSP solver.

### Performance
- Constraints on concrete values are checked directly rather than via the `constraint` package. 3.5x faster on `ldInstr`, up to 7.6x on multi-variable naive solving.
- `is_pure` treats a `functools.partial` of a pure function with immutable arguments as pure.

### Development
- CI runs the tests on Linux, Windows and macOS and builds the docs with warnings as errors.
- `ruff` formats and lints the code, enforced in CI.

## [1.2.2] - 2024-10-14

### Changed
- Added Will Keen to the copyright notice. No functional changes.

## [1.2.1] - 2024-06-07

### Added
- Unified benchmark and test framework, documented in `tests/README.md` and `benchmarks/README.md`.

### Changed
- Improved the debug output when randomization fails.

## [1.2.0] - 2024-04-22

### Added
- Pure and non-pure constraints, via the `is_pure` helper. Pure constraints allow more optimization.
- Support for using class methods as constraints, including overriding them through inheritance.
- User control of solver sparsities through `set_solver_mode`.

### Fixed
- Incorrect interaction between constraint overrides and class-member overrides.
- A random-length-list ordering issue (the `RandSizeListOrder` case).

## [1.1.2] - 2023-11-15

### Fixed
- An overflow bug in randomization.
- Documentation build failures. Added `requirements.txt` for building the docs.

## [1.1.1] - 2023-11-06

### Changed
- Argument validation now raises exceptions instead of using `assert`, so the checks are not skipped when Python runs with `-O`.

### Fixed
- An issue where a non-pure constraint could be evaluated before the value it depends on was assigned.

## [1.1.0] - 2023-09-06

### Added
- `length` and `rand_length` arguments to `add_rand_var`, for random lists of fixed or randomized length. The two are mutually exclusive.

### Changed
- Optimized the `bits` argument to `add_rand_var`.

### Fixed
- Sanitization of invalid list lengths.

## [1.0.3] - 2023-08-18

### Fixed
- Non-determinism when using global seeding.

### Added
- Documentation and testing for globally-seeded and deep-copied `RandObj` instances.

## [1.0.2] - 2023-08-16

### Added
- Support for `copy.deepcopy` on `RandObj` instances.

## [1.0.1] - 2023-08-10

### Fixed
- Bugs in list randomization.

### Added
- A note on releases and versioning in the README.

## [1.0.0] - 2023-07-28

First stable release.

### Added
- Random lists of values, via the `length` argument to `add_rand_var`.
- Temporary constraints and temporary values (`with_values`) for a single call to `randomize()`.
- Weighted distributions, via `dist` and `weighted_choice`.
- `Enum` and `IntEnum` domains.
- Global seeding through the `random` package, as an alternative to passing a `random.Random` instance.
- An `initial` argument to `add_rand_var`.
- A `bits` module of common bitwise operations (`get_bitslice`, `set_bitslice`).
- `RandomizationError`, raised when a problem cannot be solved, with debug information.

### Changed
- Renamed `add_multi_var_constraint` to `add_constraint`.

### Removed
- The `Random` re-export from the package's public API. Use `dist` and `weighted_choice`, or the standard library `random`, instead.

## [0.0.1] - 2023-05-26

### Added
- Initial public release on PyPI. Declarative constrained randomization with `RandObj`: single-variable and multi-variable constraints, ordering hints, and the naive, sparse and thorough solvers.

[Unreleased]: https://github.com/will-keen/constrainedrandom/compare/1.2.2...HEAD
[1.2.2]: https://github.com/will-keen/constrainedrandom/compare/1.2.1...1.2.2
[1.2.1]: https://github.com/will-keen/constrainedrandom/compare/1.2.0...1.2.1
[1.2.0]: https://github.com/will-keen/constrainedrandom/compare/1.1.2...1.2.0
[1.1.2]: https://github.com/will-keen/constrainedrandom/compare/1.1.1...1.1.2
[1.1.1]: https://github.com/will-keen/constrainedrandom/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/will-keen/constrainedrandom/compare/1.0.3...1.1.0
[1.0.3]: https://github.com/will-keen/constrainedrandom/compare/1.0.2...1.0.3
[1.0.2]: https://github.com/will-keen/constrainedrandom/compare/1.0.1...1.0.2
[1.0.1]: https://github.com/will-keen/constrainedrandom/compare/1.0.0...1.0.1
[1.0.0]: https://github.com/will-keen/constrainedrandom/compare/0.0.1...1.0.0
[0.0.1]: https://github.com/will-keen/constrainedrandom/releases/tag/0.0.1

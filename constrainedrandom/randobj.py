# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from . import utils
from .internal.multivar import MultiVarProblem
from .internal.randvar import RandVar


@dataclass
class _RandomizeState:
    """Working state for a single ``randomize()`` call, populated as it runs."""

    # Collect debug info during randomization
    debug: bool = False
    # True when temporary constraints alter the base problem
    has_tmp_constraints: bool = False
    # Concrete values to assign, by variable name
    with_values: Dict[str, Any] = field(default_factory=dict)
    # Temporary single-variable constraints, by variable name
    tmp_single_var_constraints: Dict[str, List[utils.Constraint]] = field(default_factory=dict)
    # Problem-level constraints for this call (base plus temporary)
    constraints: List[utils.ConstraintAndVars] = field(default_factory=list)
    # Variables to re-randomize while solving: constrained variables and everything marked with them
    constrained_var_names: Set[str] = field(default_factory=set)
    # Randomized values so far, by variable name
    result: Dict[str, Any] = field(default_factory=dict)


class RandObj:
    """
    Randomizable object. User-facing class.
    Contains any number of random variables and constraints.
    Randomizes to produce a valid solution for those variables and constraints.

    :param _random: An instance of ``random.Random``, which controls the
        seeding and random generation for this class. If passed none, use the global
        Python random package.
    :param max_iterations: The maximum number of failed attempts to solve the randomization
        problem before giving up.
    :param max_domain_size: The maximum size of domain that a constraint satisfaction problem
        may take. This is used to avoid poor performance. When a problem exceeds this domain
        size, we don't use the ``constraint`` package, but just use ``random`` instead.

    :example:

    .. code-block:: python

        import random
        from constrainedrandom import RandObj

        # Create a random object based on a random generator with seed 0
        rand_generator = random.Random(0)
        rand_obj = RandObj(rand_generator)

        # Add some random variables
        rand_obj.add_rand_var('one_to_nine', domain=range(1, 10))
        rand_obj.add_rand_var('eight_bits', bits=8, constraints=(lambda x : x != 0))

        # Add a multi-variable constraint
        rand_obj.add_constraint(lambda x, y : x != y, ('one_to_nine', 'eight_bits'))

        # Produce one valid solution
        rand_obj.randomize()

        # Random variables are now accessible as member variables
        print(rand_obj.one_to_nine)
        print(rand_obj.eight_bits)
    """

    def __init__(
        self,
        _random: Optional[random.Random] = None,
        max_iterations: int = utils.MAX_ITERATIONS,
        max_domain_size: int = utils.CONSTRAINT_MAX_DOMAIN_SIZE,
    ) -> None:
        # Prefix 'internal use' variables with '_', as randomized results are populated to the class
        self._random: Optional[random.Random] = _random
        # Insertion order is dependency order: a variable's rand_length and
        # rand_var_args must already exist when it is added, so iterating this
        # dict visits every variable after the ones it depends on.
        self._random_vars: Dict[str, RandVar] = {}
        # This maps the names of variables used as random lengths (keys) to a list of the variable
        # names that they set the length for (values).
        self._rand_list_lengths: Dict[str, List[str]] = defaultdict(list)
        # Names of variables whose value is derived from other variables.
        self._derived_vars: Set[str] = set()
        # This maps each variable name (keys) to the derived variables that
        # name it in rand_var_args (values).
        self._derived_dependents: Dict[str, List[str]] = defaultdict(list)
        self._constraints: List[utils.ConstraintAndVars] = []
        self._constrained_vars: Set[str] = set()
        self._max_iterations: int = max_iterations
        self._max_domain_size: int = max_domain_size
        self._naive_solve: bool = True
        self._sparse_solve: bool = True
        self._sparsities: List[int] = [1, 10, 100, 1000]
        self._thorough_solve: bool = True
        # A constraint or variable was added, so the CSP problem must be rebuilt.
        self._problem_changed: bool = False
        self._multi_var_problem: Optional[MultiVarProblem] = None

    def _get_random(self) -> random.Random:
        """
        Internal function to get the appropriate randomization object.

        We can't store the package ``random`` in a member variable as this
        prevents pickling.

        :return: The appropriate random generator.
        """
        if self._random is None:
            return random
        return self._random

    def _get_list_length_constraints(self, var_names: Set[str]) -> List[utils.ConstraintAndVars]:
        """
        Internal function to get constraints to describe
        the relationship between random list lengths and the variables
        that define them.

        :param var_names: List of variable names that we want to
            constrain. Only consider variables from within
            this list in the result. Both the list length
            variable and the list variable it constrains must
            be in ``var_names`` to return a constraint.
        :return: List of constraints with variables, describing
            relationship between random list variables and lengths.
        """
        result: List[utils.ConstraintAndVars] = []
        for rand_list_length, list_vars in self._rand_list_lengths.items():
            if rand_list_length in var_names:
                for list_var in list_vars:
                    if list_var in var_names:

                        def len_constr(_list_var, _length):
                            return len(_list_var) == _length

                        result.append((len_constr, (list_var, rand_list_length)))
        return result

    def _derive_lengths_from_concrete_lists(self, with_values: Dict[str, Any]) -> None:
        """
        Set each length variable to the length of any list given a concrete value
        in ``with_values``. Raises ``ValueError`` on conflicting values.

        :param with_values: The concrete values passed to the ``randomize()`` call.
        :raise ValueError: If lists with the same governing random length
            variable have different lengths.
        """
        if len(with_values) == 0:
            return
        for length_name, list_names in self._rand_list_lengths.items():
            # Create a map of list names to concrete values for lists
            # governed by one random length variable
            concrete_lengths = {
                list_name: len(with_values[list_name])
                for list_name in list_names
                if list_name in with_values
            }
            if len(concrete_lengths) == 0:
                continue
            # Check the lengths are all the same
            final_length: int | None = None
            for length in concrete_lengths.values():
                if final_length is None:
                    final_length = length
                elif length != final_length:
                    raise ValueError(
                        f'with_values gives lists sharing length'
                        f" '{length_name}' with different lengths: {concrete_lengths}"
                    )
            # Check that the length itself isn't inconsistently overridden in with_values
            if length_name in with_values and with_values[length_name] != final_length:
                raise ValueError(
                    f"with_values gives '{length_name}'="
                    f'{with_values[length_name]} but lists whose lengths '
                    f'are governed by that variable of differing lengths: {concrete_lengths}'
                )
            # Modify in-place
            with_values[length_name] = final_length

    def _check_with_values(self, with_values: Dict[str, Any]) -> None:
        """
        Check that each concrete value in ``with_values`` is a valid
        assignment to its variable.

        :param with_values: The concrete values passed to the ``randomize()`` call.
        :raises KeyError: If a name in ``with_values`` is not a random variable.
        :raises ValueError: If a value is not in its variable's domain.
        :raises RandomizationError: If a value does not satisfy its variable's
            constraints.
        """
        for name, value in with_values.items():
            if name not in self._random_vars:
                raise KeyError(
                    f"with_values gives a value for '{name}', which is not a random variable."
                )
            rand_var = self._random_vars[name]
            if not rand_var.value_in_domain(value):
                raise ValueError(
                    f"with_values gives '{name}' the value {value},"
                    f" which is not in that variable's domain - check its definition."
                )
            if not rand_var.satisfies_constraints(value):
                raise utils.RandomizationError(
                    f"with_values gives '{name}' the value"
                    f' {value}, which does not satisfy its constraints.'
                )

    def _mark_constrained(self, name: str, constrained: Optional[Set[str]] = None) -> None:
        """
        Mark a variable as constrained, and mark everything that must be
        re-randomized along with it.

        Marking a variable also marks:

        - any lists whose length it controls,
        - its length variable, if it is a random-length list,
        - its ``rand_var_args``, if it is derived,
        - any derived variable that names it in ``rand_var_args``, but not
          that variable's other inputs, which have no reason to change.

        This repeats for each newly marked variable. It terminates because a
        variable that is already marked is skipped, so each is visited at most once.

        :param name: Variable to mark as constrained.
        :param constrained: Set of constrained variable names to update.
            Defaults to this object's own set of constrained variables.
        """
        if constrained is None:
            constrained = self._constrained_vars
        if name in constrained:
            return
        constrained.add(name)
        # If this variable controls others' lengths, they are constrained too.
        if name in self._rand_list_lengths:
            for list_var in self._rand_list_lengths[name]:
                self._mark_constrained(list_var, constrained)
        # If this variable has a random length, its length variable is constrained.
        rand_length = self._random_vars[name].rand_length
        if rand_length is not None:
            self._mark_constrained(rand_length, constrained)
        # If this variable is derived, its rand_var_args are constrained.
        if name in self._derived_vars:
            for dep in self._random_vars[name].rand_var_args:
                self._mark_constrained(dep, constrained)
        # Derived variables that name this one may change value, so they are
        # constrained too.
        for dependent in self._derived_dependents.get(name, ()):
            self._mark_derived_constrained(dependent, constrained)

    def _mark_derived_constrained(self, name: str, constrained: Optional[Set[str]] = None) -> None:
        """
        Mark a derived variable as constrained, so it is recomputed while solving.
        Also mark the lists whose length it sets and the derived variables that name it.
        Do not mark its inputs. Re-randomizing an unconstrained input cannot satisfy a constraint.

        :param name: Derived variable to mark as constrained.
        :param constrained: Set of constrained variable names to update.
            Defaults to this object's own set of constrained variables.
        """
        if constrained is None:
            constrained = self._constrained_vars
        if name in constrained:
            return
        constrained.add(name)
        for list_var in self._rand_list_lengths.get(name, ()):
            self._mark_constrained(list_var, constrained)
        for dependent in self._derived_dependents.get(name, ()):
            self._mark_derived_constrained(dependent, constrained)

    def _add_single_var_constraint(self, constr: utils.Constraint, var: str) -> None:
        """
        Add a single-variable constraint to ``var``.

        For a derived variable, the constraint is registered at the problem
        level and its ``rand_var_args`` are marked constrained, so
        re-randomizing them searches for a value that satisfies it.

        :param constr: Constraint to add.
        :param var: Name of the variable the constraint applies to.
        """
        if var in self._derived_vars:
            self._constraints.append((constr, (var,)))
            self._mark_constrained(var)
        else:
            self._random_vars[var].add_constraint(constr)

    def set_random(self, _random: Optional[random.Random] = None) -> None:
        """
        Set the random instance for this RandObj and propagate to all existing random variables.

        This is useful when the random instance is not available at construction time
        but needs to be set before randomization. Unlike passing ``_random`` to ``__init__``,
        this method propagates to :class:`RandVar` objects that were already created.

        :param _random: A ``random.Random`` instance to use for randomization, or ``None`` to
            use the default random module.
        :return: ``None``
        """
        self._random = _random
        for rand_var in self._random_vars.values():
            rand_var._random = _random

    def set_solver_mode(
        self,
        *,
        naive: Optional[bool] = None,
        sparse: Optional[bool] = None,
        sparsities: Optional[List[int]] = None,
        thorough: Optional[bool] = None,
    ) -> None:
        """
        Disable/enable different solving steps.

        Solvers are used in the following order:
        1. Naive solve - randomizing and checking constraints.
        For some problems, it is more expedient to skip this
        step and go straight to a MultiVarProblem.
        2. Sparse solve - graph-based exploration of state space.
        Start with depth-first search, move to wider subsets
        of each level of state space until valid solution
        found.
        3. Thorough solve - use constraint solver to get
        all solutions and pick a random one.

        If a solver step is enabled it will run, if disabled
        it won't run.

        :param naive: ``True`` if naive solver should be used,
            ``False`` otherwise. Setting not changed if argument
            not provided.
        :param sparse: ``True`` if sparse solver should be used,
            ``False`` otherwise. Setting not changed if argument
            not provided.
        :param sparsities: A list specifying the number of solutions
            to keep when solving each generation of the problem
            sparsely. Setting not changed if argument not provided.
        :param thorough: ``True`` if thorough solver should be used,
            ``False`` otherwise. Setting not changed if argument
            not provided.
        :return: ``None``
        """
        if naive is not None:
            self._naive_solve = naive
        if sparse is not None:
            self._sparse_solve = sparse
        if sparsities is not None:
            self._sparsities = sparsities
        if thorough is not None:
            self._thorough_solve = thorough

    def add_rand_var(
        self,
        name: str,
        *,
        domain: Optional[utils.Domain] = None,
        bits: Optional[int] = None,
        fn: Optional[Callable] = None,
        args: Optional[tuple] = None,
        rand_var_args: Optional[Iterable[str]] = None,
        constraints: Optional[Iterable[utils.Constraint]] = None,
        list_constraints: Optional[Iterable[utils.Constraint]] = None,
        length: Optional[int] = None,
        rand_length: Optional[str] = None,
        order: Optional[int] = None,
        initial: Any = None,
        disable_naive_list_solver: bool = False,
    ) -> None:
        """
        Add a random variable to the object.
        Exactly one of ``domain``, ``bits``, or ``fn`` (optionally with ``args``) must be provided
        to determine how to randomize.

        :param name: The name of this random variable.
        :param domain: The possible values for this random variable, expressed either
            as a ``range``, or as an iterable (e.g. ``list``, ``tuple``) of possible values.
            Mutually exclusive with ``bits`` and ``fn``.
        :param bits: Specifies the possible values of this variable in terms of a width
            in bits. E.g. ``bits=32`` signifies this variable can be ``0 <= x < 1 << 32``.
            Mutually exclusive with ``domain`` and ``fn``.
        :param fn: Specifies a function to call that will provide the value of this random
            variable.
            Mutually exclusive with ``domain`` and ``bits``.
        :param args: Arguments to pass to the function specified in ``fn``.
            If ``fn`` is not used, ``args`` must not be used.
        :param rand_var_args: Names of existing variables whose values are passed to
            ``fn`` to compute this variable's value, making this a *derived* variable.
            The values are passed positionally after any ``args``, i.e.
            ``fn(*args, *rand_var_arg_values)``. Each name must already have been added
            as a random variable. Requires ``fn``. ``fn`` may itself use randomness.
        :param constraints: List or tuple of constraints that apply to this random variable.
            Each of these apply only to the individual values in the list, if a length is
            specified. For a derived variable they are satisfied by re-randomizing its
            ``rand_var_args``.
        :param list_constraints: List or tuple of constraints on the list as a whole. Each is
            called with the entire list, unlike ``constraints``, which are called with one
            element. Ignored unless ``length`` or ``rand_length`` is given.
        :param length: Specify a length >= 0 to turn this variable into a list of random
            values. A value >= 0 means a list of that length. A zero-length list is just
            an empty list. A value of ``None`` (default) means a scalar value.
            Mutually exclusive with ``rand_length``.
        :param rand_length: Specify the name of a random variable that defines the length
            of this variable. The variable must have already been added to this instance.
            Mutually exclusive with ``length``. A derived length requires the naive
            solver. See :func:`set_solver_mode`.
        :param order: The solution order for this variable with respect to other variables.
        :param initial: Initial value to assign to the variable prior to randomizing.
        :param disable_naive_list_solver: Attempt to use a faster algorithm for solving
            list problems. May be faster, but may negatively impact quality of results.
        :return: ``None``
        :raises ValueError: If inputs are not valid.
        :raises RuntimeError: If mutually-exclusive inputs are specified together.

        :example:

        .. code-block:: python

            # Create a random object based on a random generator with seed 0
            rand_generator = random.Random(0)
            rand_obj = RandObj(rand_generator)

            # Add a variable which can be 1, 3, 5, 7 or 11
            rand_obj.add_rand_var('prime', domain=(1, 3, 5, 7, 11))

            # Add a variable which can be any number between 3 and 13, except 7
            rand_obj.add_rand_var('not_7', domain=range(3, 14), constraints=(lambda x: x != 7,))

            # Add a variable which is 12 bits wide and can't be zero
            rand_obj.add_rand_var('twelve_bits', bits=12, constraints=(lambda x: x != 0,))

            # Add a variable whose value is generated by calling a function
            def my_fn():
                return rand_generator.randrange(10)
            rand_obj.add_rand_var('fn_based', fn=my_fn)

            # Add a variable whose value is generated by calling a function that takes arguments
            def my_fn(factor):
                return factor * rand_generator.randrange(10)
            rand_obj.add_rand_var('fn_based_with_args', fn=my_fn, args=(2,))
        """
        # Check this is a valid name
        if name in self.__dict__:
            raise ValueError(
                f"random variable name '{name}' is not valid, already exists in object"
            )
        if name in self._random_vars:
            raise ValueError(
                f"random variable name '{name}' is not valid, already exists in random variables"
            )
        # rand_length and length are mutually-exclusive.
        if (length is not None) and (rand_length is not None):
            raise RuntimeError(
                "'length' and 'rand_length' are mutually-exclusive, but both were specified"
            )
        if length is not None and length < 0:
            raise ValueError('length was negative, must be zero or positive.')
        # A derived variable is a scalar computed from its inputs, so a list
        # of them has no defined meaning.
        if rand_var_args is not None and (length is not None or rand_length is not None):
            raise RuntimeError(
                "'rand_var_args' is mutually-exclusive with 'length' and"
                " 'rand_length', but both were specified."
            )
        if rand_length is not None:
            # Indicates the length of the RandVar depends on another random variable.
            if rand_length not in self._random_vars:
                raise ValueError(
                    f"rand_length '{rand_length}' is not valid,"
                    ' it must be the name of an existing random variable.'
                )
            if self._random_vars[rand_length].is_list():
                raise ValueError(
                    f"rand_length '{rand_length}' must be a scalar random"
                    ' variable, but is itself a random list.'
                )
            # Track that this variable depends on another for its length.
            self._rand_list_lengths[rand_length].append(name)
            # Ensure the order used for this variable is greater than
            # the one we depend on.
            # Ignore the user if they're wrong rather than raising an error.
            if order is None or order <= self._random_vars[rand_length].order:
                order = self._random_vars[rand_length].order + 1
        if rand_var_args is not None:
            # A derived variable's value is computed by fn from the values
            # of the variables it depends on.
            if fn is None:
                raise ValueError(f"derived variable '{name}' requires 'fn' to compute its value.")
            rand_var_args = tuple(rand_var_args)
            for dep in rand_var_args:
                # Dependencies must already exist. This forces variables to be
                # added before those that depend on them, which makes circular
                # dependencies impossible to construct.
                if dep not in self._random_vars:
                    raise ValueError(
                        f"rand_var_args for '{name}' names '{dep}',"
                        ' which is not an existing random variable.'
                    )
        order = 0 if order is None else order
        self._random_vars[name] = RandVar(
            name=name,
            _random=self._random,
            order=order,
            domain=domain,
            bits=bits,
            fn=fn,
            args=args,
            rand_var_args=rand_var_args,
            constraints=(None if rand_var_args is not None else constraints),
            list_constraints=list_constraints,
            length=length,
            rand_length=rand_length,
            max_iterations=self._max_iterations,
            max_domain_size=self._max_domain_size,
            disable_naive_list_solver=disable_naive_list_solver,
        )
        if rand_length is not None and rand_length in self._constrained_vars:
            # The length variable is already constrained, so the list it
            # controls must be re-randomized when solving too.
            self._mark_constrained(name)
        if rand_var_args is not None:
            self._derived_vars.add(name)
            for dep in rand_var_args:
                self._derived_dependents[dep].append(name)
            # An input is already constrained, so this variable's value may
            # change when solving, as for a list whose length is constrained.
            if any(dep in self._constrained_vars for dep in rand_var_args):
                self._mark_derived_constrained(name)
            if constraints is not None:
                for con in constraints:
                    self._add_single_var_constraint(con, name)
        self._problem_changed = True
        self.__dict__[name] = initial

    def add_constraint(self, constr: utils.Constraint, variables: Iterable[str]):
        """
        Add an arbitrary constraint that applies to one or more variable(s).

        :param constr: A function (or callable) that accepts the random variables listed in
            ``variables`` as argument(s) and returns either ``True`` or ``False``.
            If the function returns ``True`` when passed the variables, the constraint is satisfied.
        :param variables: A tuple/list of variables affected by this constraint.
            The order matters, this order will be preserved when passing variables into
            the constraint.
        :return: ``None``
        :raises KeyError: If any member of ``variables`` is not a valid random variable.
        :raises TypeError: If type of ``variables`` is not str, list or tuple.

        :example:

        .. code-block:: python

            # Assume we have a RandObj called 'randobj', with random variables a, b and c
            # Add a constraint that a, b and c must be different values
            def not_equal(x, y, z):
                return (x != y) and (y != z) and (x != z)
            randobj.add_constraint(not_equal, ('a', 'b', 'c'))

            # Add a constraint that a is less than b
            randobj.add_constraint(lambda x, y: x < y, ('a', 'b'))

            # Add a constraint that c must be more than double a but less than double b
            randobj.constr(lambda a, b, c: (a * 2) < c < (b * 2), ('a', 'b', 'c'))
        """
        if isinstance(variables, str):
            # Single-variable constraint
            self._add_single_var_constraint(constr, variables)
        elif isinstance(variables, (list, tuple)):
            if len(variables) == 1:
                # Single-variable constraint
                self._add_single_var_constraint(constr, variables[0])
            else:
                # Multi-variable constraint
                # Validate the variables before changing any state.
                for var in variables:
                    if var not in self._random_vars:
                        raise KeyError(f"Variable '{var}' was not in the set of random variables!")
                self._constraints.append((constr, variables))
                for var in variables:
                    self._mark_constrained(var)
        else:
            raise TypeError(f"'variables' must be of type str, tuple or list, got {variables}")
        self._problem_changed = True

    def pre_randomize(self) -> None:
        """
        Called by :func:`randomize` before randomizing variables. Can be overridden to do something.

        :return: ``None``
        """
        pass

    def randomize(
        self,
        *,
        with_values: Optional[Dict[str, Any]] = None,
        with_constraints: Optional[Iterable[utils.ConstraintAndVars]] = None,
        check_with_values: bool = True,
        debug: bool = False,
    ) -> None:
        """
        Randomizes all random variables, applying all constraints provided.
        After calling this for the first time, random variables are
        accessible as member variables.

        :return: None
        :param with_constraints: Temporary constraints for this randomization only.
            List of tuples, consisting of a constraint function and an iterable
            containing the variables it applies to.
        :param check_with_values: If ``True``, check that each value in
            ``with_values`` is a valid assignment to its variable. Set ``False``
            to skip this check and assign the values regardless.
        :param debug: ``True`` to run in debug mode. Slower, but collects
            all debug info along the way and not just the final failure.
        :raises RandomizationError: If no solution is found
            that satisfies the defined constraints.
        :raises TypeError: If types are incorrect.
        :raises ValueError: If no variables are supplied for a given constraint.
        """
        self.pre_randomize()

        state = _RandomizeState(debug=debug)
        self._apply_temporary_constraints(state, with_constraints)
        self._apply_with_values(state, with_values, check_with_values)

        # Give every variable a value that satisfies its own constraints...
        self._randomize_variables(self._random_vars.keys(), state)
        # ...then revise the constrained ones until the multi-variable constraints hold.
        self._solve(state)

        # Make the results available as member variables.
        self.__dict__.update(state.result)

        self.post_randomize()

    def _apply_temporary_constraints(
        self,
        state: _RandomizeState,
        with_constraints: Optional[Iterable[utils.ConstraintAndVars]],
    ) -> None:
        """
        Populate ``state`` with the constraints for this call: the base
        constraints plus any temporary ones in ``with_constraints``.

        :raises TypeError: If a constraint's variables are not iterable.
        :raises ValueError: If a constraint applies to no variables.
        """
        constraints = list(self._constraints)
        constrained_var_names = set(self._constrained_vars)
        tmp_single_var_constraints: Dict[str, List[utils.Constraint]] = defaultdict(list)
        has_tmp_constraints = False
        if with_constraints is not None:
            for constr, var_names in with_constraints:
                if not isinstance(var_names, Iterable):
                    raise TypeError(
                        'with_constraints should specify a list of tuples of '
                        '(constraint, Iterable[variables])'
                    )
                if not len(var_names) > 0:
                    raise ValueError('Cannot add a constraint that applies to no variables')
                # A derived variable cannot satisfy a constraint on its own, so
                # its constraints are applied at problem level.
                if len(var_names) == 1 and var_names[0] not in self._derived_vars:
                    tmp_single_var_constraints[var_names[0]].append(constr)
                    has_tmp_constraints = True
                else:
                    constraints.append((constr, var_names))
                    for var_name in var_names:
                        self._mark_constrained(var_name, constrained_var_names)
                    has_tmp_constraints = True
            # If a variable becomes constrained by a temporary multi-variable
            # constraint, its temporary single-variable constraints apply too.
            for var_name, constrs in sorted(tmp_single_var_constraints.items()):
                if var_name in constrained_var_names:
                    for constr in constrs:
                        constraints.append((constr, (var_name,)))
        state.constraints = constraints
        state.constrained_var_names = constrained_var_names
        state.tmp_single_var_constraints = tmp_single_var_constraints
        state.has_tmp_constraints = has_tmp_constraints

    def _apply_with_values(
        self,
        state: _RandomizeState,
        with_values: Optional[Dict[str, Any]],
        check_with_values: bool,
    ) -> None:
        """
        Copy ``with_values`` into ``state``, derive any list lengths implied
        by concrete lists, and validate the values unless ``check_with_values``
        is ``False``.
        """
        with_values = dict(with_values) if with_values else {}
        self._derive_lengths_from_concrete_lists(with_values)
        if check_with_values:
            self._check_with_values(with_values)
        state.with_values = with_values

    def _randomize_variables(self, names: Iterable[str], state: _RandomizeState) -> None:
        """
        Give each named variable a value:

        - use its concrete value if one was supplied,
        - compute it from its rand_var_args if it is derived,
        - otherwise randomize it,
        - then set the length of any list it governs.

        Names must be in dependency order.
        """
        result = state.result
        with_values = state.with_values
        tmp_single_var_constraints = state.tmp_single_var_constraints
        debug = state.debug
        random_vars = self._random_vars
        rand_list_lengths = self._rand_list_lengths
        derived_vars = self._derived_vars
        for name in names:
            if name in with_values:
                value = with_values[name]
            elif name in derived_vars:
                rand_var = random_vars[name]
                rand_var.set_rand_var_args({dep: result[dep] for dep in rand_var.rand_var_args})
                value = rand_var.randomize(tmp_single_var_constraints.get(name, []), debug)
            else:
                value = random_vars[name].randomize(tmp_single_var_constraints.get(name, []), debug)
            result[name] = value
            dependents = rand_list_lengths.get(name)
            if dependents:
                for dependent_var_name in dependents:
                    random_vars[dependent_var_name].set_rand_length(value)

    def _solve(self, state: _RandomizeState) -> None:
        """
        Satisfy the constraints. Try the fast naive solver first, and fall
        back to the CSP solver if it does not converge.

        :raises RandomizationError: If no solution satisfying the constraints
            is found, or if no constraint solver is enabled.
        """
        if self._solve_naive(state):
            return
        self._solve_csp(state)

    def _solve_naive(self, state: _RandomizeState) -> bool:
        """
        Try to satisfy the constraints by re-randomizing constrained variables
        a bounded number of times. Faster than building a ``MultiVarProblem``
        when the constraints turn out to be easy.

        :return: ``True`` if the constraints are satisfied, ``False`` if the
            attempt budget is exhausted or naive solving is disabled.
        """
        constraints = state.constraints
        if len(constraints) == 0:
            return True
        if not self._naive_solve:
            return False
        result = state.result
        # Each attempt re-randomizes the constrained variables, which include
        # derived variables whose inputs may change. Randomizing a length
        # variable sets its lists' length, so a constrained list is retried at
        # the new length.
        to_randomize = [
            name
            for name in self._random_vars
            if name not in state.with_values and name in state.constrained_var_names
        ]
        attempts = 0
        while attempts < self._max_iterations:
            if utils.check_constraints(constraints, result):
                return True
            self._randomize_variables(to_randomize, state)
            attempts += 1
        return False

    def _solve_csp(self, state: _RandomizeState) -> None:
        """
        Solve the constraints with a ``MultiVarProblem``. Derived variables
        are excluded from the solver and recomputed from the solved values.
        Constraints that name a derived variable are checked once after solving.

        :raises RandomizationError: If no solver is enabled, if a derived
            variable sets a list length, or if a constraint that names a derived
            variable is not satisfied.
        """
        if not (self._sparse_solve or self._thorough_solve):
            raise utils.RandomizationError(
                'Naive solve failed, and sparse solve and thorough solve disabled.'
                ' There is no way to solve the problem.'
            )
        result = state.result
        # The solver excludes derived variables, so it cannot revise a list
        # length that is itself derived: the list's size would stay fixed while
        # the solver moved the variables the length is computed from. Only the
        # naive solver handles this combination.
        constrained = state.constrained_var_names
        derived_lengths = sorted(
            name
            for name in self._rand_list_lengths
            if name in self._derived_vars and name in constrained
        )
        if derived_lengths:
            raise utils.RandomizationError(
                'Cannot use the constraint solver for a derived variable that sets a'
                f' list length ({derived_lengths}). Only the naive solver supports such'
                ' variables. When enabled it runs first, so randomize() may succeed on'
                ' another seed if the naive solver satisfies the constraints there.'
            )
        non_derived = constrained - self._derived_vars
        # Constraints that name a derived variable are checked after solving.
        # The rest go to the constraint solver.
        csp_constraints = []
        deferred_constraints = []
        for con, con_vars in state.constraints:
            if any(var in self._derived_vars for var in con_vars):
                deferred_constraints.append((con, con_vars))
            else:
                csp_constraints.append((con, con_vars))
        if state.has_tmp_constraints or self._problem_changed or self._multi_var_problem is None:
            # Naive solve failed, so the list lengths must become constraints.
            csp_constraints = csp_constraints + self._get_list_length_constraints(non_derived)
            multi_var_problem = MultiVarProblem(
                random_getter=self._get_random,
                vars=[
                    self._random_vars[var_name]
                    for var_name in self._random_vars
                    if var_name in non_derived
                ],
                constraints=csp_constraints,
                max_iterations=self._max_iterations,
                max_domain_size=self._max_domain_size,
            )
            # Cache only the base problem, i.e. with no temporary constraints.
            if not state.has_tmp_constraints:
                self._multi_var_problem = multi_var_problem
                self._problem_changed = False
        else:
            multi_var_problem = self._multi_var_problem
        solution = multi_var_problem.solve(
            sparse=self._sparse_solve,
            sparsities=self._sparsities,
            thorough=self._thorough_solve,
            with_values=state.with_values,
            debug=state.debug,
        )
        if solution is None:
            raise utils.RandomizationError('Could not solve constraint satisfaction problem')
        result.update(solution)
        # Recompute the constrained derived variables from the solved values,
        # in dependency order, and check the constraints that name them.
        derived_to_recompute = [
            name for name in self._random_vars if name in constrained and name in self._derived_vars
        ]
        self._randomize_variables(derived_to_recompute, state)
        if deferred_constraints and not utils.check_constraints(deferred_constraints, result):
            raise utils.RandomizationError(
                'Could not satisfy a constraint that names a derived variable. The'
                ' constraint solver checks such constraints once, after solving, and does'
                ' not retry with new inputs. Enable the naive solver or relax the constraints.'
            )

    def post_randomize(self) -> None:
        """
        Called by :func:`randomize` after randomizing variables. Can be overridden to do something.

        :return: ``None``
        """
        pass

    def get_results(self) -> Dict[str, Any]:
        """
        Returns a dictionary of the results from the most recent randomization.
        This is mainly provided for testing purposes.

        Note that individual variables can be accessed as member variables of
        a RandObj instance, e.g.

        .. code-block:: python

            randobj = RandObj()
            randobj.add_rand_var('a', domain=range(10))
            randobj.randomize()
            print(randobj.a)

        :return: dictionary of the results from the most recent randomization.
        """
        # Return a new dict object rather than a reference to this object's __dict__
        return {k: self.__dict__[k] for k in self._random_vars}

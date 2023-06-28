# SPDX-License-Identifier: MIT
# Copyright (c) 2023 Imagination Technologies Ltd. All Rights Reserved

import constraint
from functools import partial
from itertools import product
from typing import Any, Callable, Iterable, Optional, Union
import random

from .. import utils
from ..random import dist


class RandVar:
    '''
    Randomizable variable. For internal use with :class:`RandObj`.

    :param name: The name of this random variable.
    :param _random: Provides the random generator object this instance will use to
        create random values. Either provide an existing instance of a :class:`Random`,
        or leave as ``None`` to use the global Python `random` package.
    :param order: The solution order for this variable with respect to other variables.
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
    :param constraints: List or tuple of constraints that apply to this random variable.
        Each of these apply only to the individual values in the list, if a length is
        specified.
    :param constraints: List or tuple of constraints that apply to this random variable.
        Each of these apply across the values in the list, if a length is specified.
    :param length: Specify a length > 0 to turn this variable into a list of random
        values. A value of 0 means a scalar value. A value >= 1 means a list of that length.
    :param max_iterations: The maximum number of failed attempts to solve the randomization
        problem before giving up.
    :param max_domain_size: The maximum size of domain that a constraint satisfaction problem
        may take. This is used to avoid poor performance. When a problem exceeds this domain
        size, we don't use the ``constraint`` package, but just use ``random`` instead.
    '''

    def __init__(self,
        name: str,
        *,
        _random: Optional[random.Random]=None,
        order: int=0,
        domain: Optional[utils.Domain]=None,
        bits: Optional[int]=None,
        fn: Optional[Callable]=None,
        args: Optional[tuple]=None,
        constraints: Optional[Iterable[utils.Constraint]]=None,
        list_constraints: Optional[Iterable[utils.Constraint]]=None,
        length: int,
        max_iterations: int,
        max_domain_size: int,
    ) -> None:
        self._random = _random
        self.name = name
        self.order = order
        self.length = length
        self.max_iterations = max_iterations
        self.max_domain_size = max_domain_size
        assert  ((domain is not None) != (fn is not None)) != (bits is not None), "Must specify exactly one of fn, domain or bits"
        if fn is None:
            assert args is None, "args has no effect without fn"
        self.domain = domain
        self.bits = bits
        self.fn = fn
        self.args = args
        self.constraints = constraints if constraints is not None else []
        if not (isinstance(self.constraints, tuple) or isinstance(self.constraints, list)):
            self.constraints = (self.constraints,)
        self.list_constraints = list_constraints if list_constraints is not None else []
        if not (isinstance(self.list_constraints, tuple) or isinstance(self.list_constraints, list)):
            self.list_constraints = (self.list_constraints,)
        # Default strategy is to randomize and check the constraints.
        self.check_constraints = len(self.constraints) > 0 or len(self.list_constraints) > 0
        self.randomizer = self.create_randomizer()

    def create_randomizer(self) -> Callable:
        '''
        Creates a randomizer function that returns an appropriate
        random value for a single instance of the variable, i.e. a single
        element of a list or a simple scalar variable.
        We do this to create a more optimal randomizer than the user might
        have specified that is functionally equivalent.

        :return: a function as described.
        :raises TypeError: if the domain is of a bad type.
        '''
        # self.fn, self.bits and self.domain should already be guaranteed
        # to be mutually exclusive - only one should be non-None.
        if self.fn is not None:
            if self.args is not None:
                return partial(self.fn, *self.args)
            else:
                return self.fn
        elif self.bits is not None:
            self.domain = range(0, 1 << self.bits)
            return partial(self._get_random().getrandbits, self.bits)
        else:
            # Handle possible types of domain.
            is_range = isinstance(self.domain, range)
            is_list_or_tuple = isinstance(self.domain, list) or isinstance(self.domain, tuple)
            is_dict = isinstance(self.domain, dict)
            # Range, list and tuple are handled nicely by the constraint package.
            # Other Iterables may not be, e.g. enum.Enum isn't, despite being an Iterable.
            is_iterable = isinstance(self.domain, Iterable)
            if is_iterable and not (is_range or is_list_or_tuple or is_dict):
                # Convert non-dict iterables to a tuple as we don't expect them to need to be mutable,
                # and tuple ought to be slightly more performant than list.
                try:
                    self.domain = tuple(self.domain)
                except TypeError:
                    raise TypeError(f'RandVar was passed a domain of bad type - {self.domain}. '
                                    'This was an Iterable but could not be converted to tuple.')
                is_list_or_tuple = True
            if self.check_constraints and (is_range or is_list_or_tuple) and len(self.domain) < self.max_domain_size:
                # If we are provided a sufficiently small domain and we have constraints, simply construct a
                # constraint solution problem instead.
                problem = constraint.Problem()
                problem.addVariable(self.name, self.domain)
                for con in self.constraints:
                    problem.addConstraint(con, (self.name,))
                # Produces a list of dictionaries
                solutions = problem.getSolutions()
                def solution_picker(solns):
                    return self._get_random().choice(solns)[self.name]
                self.check_constraints = False
                return partial(solution_picker, solutions)
            elif is_range:
                return partial(self._get_random().randrange, self.domain.start, self.domain.stop)
            elif is_list_or_tuple:
                return partial(self._get_random().choice, self.domain)
            elif is_dict:
                return partial(dist, self.domain, self._get_random())
            else:
                raise TypeError(f'RandVar was passed a domain of a bad type - {self.domain}. '
                                'Domain should be a range, list, tuple, dictionary or other Iterable.')

    def _get_random(self) -> random.Random:
        '''
        Internal function to get the appropriate randomization object.

        We can't store the package ``random`` in a member variable as this
        prevents pickling.

        :return: The appropriate random generator.
        '''
        if self._random is None:
            return random
        return self._random

    def get_domain_size(self) -> int:
        '''
        Return total domain size, accounting for length of this random variable.

        :return: domain size, integer.
        '''
        if self.domain is None:
            # If there's no domain, it means we can't estimate the complexity
            # of this variable. Return 1.
            return 1
        else:
            # length == 0 implies a scalar variable, 1 is a list of length 1
            if self.length == 0 or self.length == 1:
                return len(self.domain)
            else:
                # In this case it is effectively cartesian product, i.e.
                # n ** k, where n is the size of the domain and k is the length
                # of the list.
                return len(self.domain) ** self.length

    def can_use_with_constraint(self) -> bool:
        '''
        Check whether this random variable can be used in a
        ``constraint.Problem`` or not.
        Note this isn't depenedent on the domain size, just
        purely whether it will work.

        :return: bool, True if it can be used with ``constraint.Problem``.
        '''
        # constraint can handle the variable as long as it has a domain
        # and the domain isn't a dictionary.
        return self.domain is not None and not isinstance(self.domain, dict)

    def get_constraint_domain(self) -> utils.Domain:
        '''
        Get a ``constraint`` package friendly version of the domain
        of this random variable.

        :return: the variable's domain in a format that will work
        with the ``constraint`` package.
        '''
        if self.length == 0:
            # Straightforward, scalar
            return self.domain
        elif self.length == 1:
            # List of length one
            return [[x] for x in self.domain]
        else:
            # List of greater length, cartesian product.
            # Beware that this may be an extremely large domain.
            return product(self.domain, repeat=self.length)

    def randomize_once(self, constraints: Iterable[utils.Constraint], check_constraints: bool) -> Any:
        '''
        Get one random value that satisfies the constraints.

        :param constraints: The constraints that apply to this randomization.
        :param check_constraints: Whether constraints need to be checked.
        :return: A random value for the variable, respecting the constraints.
        :raises RandomizationError: When the problem cannot be solved in fewer than
            the allowed number of iterations.
        '''
        value = self.randomizer()
        if not check_constraints:
            return value
        value_valid = False
        iterations = 0
        while not value_valid:
            if iterations == self.max_iterations:
                raise utils.RandomizationError("Too many iterations, can't solve problem")
            problem = constraint.Problem()
            problem.addVariable(self.name, (value,))
            for con in constraints:
                problem.addConstraint(con, (self.name,))
            value_valid = problem.getSolution() is not None
            if not value_valid:
                value = self.randomizer()
            iterations += 1
        return value

    def randomize(self, temp_constraints:Union[Iterable[utils.Constraint], None]=None) -> Any:
        '''
        Returns a random value based on the definition of this random variable.
        Does not modify the state of the :class:`RandVar` instance.

        :param temp_constraints: Temporary constraints to apply only for
            this randomization.
        :return: A randomly generated value, conforming to the definition of
            this random variable, its constraints, etc.
        :raises RandomizationError: When the problem cannot be solved in fewer than
            the allowed number of iterations.
        '''
        check_constraints = self.check_constraints
        # Handle temporary constraints. Start with copy of existing constraints,
        # adding any temporary ones in.
        constraints = list(self.constraints)
        if temp_constraints is not None and len(temp_constraints) > 0:
            check_constraints = True
            constraints += temp_constraints
        if self.length == 0:
            return self.randomize_once(constraints, check_constraints)
        elif self.length == 1:
            return [self.randomize_once(constraints, check_constraints)]
        else:
            values = []
            # Create list of values, checking as we go that list constraints
            # are followed.
            # Try to construct a constraint solution problem, if possible.
            check_list_constraints = len(self.list_constraints) > 0
            use_csp = check_list_constraints and self.can_use_with_constraint() \
                    and len(self.domain) < self.max_domain_size
            for i in range(self.length):
                if use_csp:
                    problem = constraint.Problem()
                    possible_values = []
                    for x in self.domain:
                        new_values = list(values)
                        new_values.append(x)
                        possible_values.append(new_values)
                    problem.addVariable(self.name, possible_values)
                    for con in self.list_constraints:
                        problem.addConstraint(con, (self.name,))
                    solutions = problem.getSolutions()
                    if len(solutions) == 0:
                        raise utils.RandomizationError("Problem was unsolvable.")
                    values = self._get_random().choice(solutions)[self.name]
                else:
                    # Otherwise, just randomize and check.
                    new_value = self.randomize_once(constraints, check_constraints)
                    values_valid = not check_list_constraints or i == 0
                    iterations = 0
                    while not values_valid:
                        if iterations == self.max_iterations:
                            raise utils.RandomizationError("Too many iterations, can't solve problem")
                        problem = constraint.Problem()
                        problem.addVariable(self.name, (values + [new_value],))
                        for con in self.list_constraints:
                            problem.addConstraint(con, (self.name,))
                        values_valid = problem.getSolution() is not None
                        if not values_valid:
                            new_value = self.randomize_once(constraints, check_constraints)
                            iterations += 1
                    values.append(new_value)
            return values

# Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


"""Operators for assignment statements."""

import copy
from collections.abc import Iterable
from typing import Any

import oqpy
import oqpy.base
from malt.operators.variables import UndefinedReturnValue

from autoqasm import constants, errors, program, types
from autoqasm.types.conversions import var_type_from_oqpy
from autoqasm.types.deferred import DeferredVarMixin, make_deferred


def assign_for_output(target_name: str, value: Any) -> Any:
    """Operator declares the `oq` variable, or sets variable's value if it's
    already declared. Runs only for return statements on `main` decorated
    functions.

    Args:
        target_name (str): The name of assignment target. It is the variable
            name on the lhs of an assignment statement.
        value (Any): The value of assignment. It is the object on the rhs of
            an assignment statement.

    Returns:
        Any: Assignment value with updated name attribute if the value is an
        `oqpy` type. Otherwise, it returns unchanged assignment value.
    """
    if value is None:
        return None
    value = types.wrap_value(value)

    aq_context = program.get_program_conversion_context()
    oqpy_program = aq_context.get_oqpy_program()

    if isinstance(value, oqpy.base.OQPyExpression) and not isinstance(value, oqpy.base.Var):
        target = oqpy.FloatVar(name=target_name)
        oqpy_program.set(target, value)
        return target

    if isinstance(value, Iterable):
        retvals = []
        for i, item in enumerate(value):
            retvals.append(_add_assignment(f"{target_name}{i}", item))
        return retvals
    else:
        return _add_assignment(target_name, value)


def _add_assignment(target_name: str, value: Any) -> Any:
    """Adds a statement to the underlying oqpy program that assigns `target_name`
    to the `value`.

    Args:
        target_name (str): The name of assignment target.
        value (Any): The value of assignment.

    Returns:
        Any: Value of the assignment.
    """
    aq_context = program.get_program_conversion_context()
    oqpy_program = aq_context.get_oqpy_program()
    target = copy.copy(value)
    target.init_expression = None
    target.name = target_name

    if target_name == value.name:
        # Avoid statements like `a = a;`
        return value

    is_value_name_used = isinstance(value, oqpy.base.Var) and aq_context.is_var_name_used(
        value.name
    )
    if is_value_name_used or value.init_expression is None:
        oqpy_program.set(target, value)
    else:
        oqpy_program.set(target, value.init_expression)

    return target


def _resolve_retval(value: Any, ctx) -> Any:
    """Handle the special ``retval_`` variable that AutoGraph uses for return statements.

    AutoGraph transpiles ``return <return_value>`` into::

        retval_ = <return_value>
        return retval_

    This function handles that pattern, avoiding declaring a new variable
    unless it is necessary. If the value already exists as a variable in the
    program during subroutine processing, it is returned directly without
    wrapping or declaring a new variable.

    Deferred wrappers (``_DeferredVarMixin``) are unwrapped back to their raw
    Python value before calling ``wrap_value``, so the retval path behaves
    identically to the original code that never saw a deferred wrapper.
    """
    if (
        ctx.subroutines_processing
        and isinstance(value, oqpy.base.Var)
        and ctx.is_var_name_used(value.name)
    ):
        return value

    if ctx.subroutines_processing and isinstance(value, list):
        raise errors.UnsupportedSubroutineReturnType(
            "Subroutine returns an array or list, which is not allowed."
        )

    if isinstance(value, DeferredVarMixin):
        value = value._deferred_value

    return types.wrap_value(value)


def _promote_deferred_expression(
    target_name: str, value: oqpy.base.OQPyExpression, ctx
) -> oqpy.base.Var | None:
    """Promote a deferred plain-Python variable to a declared QASM variable.

    Called when a variable that was initially assigned a plain Python value
    (e.g. ``val = 0.5``) is later reassigned with a QASM expression
    (e.g. ``val = val + measure(q)``).

    Returns ``None`` if no deferred value exists for the target name and the
    expression is not a Var (e.g. a temporary expression like ``2 * theta``).
    In that case the caller should return the expression value as-is.
    """
    target = ctx.promote_deferred_value(target_name)
    if target is not None:
        return target
    return None


def _defer_python_value(target_name: str, value: Any, ctx) -> Any:
    """Wrap a plain Python value for deferred promotion and register it.

    If the value can be deferred (int, float, bool), returns a deferred
    wrapper that behaves as a plain numeric literal but lazily promotes to an
    oqpy variable when combined with a QASM expression.  The wrapper is
    stored via ``ctx.defer_python_value`` so that
    ``ctx.promote_deferred_value`` can retrieve it later.

    If the value's type cannot be deferred, it is returned unchanged.
    """
    deferred = make_deferred(value, target_name)
    if deferred is not value:
        ctx.defer_python_value(target_name, deferred)
    return deferred


def assign_stmt(target_name: str, value: Any) -> Any:
    """Operator declares the `oq` variable, or sets variable's value if it's
    already declared.

    Args:
        target_name (str): The name of assignment target. It is the variable
            name on the lhs of an assignment statement.
        value (Any): The value of assignment. It is the object on the rhs of
            an assignment statement.

    Returns:
        Any: Assignment value with updated name attribute if the value is an
        `oqpy` type. Otherwise, it returns unchanged assignment value.
    """
    # TODO: The logic branch for return value and measurement should be handled
    # in different converters.
    if isinstance(value, UndefinedReturnValue):
        return value

    ctx = program.get_program_conversion_context()
    is_target_name_used = ctx.is_var_name_used(target_name)
    is_value_name_used = isinstance(value, oqpy.base.Var) and ctx.is_var_name_used(value.name)

    if target_name == constants.RETVAL_VARIABLE_NAME:
        value = _resolve_retval(value, ctx)
        if isinstance(value, oqpy.base.Var) and ctx.is_var_name_used(value.name):
            return value
        if not isinstance(value, (oqpy.base.Var, oqpy.base.OQPyExpression)):
            return value

    if is_target_name_used and isinstance(value, (oqpy.base.Var, oqpy.base.OQPyExpression)):
        target = _get_oqpy_program_variable(target_name)
        _validate_assignment_types(target, value)
    elif isinstance(value, oqpy.base.Var):
        target = copy.copy(value)
        target.init_expression = None
        target.name = target_name
    elif isinstance(value, oqpy.base.OQPyExpression):
        target = _promote_deferred_expression(target_name, value, ctx)
        if target is None:
            return value
    else:
        return _defer_python_value(target_name, value, ctx)

    oqpy_program = ctx.get_oqpy_program()

    value_init_expression = value.init_expression if isinstance(value, oqpy.base.Var) else None
    if is_value_name_used or value_init_expression is None:
        # Directly assign the value to the target.
        # For example:
        #   a = b;
        # where `b` is previously declared.
        oqpy_program.set(target, value)
    elif target.name not in oqpy_program.declared_vars and ctx.at_function_root_scope:
        # Explicitly declare and initialize the variable at the root scope.
        # For example:
        #   int[32] a = 10;
        # where `a` is at the root scope of the function (not inside any if/for/while block).
        target.init_expression = value_init_expression
        oqpy_program.declare(target)
    else:
        # Set to `value_init_expression` to avoid declaring an unnecessary variable.
        # The variable will be set in the current scope and auto-declared at the root scope.
        # For example, the `a = 1` and `a = 0` statements in the following:
        #   int[32] a;
        #   if (b == True) { a = 1; }
        #   else { a = 0; }
        # where `b` is previously declared.
        oqpy_program.set(target, value_init_expression)

    return target


def _get_oqpy_program_variable(var_name: str) -> oqpy.base.Var:
    """Return oqpy variable of the specified name used in the oqpy program.

    Args:
        var_name (str): Name of the variable

    Returns:
        oqpy.base.Var: Variable with the specified name in the oqpy program.
    """
    oqpy_program = program.get_program_conversion_context().get_oqpy_program()
    variables = {**oqpy_program.declared_vars, **oqpy_program.undeclared_vars}
    return variables[var_name]


def _validate_assignment_types(var1: oqpy.base.Var, var2: oqpy.base.Var) -> None:
    """Validates that the size and type of the variables are compatible for assignment.

    Args:
        var1 (oqpy.base.Var): Variable to validate.
        var2 (oqpy.base.Var): Variable to validate.
    """
    if var_type_from_oqpy(var1) != var_type_from_oqpy(var2):
        raise errors.InvalidAssignmentStatement(
            "Variables in assignment statements must have the same type"
        )

    if isinstance(var1, oqpy.ArrayVar) and isinstance(var2, oqpy.ArrayVar):
        if var1.dimensions != var2.dimensions:
            raise errors.InvalidAssignmentStatement(
                "Arrays in assignment statements must have the same dimensions"
            )
    elif isinstance(var1, oqpy.classical_types._SizedVar) and isinstance(
        var2, oqpy.classical_types._SizedVar
    ):
        var1_size = var1.size or 1
        var2_size = var2.size or 1
        if var1_size != var2_size:
            raise errors.InvalidAssignmentStatement(
                "Variables in assignment statements must have the same size"
            )

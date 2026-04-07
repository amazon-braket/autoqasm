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


"""Operators for control flow constructs (e.g. if, for, while)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import oqpy.base

from autoqasm import program
from autoqasm.types import Range, is_qasm_type


def for_stmt(
    iter: Iterable | oqpy.Range | oqpy.Qubit,
    extra_test: Callable[[], Any] | None,
    body: Callable[[Any], None],
    get_state: Any,
    set_state: Any,
    symbol_names: Any,
    opts: dict,
) -> None:
    """Implements a for loop.

    Args:
        iter (Iterable | Range | Qubit): The iterable to be looped over.
        extra_test (Callable[[], Any] | None): A function to cause the loop to break if true.
        body (Callable[[Any], None]): The body of the for loop.
        get_state (Any): Unused.
        set_state (Any): Unused.
        symbol_names (Any): Unused.
        opts (dict): Options of the for loop.
    """
    del get_state, set_state, symbol_names
    if extra_test is not None:
        raise NotImplementedError("break and return statements are not supported in for loops.")

    if is_qasm_type(iter):
        _oqpy_for_stmt(iter, body, opts)
    else:
        _py_for_stmt(iter, body)


def _oqpy_for_stmt(
    iter: oqpy.Range | oqpy.Qubit,
    body: Callable[[Any], None],
    opts: dict,
) -> None:
    """Overload of for_stmt that produces an oqpy for loop."""
    ctx = program.get_program_conversion_context()
    if isinstance(iter, oqpy.Qubit):
        iter = Range(iter.size)

    def _trace(ctx):
        with ctx.for_in(iter, opts["iterate_names"]) as f:
            body(f)

    _two_pass_trace(ctx, _trace)


def _py_for_stmt(
    iter: Iterable,
    body: Callable[[Any], None],
) -> None:
    """Overload of for_stmt that executes a Python for loop."""
    for target in iter:
        body(target)


def while_stmt(
    test: Callable[[], Any],
    body: Callable[[], None],
    get_state: Any,
    set_state: Any,
    symbol_names: Any,
    opts: dict,
) -> None:
    """Implements a while loop.

    Args:
        test (Callable[[], Any]): The condition of the while loop.
        body (Callable[[], None]): The body of the while loop.
        get_state (Any): Unused.
        set_state (Any): Unused.
        symbol_names (Any): Unused.
        opts (dict): Options of the while loop.
    """
    del get_state, set_state, symbol_names, opts
    ctx = program.get_program_conversion_context()
    oqpy_program = ctx.get_oqpy_program()
    pre_trace_state = _capture_pre_trace_state(ctx, oqpy_program)
    if is_qasm_type(test()):
        _oqpy_while_stmt(test, body, pre_trace_state)
    else:
        _py_while_stmt(test, body)


def _oqpy_while_stmt(
    test: Callable[[], Any],
    body: Callable[[], None],
    pre_trace_state: dict,
) -> None:
    """Overload of while_stmt that produces an oqpy while loop."""
    ctx = program.get_program_conversion_context()

    def _trace(ctx):
        with ctx.while_loop(test()):
            body()

    _two_pass_trace(ctx, _trace, pre_trace_state=pre_trace_state)


def _py_while_stmt(
    test: Callable[[], Any],
    body: Callable[[], None],
) -> None:
    """Overload of while_stmt that executes a Python while loop."""
    while test():
        body()


def _capture_pre_trace_state(
    ctx: program.ProgramConversionContext,
    oqpy_program: oqpy.base.Program,
) -> dict:
    """Capture the program state needed to roll back a first-pass trace."""
    return {
        "var_idx": ctx._var_idx,
        "scope_lengths": [len(s.body) for s in oqpy_program.stack],
        "deferred": dict(ctx._deferred_python_values),
        "declared_vars": dict(oqpy_program.declared_vars),
    }


def _rollback_and_pre_promote(
    ctx: program.ProgramConversionContext,
    oqpy_program: oqpy.base.Program,
    pre_trace_state: dict,
    promoted_names: set[str],
) -> None:
    """Undo the first-pass trace output and pre-promote the discovered
    deferred values so the second pass sees them as QASM variables."""
    for scope, orig_len in zip(oqpy_program.stack, pre_trace_state["scope_lengths"]):
        del scope.body[orig_len:]
    oqpy_program.declared_vars = pre_trace_state["declared_vars"]

    ctx._var_idx = pre_trace_state["var_idx"]
    ctx._deferred_python_values = pre_trace_state["deferred"]
    for name in promoted_names:
        ctx._deferred_python_values[name].promoted_var = None
        ctx.promote_deferred_value(name)


def _two_pass_trace(
    ctx: program.ProgramConversionContext,
    trace_fn: Callable[[program.ProgramConversionContext], None],
    pre_trace_state: dict | None = None,
) -> None:
    """Run *trace_fn* once.  If any deferred Python values were promoted
    during that run, discard the output and re-run with those values
    pre-promoted so that every reference in the loop body (comparisons,
    gate parameters, reverse operators) sees the QASM variable.

    If no deferred values are promoted the first-pass output is kept as-is.
    """
    oqpy_program = ctx.get_oqpy_program()
    if pre_trace_state is None:
        pre_trace_state = _capture_pre_trace_state(ctx, oqpy_program)

    # --- First pass ---
    trace_fn(ctx)

    promoted_names = set(pre_trace_state["deferred"]) - set(ctx._deferred_python_values)
    if not promoted_names:
        return

    # --- Discard first pass ---
    _rollback_and_pre_promote(ctx, oqpy_program, pre_trace_state, promoted_names)

    # --- Second pass ---
    trace_fn(ctx)


def if_stmt(
    cond: Any,
    body: Callable[[], Any],
    orelse: Callable[[], Any],
    get_state: Any,
    set_state: Any,
    symbol_names: Any,
    nouts: int,
) -> None:
    """Implements an if/else statement.

    Args:
        cond (Any): The condition of the if statement.
        body (Callable[[], Any]): The contents of the if block.
        orelse (Callable[[], Any]): The contents of the else block.
        get_state (Any): Unused.
        set_state (Any): Unused.
        symbol_names (Any): Unused.
        nouts (int): The number of outputs from the if block.
    """
    del get_state, set_state, symbol_names, nouts
    if is_qasm_type(cond):
        _oqpy_if_stmt(cond, body, orelse)
    else:
        _py_if_stmt(cond, body, orelse)


def _oqpy_if_stmt(
    cond: Any,
    body: Callable[[], Any],
    orelse: Callable[[], Any],
) -> None:
    """Overload of if_stmt that stages an oqpy cond."""
    program_conversion_context = program.get_program_conversion_context()
    with program_conversion_context.if_block(cond):
        body()
    with program_conversion_context.else_block():
        orelse()


def _py_if_stmt(cond: Any, body: Callable[[], Any], orelse: Callable[[], Any]) -> None:
    """Overload of if_stmt that executes a Python if statement."""
    if cond:
        body()
    else:
        orelse()

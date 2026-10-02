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


"""Utility functions that handle qubit construction and naming."""

from __future__ import annotations

import re
from functools import singledispatch
from typing import Any

import oqpy.base
from openpulse.printer import dumps

from autoqasm import errors, program


def _get_physical_qubit_indices(qids: list[str]) -> list[int]:
    """Convert physical qubit labels to the corresponding qubit indices.

    Args:
        qids (list[str]): Physical qubit labels.

    Returns:
        list[int]: Qubit indices corresponding to the input physical qubits.
    """
    braket_qubits = []
    for qid in qids:
        if not (isinstance(qid, str) and re.match(r"\$\d+", qid)):
            raise ValueError(
                f"Invalid physical qubit label: '{qid}'. Physical qubit must be labeled as a string"
                "with '$' followed by an integer. For example: '$1'."
            )
        braket_qubits.append(int(qid[1:]))
    return braket_qubits


@singledispatch
def _qubit(qid: Any) -> oqpy.Qubit:
    """Maps a given qubit representation to an oqpy qubit.

    Args:
        qid (Any): The qubit argument provided to a gate.

    Returns:
        Qubit: A translated oqpy qubit.

    Raises:
        errors.InvalidQubitIdentifier: ``qid`` cannot be used as a qubit.
    """
    raise errors.InvalidQubitIdentifier(qid)


@_qubit.register
def _(qid: bool) -> oqpy.Qubit:
    # `bool` is a subclass of `int`, so without this, `singledispatch` would route
    # `h(True)` to the `int` arm and emit a gate on qubit 1.
    raise errors.InvalidQubitIdentifier(qid)


@_qubit.register
def _(qid: int) -> oqpy.Qubit:
    # Integer virtual qubit, like `h(0)`
    ctx = program.get_program_conversion_context()
    ctx.register_qubit(qid)
    return ctx.global_qubit_register._index_by_expression(qid)


@_qubit.register
def _(qid: oqpy._ClassicalVar) -> oqpy.Qubit:
    # Indexed by variable, such as i in range(n); h(i)
    ctx = program.get_program_conversion_context()
    if ctx.get_declared_qubits() is None:
        raise errors.UnknownQubitCountError()
    return ctx.global_qubit_register._index_by_expression(qid.name)


@_qubit.register
def _(qid: oqpy.base.OQPyExpression) -> oqpy.Qubit:
    # Indexed by expression, such as i in range(n); h(i + 1)
    ctx = program.get_program_conversion_context()
    if ctx.get_declared_qubits() is None:
        raise errors.UnknownQubitCountError()

    qubit_idx_expr = dumps(qid.to_ast(ctx.get_oqpy_program()))
    return ctx.global_qubit_register._index_by_expression(qubit_idx_expr)


@_qubit.register
def _(qid: str) -> oqpy.Qubit:
    # Physical qubit label, like `h("$0")`
    if qid.startswith("$"):
        qubit_idx = qid[1:]
        try:
            qubit_idx = int(qubit_idx)
        except ValueError:
            raise ValueError(f"invalid physical qubit label: '{qid}'")
        return oqpy.PhysicalQubits[qubit_idx]
    else:
        raise ValueError(f"invalid qubit label: '{qid}'")


@_qubit.register
def _(qid: oqpy.Qubit) -> oqpy.Qubit:
    return qid


def _index_global_qubit_register(index: Any) -> oqpy.Qubit:
    """Resolves ``aq.qubits[index]`` inside a converted program.

    Accepts the same virtual qubit index types as a gate target (``int``, integer
    variables, and integer expressions), so ``h(aq.qubits[i])`` is equivalent to
    ``h(i)``. Physical qubit labels and qubit objects are not valid register indices.

    Args:
        index (Any): The index into the global qubit register.

    Returns:
        oqpy.Qubit: The qubit at ``index``.

    Raises:
        errors.InvalidQubitIdentifier: ``index`` is not a valid register index.
    """
    if isinstance(index, (str, oqpy.Qubit)):
        raise errors.InvalidQubitIdentifier(index)
    return _qubit(index)

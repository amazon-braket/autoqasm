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

"""Qubit identifier types and the program-level qubit register."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, get_args

import oqpy
import oqpy.base

from autoqasm import constants, errors
from braket.registers import Qubit

QubitIdentifierType = int | str | Qubit | oqpy._ClassicalVar | oqpy.base.OQPyExpression | oqpy.Qubit

# Precompute the type tuple once. get_args(QubitIdentifierType) is
# an expensive operation and is called on every gate emission.
_QUBIT_IDENTIFIER_TYPES: tuple[type, ...] = get_args(QubitIdentifierType)


def is_qubit_identifier_type(qubit: Any) -> bool:
    """Checks if a given object is a qubit identifier type.

    Args:
        qubit (Any): The object to check.

    Returns:
        bool: True if the object is a qubit identifier type, False otherwise.
    """
    return isinstance(qubit, _QUBIT_IDENTIFIER_TYPES)


def _as_qubit_iterable(
    qubits: QubitIdentifierType | Iterable[QubitIdentifierType] | None,
    default: Iterable[QubitIdentifierType] | None = None,
) -> Iterable[QubitIdentifierType]:
    """Normalize a qubit argument to an iterable. ``None`` maps to ``default`` (an empty
    list if not provided); a single qubit identifier is wrapped in a list; iterables
    (including :class:`GlobalQubitRegister`) pass through unchanged."""
    if qubits is None:
        qubits = default if default is not None else []
    if is_qubit_identifier_type(qubits):
        return [qubits]
    return qubits


class GlobalQubitRegister:
    def __init__(self, size: int | None = None):
        self._var = oqpy.Qubit(constants.QUBIT_REGISTER, size=size, needs_declaration=False)

    @property
    def name(self) -> str:
        return self._var.name

    @property
    def size(self) -> int | None:
        return self._var.size

    @size.setter
    def size(self, value: int) -> None:
        self._var.size = value

    @property
    def oqpy_var(self) -> oqpy.Qubit:
        """The underlying oqpy variable used to declare the register in OpenQASM."""
        return self._var

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r}, size={self.size!r})"

    def __str__(self) -> str:
        return self.name

    def __len__(self) -> int:
        if self.size is None:
            raise errors.UnknownQubitCountError()
        return self.size

    def __iter__(self) -> Iterator[int]:
        return iter(range(len(self)))

    def __getitem__(self, index: int | str) -> oqpy.Qubit:
        """Returns an oqpy.Qubit referring to ``__qubits__[index]``.
        ``index`` is either an integer index or a string containing
        an already-serialized OpenQASM index expression.
        """
        if isinstance(index, bool) or not isinstance(index, (int, str)):
            raise TypeError(f"invalid qubit register index: {index!r}")
        return oqpy.Qubit(f"{self.name}[{index}]", needs_declaration=False)

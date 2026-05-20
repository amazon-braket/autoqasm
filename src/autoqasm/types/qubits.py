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

from collections.abc import Iterator
from typing import Any, get_args

import oqpy
import oqpy.base

from autoqasm import constants
from braket.registers import Qubit

QubitIdentifierType = int | str | Qubit | oqpy._ClassicalVar | oqpy.base.OQPyExpression | oqpy.Qubit

_QUBIT_IDENTIFIER_TYPES: tuple[type, ...] = get_args(QubitIdentifierType)


def is_qubit_identifier_type(qubit: Any) -> bool:
    """Checks if a given object is a qubit identifier type.

    Args:
        qubit (Any): The object to check.

    Returns:
        bool: True if the object is a qubit identifier type, False otherwise.
    """
    return isinstance(qubit, _QUBIT_IDENTIFIER_TYPES)


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
        return self.name

    def __len__(self) -> int:
        return self.size

    def __iter__(self) -> Iterator[int]:
        return iter(range(len(self)))

    def __getitem__(self, index: int | str) -> oqpy.Qubit:
        """Returns an oqpy.Qubit referring to ``__qubits__[index]``."""
        return oqpy.Qubit(f"{self.name}[{index}]", needs_declaration=False)

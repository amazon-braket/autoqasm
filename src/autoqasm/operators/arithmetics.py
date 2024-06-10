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

"""Operators for arithmetic operators: // """

from __future__ import annotations

from typing import Any

from autoqasm import program
from autoqasm import types as aq_types

from .utils import _register_and_convert_parameters


def fd_(a: Any, b: Any) -> int | aq_types.IntVar:
    """Functional form of "//"

    Args:
        a (Any) : The first operator can be int | IntVar
        b (Any) : The second operator can be int | IntVar

    Returns :
        int | IntVar : floor division of a by b
    """
    if aq_types.is_qasm_type(a) or aq_types.is_qasm_type(b):
        return _aq_fd(a, b)
    else:
        return a / b


def _aq_fd(a: Any, b: Any) -> aq_types.IntVar:
    a, b = _register_and_convert_parameters(a, b)

    oqpy_program = program.get_program_conversion_context().get_oqpy_program()
    result = aq_types.IntVar()
    oqpy_program.declare(result)
    oqpy_program.set(result, a / b)
    return result

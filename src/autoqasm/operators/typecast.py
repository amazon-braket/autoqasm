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


"""Operators for int cast statements."""
from __future__ import annotations

from typing import Any

from autoqasm import program
from autoqasm import types as aq_types


def int_(argument: Any, *args, **kwargs) -> aq_types.IntVar | int:
    """Functional form of "int".

    Args:
        argument (Any): object to be converted into an int.

    Returns:
        IntVar | int : IntVar object if argument is QASM type, else int.
    """
    if aq_types.is_qasm_type(argument):
        return _oqpy_int(argument)
    else:
        return _py_int(argument, *args, **kwargs)


def _oqpy_int(argument: Any) -> aq_types.IntVar:
    oqpy_program = program.get_program_conversion_context().get_oqpy_program()
    result = aq_types.IntVar()
    oqpy_program.declare(result)
    oqpy_program.set(result, argument)
    return result


def _py_int(argument: Any, *args, **kwargs) -> int:
    return int(argument, *args, **kwargs)

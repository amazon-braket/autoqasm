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

from autoqasm import program
from autoqasm import types as aq_types

from .utils import _register_and_convert_parameters


def fd_(
    num_: aq_types.IntVar | aq_types.FloatVar | int | float,
    den_: aq_types.IntVar | aq_types.FloatVar | int | float,
) -> int | aq_types.IntVar:
    """Functional form of "//".
    Args:
        num_ (aq_types.IntVar | aq_types.FloatVar | int | float) :
            The numerator of the integer division
        den_ (aq_types.IntVar | aq_types.FloatVar | int | float) :
            The denominator of the integer division
    Returns :
        int | IntVar : integer division, IntVar if either numerator or denominator
        are QASM types, else int
    """
    if aq_types.is_qasm_type(num_) or aq_types.is_qasm_type(den_):
        return _oqpy_fd(num_, den_)
    else:
        return _py_fd(num_, den_)


def _oqpy_fd(
    num_: aq_types.IntVar | aq_types.FloatVar,
    den_: aq_types.IntVar | aq_types.FloatVar,
) -> aq_types.IntVar:
    num_, den_ = _register_and_convert_parameters(num_, den_)
    oqpy_program = program.get_program_conversion_context().get_oqpy_program()
    num_is_float = isinstance(num_, aq_types.FloatVar)
    den_is_float = isinstance(den_, aq_types.FloatVar)

    # if they are of different types, then one must cast to FloatVar
    if num_is_float or den_is_float:
        if num_is_float:
            float_var = aq_types.FloatVar()
            oqpy_program.declare(float_var)
            oqpy_program.set(float_var, den_)
        if den_is_float:
            float_var = aq_types.FloatVar()
            oqpy_program.declare(float_var)
            oqpy_program.set(float_var, num_)

    result = aq_types.IntVar()
    oqpy_program.declare(result)
    oqpy_program.set(result, num_ / den_)
    return result


def _py_fd(
    num_: int | float,
    den_: int | float,
) -> int:
    return num_ // den_

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

"""Operators for arithmetic operators: //"""

from __future__ import annotations

from autoqasm import program
from autoqasm import types as aq_types

from .utils import _register_and_convert_parameters


def floor_div(
    num: aq_types.IntVar | aq_types.FloatVar | int | float,
    den: aq_types.IntVar | aq_types.FloatVar | int | float,
) -> int | aq_types.IntVar:
    """Functional form of "//".
    Args:
        num (IntVar | FloatVar | int | float) : The numerator of the integer division
        den (IntVar | FloatVar | int | float) : The denominator of the integer division
    Returns :
        int | IntVar : integer division, IntVar if either numerator or denominator
        are QASM types, else int
    """
    if aq_types.is_qasm_type(num) or aq_types.is_qasm_type(den):
        return _oqpy_floor_div(num, den)
    else:
        return _py_floor_div(num, den)


def _oqpy_floor_div(
    num: aq_types.IntVar | aq_types.FloatVar | int | float,
    den: aq_types.IntVar | aq_types.FloatVar | int | float,
) -> aq_types.IntVar | aq_types.FloatVar:
    num, den = _register_and_convert_parameters(num, den)
    oqpy_program = program.get_program_conversion_context().get_oqpy_program()
    num_is_float = isinstance(num, (aq_types.FloatVar, float))
    den_is_float = isinstance(den, (aq_types.FloatVar, float))

    # if either is a FloatVar, then both must be FloatVar
    if num_is_float and not den_is_float:
        den_float_var = aq_types.FloatVar()
        oqpy_program.declare(den_float_var)
        oqpy_program.set(den_float_var, den)
        den = den_float_var
    if den_is_float and not num_is_float:
        num_float_var = aq_types.FloatVar()
        oqpy_program.declare(num_float_var)
        oqpy_program.set(num_float_var, num)
        num = num_float_var

    # if either is a FloatVar, then the result will be a FloatVar
    result = aq_types.IntVar()
    oqpy_program.declare(result)
    oqpy_program.set(result, num / den)

    if num_is_float or den_is_float:
        float_result = aq_types.FloatVar()
        oqpy_program.declare(float_result)
        oqpy_program.set(float_result, result)
        return float_result

    return result


def _py_floor_div(
    num: int | float,
    den: int | float,
) -> int | float:
    return num // den

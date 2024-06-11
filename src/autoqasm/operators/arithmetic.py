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
        num_ (IntVar | FloatVar | int | float) : The numerator of the integer division
        den_ (IntVar | FloatVar | int | float) : The denominator of the integer division
    Returns :
        int | IntVar : integer division, IntVar if either numerator or denominator
        are QASM types, else int
    """
    if aq_types.is_qasm_type(num_) or aq_types.is_qasm_type(den_):
        return _oqpy_fd(num_, den_)
    else:
        return _py_fd(num_, den_)


def _oqpy_fd(
    num_: aq_types.IntVar | aq_types.FloatVar | int | float,
    den_: aq_types.IntVar | aq_types.FloatVar | int | float,
) -> aq_types.IntVar:
    num_, den_ = _register_and_convert_parameters(num_, den_)
    oqpy_program = program.get_program_conversion_context().get_oqpy_program()
    num_is_float = isinstance(num_, (aq_types.FloatVar, float))
    den_is_float = isinstance(den_, (aq_types.FloatVar, float))

    # if either is a FloatVar, then both must be FloatVar
    if num_is_float and not den_is_float:
        den_float_var = aq_types.FloatVar()
        oqpy_program.declare(den_float_var)
        oqpy_program.set(den_float_var, den_)
        den_ = den_float_var
    if den_is_float and not num_is_float:
        num_float_var = aq_types.FloatVar()
        oqpy_program.declare(num_float_var)
        oqpy_program.set(num_float_var, num_)
        num_ = num_float_var

    # if either is a FloatVar, then the result will be a FloatVar
    if num_is_float or den_is_float:
        result = aq_types.FloatVar()
    else:
        result = aq_types.IntVar()

    oqpy_program.declare(result)
    oqpy_program.set(result, num_ / den_)
    return result


def _py_fd(
    num_: int | float,
    den_: int | float,
) -> int | float:
    return num_ // den_

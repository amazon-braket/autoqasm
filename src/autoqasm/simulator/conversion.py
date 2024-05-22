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

from functools import singledispatch
from typing import Any, Union

import numpy as np
from braket.default_simulator.openqasm._helpers.casting import convert_bool_array_to_string
from braket.default_simulator.openqasm.parser.openqasm_ast import (
    ArrayLiteral,
    BitstringLiteral,
    BooleanLiteral,
    FloatLiteral,
    IntegerLiteral,
)

LiteralType = Union[BooleanLiteral, IntegerLiteral, FloatLiteral, ArrayLiteral, BitstringLiteral]


@singledispatch
def convert_to_output(value: LiteralType) -> Any:
    raise NotImplementedError(f"converting {value} to output")


@convert_to_output.register(IntegerLiteral)
@convert_to_output.register(FloatLiteral)
@convert_to_output.register(BooleanLiteral)
@convert_to_output.register(BitstringLiteral)
def _(value):
    return value.value


@convert_to_output.register
def _(value: ArrayLiteral):
    if isinstance(value.values[0], BooleanLiteral):
        return convert_bool_array_to_string(value)
    return np.array([convert_to_output(x) for x in value.values])

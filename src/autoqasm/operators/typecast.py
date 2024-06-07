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

from typing import Any

from autoqasm import types as aq_types


def typecast(type_: type, argument_: Any) -> aq_types.IntVar | int:
    """Operator declares the `oq` variable, or sets variable's value if it's
    already declared.

    Args:
        type_ (type): the type for the conversion
        argument_ (Any): object to be converted.

    Returns:
        IntVar | FloatVar | int | float: IntVar/FloatVar object if argument is QASM type, else int/float.
    """
    type_to_aq_type_map = {int: aq_types.IntVar, float: aq_types.FloatVar}
    if aq_types.is_qasm_type(argument_):
        if (
            argument_.size is not None
            and argument_.size > 1
            and isinstance(argument_, aq_types.BitVar)
        ):
            typecasted_arg = type_to_aq_type_map[type_](argument_[0])
            for index in range(1, argument_.size):
                typecasted_arg += type_to_aq_type_map[type_](argument_[index]) * 2**index
            return typecasted_arg
        else:
            return type_to_aq_type_map[type_](argument_)
    else:
        return type_(*argument_)

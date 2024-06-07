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


def int_typecast(argument_: Any, *args, **kwargs) -> aq_types.IntVar | int:
    """Operator declares the `oq` variable, or sets variable's value if it's
    already declared.

    Args:
        argument_ (Any): object to be converted into an int.

    Returns:
        IntVar | int : IntVar object if argument is QASM type, else int.
    """
    if aq_types.is_qasm_type(argument_):
        return aq_types.IntVar(argument_)
    else:
        return int(argument_, *args, **kwargs)

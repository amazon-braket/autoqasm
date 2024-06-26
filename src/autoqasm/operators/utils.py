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


"Utility methods for operators."

from __future__ import annotations

from typing import Any

from autoqasm import program
from autoqasm import types as aq_types


def _register_and_convert_parameters(
    *args: tuple[Any],
) -> list[aq_types.FloatVar] | aq_types.FloatVar:
    """Adds FreeParameters to the program conversion context parameter registry, and
    returns the associated FloatVar objects.

    Notes: Adding a parameter to the registry twice is safe. Conversion is a pass through
    for non-FreeParameter inputs. Input and output arity is the same.

    FloatVars are more compatible with the program conversion operations.

    Returns:
        list[FloatVar] | FloatVar: FloatVars for program conversion.
    """
    program_conversion_context = program.get_program_conversion_context()
    program_conversion_context.register_args(args)
    return args[0] if len(args) == 1 else args

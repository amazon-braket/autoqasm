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


"""Deferred variable wrappers for lazy promotion of Python values to QASM variables.

These wrappers subclass Python's numeric types (float, int) so they behave as
plain literals when used as gate parameters, but lazily promote to oqpy
variables when combined with QASM expressions via arithmetic operators.
"""

from typing import Any

import oqpy
import oqpy.base


class DeferredVarMixin:
    """Mixin that lazily promotes a Python numeric value to an oqpy variable
    when combined with a QASM expression. When used as a gate parameter the
    value remains a literal."""

    _oqpy_var_type: type = None

    def _deferred_init(self, value, name):
        self._deferred_name = name
        self._deferred_value = value
        self.promoted_var = None

    def get_or_create_var(self):
        """Return the promoted oqpy variable, creating it on first call."""
        if self.promoted_var is None:
            self.promoted_var = self._oqpy_var_type(
                init_expression=self._deferred_value, name=self._deferred_name
            )
        return self.promoted_var

    def _dispatch(self, op, other):
        if isinstance(other, oqpy.base.OQPyExpression):
            return getattr(self.get_or_create_var(), op)(other)
        return NotImplemented

    def __add__(self, other):
        r = self._dispatch("__add__", other)
        return r if r is not NotImplemented else super().__add__(other)

    def __radd__(self, other):
        r = self._dispatch("__radd__", other)
        return r if r is not NotImplemented else super().__radd__(other)

    def __sub__(self, other):
        r = self._dispatch("__sub__", other)
        return r if r is not NotImplemented else super().__sub__(other)

    def __rsub__(self, other):
        r = self._dispatch("__rsub__", other)
        return r if r is not NotImplemented else super().__rsub__(other)

    def __mul__(self, other):
        r = self._dispatch("__mul__", other)
        return r if r is not NotImplemented else super().__mul__(other)

    def __rmul__(self, other):
        r = self._dispatch("__rmul__", other)
        return r if r is not NotImplemented else super().__rmul__(other)

    def __truediv__(self, other):
        r = self._dispatch("__truediv__", other)
        return r if r is not NotImplemented else super().__truediv__(other)

    def __rtruediv__(self, other):
        r = self._dispatch("__rtruediv__", other)
        return r if r is not NotImplemented else super().__rtruediv__(other)


class DeferredFloat(DeferredVarMixin, float):
    """A Python float that lazily promotes to an oqpy FloatVar."""

    _oqpy_var_type = oqpy.FloatVar

    def __new__(cls, value, name):
        return float.__new__(cls, value)

    def __init__(self, value, name):
        self._deferred_init(value, name)


class DeferredInt(DeferredVarMixin, int):
    """A Python int that lazily promotes to an oqpy IntVar."""

    _oqpy_var_type = oqpy.IntVar

    def __new__(cls, value, name):
        return int.__new__(cls, value)

    def __init__(self, value, name):
        self._deferred_init(value, name)


def make_deferred(value: Any, name: str) -> Any:
    """Wrap a plain Python value in a deferred wrapper that lazily promotes
    to a QASM variable when used in QASM expressions.

    Returns the original value unchanged if it cannot be deferred.
    """
    if isinstance(value, float):
        return DeferredFloat(value, name)
    elif isinstance(value, bool):
        return DeferredInt(int(value), name)
    elif isinstance(value, int):
        return DeferredInt(value, name)
    return value

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

"""Tests for type-collision detection on input-parameter registration."""

import pytest
from braket.circuits.free_parameter import FreeParameter

import autoqasm as aq
from autoqasm.instructions import rx


def test_signature_int_conflicts_with_free_parameter_float() -> None:
    """A signature annotation of ``int`` conflicts with the implicit
    ``float`` type produced by passing ``FreeParameter(...)`` to a gate
    angle. We must raise rather than silently coerce one type to the other.
    """

    @aq.main
    def collision(theta: int):
        rx(0, FreeParameter("theta"))

    with pytest.raises(aq.errors.ParameterTypeError, match="theta"):
        collision.build()


def test_signature_bool_conflicts_with_free_parameter_float() -> None:
    @aq.main
    def collision(theta: bool):
        rx(0, FreeParameter("theta"))

    with pytest.raises(aq.errors.ParameterTypeError, match="theta"):
        collision.build()


def test_matching_types_are_ok() -> None:
    """Matching types (float + float) must not raise."""

    @aq.main
    def ok(theta: float):
        rx(0, FreeParameter("theta"))

    ir = ok.build().to_ir()
    assert "input float theta;" in ir


def test_bare_free_parameter_is_fine() -> None:
    """Without a conflicting signature annotation, ``FreeParameter`` keeps
    working as it always has."""

    @aq.main
    def ok():
        rx(0, FreeParameter("theta"))

    ir = ok.build().to_ir()
    assert "input float theta;" in ir


def test_register_input_parameter_same_type_is_idempotent() -> None:
    """Registering the same parameter twice with the same type is a no-op."""
    with aq.build_program() as ctx:
        first = ctx.register_input_parameter("theta", float)
        result = ctx.register_input_parameter("theta", float)
        # The second call returns None (already registered) and the
        # underlying var object is unchanged.
        assert result is None
        assert ctx._input_parameters["theta"] is first


def test_register_input_parameter_conflicting_types_raises() -> None:
    with aq.build_program() as ctx:
        ctx.register_input_parameter("theta", int)
        with pytest.raises(aq.errors.ParameterTypeError, match="theta"):
            ctx.register_input_parameter("theta", float)

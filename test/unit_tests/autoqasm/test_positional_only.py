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

"""Tests that positional-only subroutine parameters work."""

import autoqasm as aq
from autoqasm.instructions import rx


def test_positional_only_subroutine_parameter_builds() -> None:
    @aq.subroutine
    def my_sub(a: float, /, b: float):
        rx(0, a + b)

    @aq.main(num_qubits=1)
    def prog():
        my_sub(0.1, 0.2)

    ir = prog.build().to_ir()
    assert "def my_sub(float[64] a, float[64] b)" in ir
    assert "my_sub(0.1, 0.2);" in ir


def test_mixed_positional_only_and_positional_or_keyword_builds() -> None:
    """Multiple positional-only arguments followed by regular ones."""

    @aq.subroutine
    def my_sub(a: float, b: float, /, c: float, d: float):
        rx(0, a + b + c + d)

    @aq.main(num_qubits=1)
    def prog():
        my_sub(0.1, 0.2, 0.3, 0.4)

    ir = prog.build().to_ir()
    assert "def my_sub(float[64] a, float[64] b, float[64] c, float[64] d)" in ir


def test_positional_only_subroutine_with_qubit_argument() -> None:
    """The common case: a subroutine that takes a qubit argument before
    the positional-only barrier."""

    @aq.subroutine
    def my_sub(q: aq.Qubit, /, theta: float):
        rx(q, theta)

    @aq.main(num_qubits=1)
    def prog():
        my_sub(0, 0.5)

    ir = prog.build().to_ir()
    assert "def my_sub(qubit q, float[64] theta)" in ir

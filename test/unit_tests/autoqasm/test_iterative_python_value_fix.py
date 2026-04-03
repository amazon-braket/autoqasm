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

"""Tests for plain Python value iterative update fix.

These tests verify that plain Python values (float, int) initialized at root scope
and iteratively updated inside aq.range loops produce the same QASM output as
their explicit aq.FloatVar / aq.IntVar counterparts.
"""

import autoqasm as aq
from autoqasm.instructions import measure, rx


def test_float_init_loop_update():
    """Plain Python float 0.5 initialized and iteratively updated
    in an aq.range loop should produce correct QASM with a float[64] declaration."""

    @aq.main(num_qubits=3)
    def float_init_loop():
        val = 0.5
        for q in aq.range(3):
            val = val + measure(q)
            rx(0, val)

    expected = """OPENQASM 3.0;
qubit[3] __qubits__;
float[64] val = 0.5;
for int q in [0:3 - 1] {
    bit __bit_0__;
    __bit_0__ = measure __qubits__[q];
    val = val + __bit_0__;
    rx(val) __qubits__[0];
}"""

    result = float_init_loop.build().to_ir()
    assert result == expected


def test_int_init_loop_update():
    """Plain Python int 0 initialized and iteratively updated
    in an aq.range loop should produce correct QASM with an int[32] declaration."""

    @aq.main(num_qubits=3)
    def int_init_loop():
        val = 0
        for q in aq.range(3):
            val = val + measure(q)

    expected = """OPENQASM 3.0;
qubit[3] __qubits__;
int[32] val = 0;
for int q in [0:3 - 1] {
    bit __bit_0__;
    __bit_0__ = measure __qubits__[q];
    val = val + __bit_0__;
}"""

    result = int_init_loop.build().to_ir()
    assert result == expected


def test_float_init_loop_update_return():
    """Plain Python float 0.5 initialized, iteratively updated in an aq.range
    loop, and returned should produce correct QASM with output declaration."""

    @aq.main(num_qubits=3)
    def float_init_loop_return():
        val = 0.5
        for q in aq.range(3):
            val = val + measure(q)
        return val

    expected = """OPENQASM 3.0;
output float[64] val;
val = 0.5;
qubit[3] __qubits__;
for int q in [0:3 - 1] {
    bit __bit_0__;
    __bit_0__ = measure __qubits__[q];
    val = val + __bit_0__;
}"""

    result = float_init_loop_return.build().to_ir()
    assert result == expected


def test_preservation_floatvar_loop_update():
    """aq.FloatVar(0.5) + aq.range loop + measure + rx continues to produce
    correct QASM with proper variable declaration and iterative updates."""

    @aq.main(num_qubits=3)
    def floatvar_loop_update():
        val = aq.FloatVar(0.5)
        for q in aq.range(3):
            val = val + measure(q)
        rx(0, val)

    expected = """OPENQASM 3.0;
qubit[3] __qubits__;
float[64] val = 0.5;
for int q in [0:3 - 1] {
    bit __bit_1__;
    __bit_1__ = measure __qubits__[q];
    val = val + __bit_1__;
}
rx(val) __qubits__[0];"""

    result = floatvar_loop_update.build().to_ir()
    assert result == expected


def test_preservation_floatvar_loop_return():
    """aq.FloatVar(0.5) + aq.range loop + measure + return continues to
    produce correct QASM with proper output declaration."""

    @aq.main(num_qubits=3)
    def floatvar_loop_return():
        val = aq.FloatVar(0.5)
        for q in aq.range(3):
            val = val + measure(q)
        return val

    expected = """OPENQASM 3.0;
output float[64] val;
val = 0.5;
qubit[3] __qubits__;
for int q in [0:3 - 1] {
    bit __bit_1__;
    __bit_1__ = measure __qubits__[q];
    val = val + __bit_1__;
}"""

    result = floatvar_loop_return.build().to_ir()
    assert result == expected


def test_preservation_intvar_loop_update():
    """aq.IntVar(0) + aq.range loop + measure continues to produce correct
    QASM with proper variable declaration."""

    @aq.main(num_qubits=3)
    def intvar_loop_update():
        val = aq.IntVar(0)
        for q in aq.range(3):
            val = val + measure(q)

    expected = """OPENQASM 3.0;
qubit[3] __qubits__;
int[32] val = 0;
for int q in [0:3 - 1] {
    bit __bit_1__;
    __bit_1__ = measure __qubits__[q];
    val = val + __bit_1__;
}"""

    result = intvar_loop_update.build().to_ir()
    assert result == expected


def test_preservation_literal_float():
    """Plain Python float used as a gate parameter (no loop reassignment)
    continues to be treated as a literal constant."""

    @aq.main(num_qubits=1)
    def literal_float():
        rx(0, 0.5)

    expected = """OPENQASM 3.0;
qubit[1] __qubits__;
rx(0.5) __qubits__[0];"""

    result = literal_float.build().to_ir()
    assert result == expected


def test_preservation_plain_python_var_as_literal():
    """Plain Python variable assigned a value and never reassigned with a QASM
    expression should remain as a literal in the generated QASM.
    val = 0.5 followed by rx(0, val) should produce rx(0.5), NOT float[64] val = 0.5;"""

    @aq.main(num_qubits=1)
    def plain_var_as_literal():
        val = 0.5
        rx(0, val)

    expected = """OPENQASM 3.0;
qubit[1] __qubits__;
rx(0.5) __qubits__[0];"""

    result = plain_var_as_literal.build().to_ir()
    assert result == expected

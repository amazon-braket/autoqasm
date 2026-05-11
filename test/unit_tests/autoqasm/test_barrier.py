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

"""Tests for the ``barrier`` compiler directive."""

import pytest

import autoqasm as aq
from autoqasm.instructions import barrier, cnot, h


def test_barrier_on_qubits() -> None:
    @aq.main
    def program():
        h(0)
        barrier([0, 1])
        cnot(0, 1)

    expected_ir = """OPENQASM 3.0;
qubit[2] __qubits__;
h __qubits__[0];
barrier __qubits__[0], __qubits__[1];
cnot __qubits__[0], __qubits__[1];"""
    assert program.build().to_ir() == expected_ir


def test_barrier_single_qubit() -> None:
    @aq.main
    def program():
        h(0)
        barrier(0)

    expected_ir = """OPENQASM 3.0;
qubit[1] __qubits__;
h __qubits__[0];
barrier __qubits__[0];"""
    assert program.build().to_ir() == expected_ir


def test_barrier_all_qubits() -> None:
    @aq.main
    def program():
        h(0)
        barrier()
        cnot(0, 1)

    expected_ir = """OPENQASM 3.0;
qubit[2] __qubits__;
h __qubits__[0];
barrier;
cnot __qubits__[0], __qubits__[1];"""
    assert program.build().to_ir() == expected_ir


def test_barrier_disallowed_inside_gate_definition() -> None:
    """Barriers are compiler directives, not unitary gates, so they must not
    appear inside ``@aq.gate`` bodies."""

    @aq.gate
    def bad_gate(q: aq.Qubit):
        barrier(q)

    @aq.main
    def program():
        bad_gate(0)

    with pytest.raises(aq.errors.InvalidGateDefinition):
        program.build()

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

"""Tests for the IQM classical-control gates ``cc_prx`` and ``measure_ff``."""

import math

import pytest
from braket.devices import LocalSimulator

import autoqasm as aq
from autoqasm.instructions import cc_prx, h, measure, measure_ff


def test_measure_ff_emits_feedback_key() -> None:
    @aq.main
    def program():
        h(0)
        measure_ff(0, 0)

    ir = program.build().to_ir()
    assert "measure_ff(0) __qubits__[0];" in ir


def test_cc_prx_emits_angles_and_feedback_key() -> None:
    @aq.main
    def program():
        h(0)
        measure_ff(0, 0)
        cc_prx(1, 0.15, 0.25, 0)

    ir = program.build().to_ir()
    assert "cc_prx(0.15, 0.25, 0) __qubits__[1];" in ir


def test_measure_ff_different_feedback_keys() -> None:
    @aq.main
    def program():
        measure_ff(0, 0)
        measure_ff(1, 5)

    ir = program.build().to_ir()
    assert "measure_ff(0) __qubits__[0];" in ir
    assert "measure_ff(5) __qubits__[1];" in ir


def test_cc_prx_symbolic_angles() -> None:
    """``cc_prx`` should accept ``FreeParameterExpression``-style angles
    exactly like other parameterised gates (e.g. ``prx``)."""

    @aq.main
    def program(theta: float):
        measure_ff(0, 0)
        cc_prx(1, theta, 0.0, 0)

    ir = program.build().to_ir()
    assert "input float theta;" in ir
    assert "cc_prx(theta, 0.0, 0) __qubits__[1];" in ir


def test_cc_prx_disallowed_inside_gate_definition() -> None:
    """``cc_prx`` requires classical feedback; gate definitions must be
    purely unitary. Using it inside ``@aq.gate`` should raise
    ``InvalidGateDefinition``."""

    @aq.gate
    def bad_gate(q: aq.Qubit):
        cc_prx(q, 0.1, 0.2, 0)

    @aq.main
    def program():
        bad_gate(0)

    with pytest.raises(aq.errors.InvalidGateDefinition):
        program.build()


def test_measure_ff_disallowed_inside_gate_definition() -> None:
    @aq.gate
    def bad_gate(q: aq.Qubit):
        measure_ff(q, 0)

    @aq.main
    def program():
        bad_gate(0)

    with pytest.raises(aq.errors.InvalidGateDefinition):
        program.build()


def test_classical_control_runs_on_local_simulator() -> None:
    """End-to-end: measure |+> on qubit 0 (50/50 outcome), and conditionally
    X qubit 1 via ``cc_prx(pi, 0, key)`` on the measured-1 branch. Qubit 1
    outcomes should track the qubit-0 feedback, giving ``00`` / ``11``."""

    @aq.main
    def teleport_like():
        h(0)
        measure_ff(0, 0)
        cc_prx(1, math.pi, 0.0, 0)

    result = LocalSimulator().run(teleport_like, shots=200).result()
    counts = result.measurement_counts
    # Outcomes should be only the correlated Bell-like pair.
    for outcome in counts:
        assert outcome in {"00", "11"}, f"unexpected outcome: {outcome}"
    # With 200 shots we expect both outcomes to appear.
    assert "00" in counts
    assert "11" in counts


def test_classical_control_runs_on_autoqasm_simulator() -> None:
    """Same behaviour on the AutoQASM-backed simulator."""

    @aq.main
    def teleport_like():
        h(0)
        measure_ff(0, 0)
        cc_prx(1, math.pi, 0.0, 0)
        measure(1)

    result = LocalSimulator("autoqasm").run(teleport_like, shots=100).result()
    measurements = result.measurements
    feedback = [bool(v) for v in measurements["__ff_0__"]]
    qubit_1_key = next(k for k in measurements if k.startswith("__bit_"))
    qubit_1 = [bool(v) for v in measurements[qubit_1_key]]
    # Qubit 1 should match the feedback bit every time.
    assert feedback == qubit_1, "cc_prx failed to conditionally flip qubit 1"
    # Both outcomes should appear with 100 shots.
    assert any(feedback)
    assert not all(feedback)


def test_cc_prx_missing_feedback_raises() -> None:
    """If ``cc_prx`` is used before any ``measure_ff`` with the same
    feedback key, the AutoQASM simulator raises a clean ValueError."""

    @aq.main
    def missing_key():
        cc_prx(0, 0.1, 0.2, 42)

    with pytest.raises(ValueError, match="feedback key 42"):
        LocalSimulator("autoqasm").run(missing_key, shots=1).result()

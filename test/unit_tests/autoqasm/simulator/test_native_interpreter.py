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

import pytest

from autoqasm.simulator.native_interpreter import NativeInterpreter
from autoqasm.simulator.simulation import Simulation

INPUTS_QASM = "test/resources/inputs.qasm"


@pytest.mark.parametrize(
    "reset_instructions",
    (
        "for int q in [0:2 - 1] {\n    reset __qubits__[q];\n}",
        "array[int[32], 2] __arr__ = {0, 1};\nfor int q in __arr__ {\n    reset __qubits__[q];\n}",
        "reset __qubits__[0];\nreset __qubits__[1];",
        "reset __qubits__;",
    ),
)
def test_reset(reset_instructions):
    qasm = f"""
        OPENQASM 3.0;
        qubit[2] __qubits__;
        x __qubits__[0];
        {reset_instructions}
        bit[2] __bit_0__ = "00";
        __bit_0__[0] = measure __qubits__[0];
        __bit_0__[1] = measure __qubits__[1];
    """
    result = NativeInterpreter(Simulation(0, 0, 1)).simulate(qasm)
    assert result["__bit_0__"] == ["00"]


def test_inputs_outputs():
    with open(INPUTS_QASM, encoding="utf-8", mode="r") as f:
        qasm = f.read()

    result = NativeInterpreter(Simulation(1, 1, 1)).simulate(qasm, inputs={"theta": 0.0})
    assert result["return_value"] == [0]


def test_inputs_outputs_from_file():
    result = NativeInterpreter(Simulation(1, 1, 1)).simulate(
        INPUTS_QASM, inputs={"theta": 0.0}, is_file=True
    )
    assert result["return_value"] == [0]


def test_missing_input():
    qasm = """
        OPENQASM 3.0;
        input float theta;
    """
    with pytest.raises(NameError, match="Missing input variable"):
        NativeInterpreter(Simulation(0, 0, 1)).simulate(qasm)


def test_repeated_output_declaration():
    qasm = """
        OPENQASM 3.0;
        output bit return_value;
        output bit return_value;
        return_value = 0;
    """
    result = NativeInterpreter(Simulation(0, 0, 1)).simulate(qasm)
    assert result["return_value"] == [0]


def test_qubit_register():
    qasm = """
        OPENQASM 3.0;
        qubit[2] __qubits__;
        x __qubits__[1];
        bit[2] __bit_0__ = measure __qubits__;
    """
    result = NativeInterpreter(Simulation(2, 1, 1)).simulate(qasm)
    assert result["__bit_0__"] == ["01"]

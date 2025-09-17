import os
import textwrap

import pyqir
import pytest
from autoqasm.qir2qasm_trans.qir_trans import load
from autoqasm.qir2qasm_trans.qir_trans.translator import Exporter


def test_bitcode_load():
    """Test end-to-end conversion of a Bell pair QIR program to QASM."""
    bell = pyqir.SimpleModule("bell", num_qubits=2, num_results=2)
    qis = pyqir.BasicQisBuilder(bell.builder)

    # Add instructions to the module to create a Bell pair and measure both qubits.
    qis.h(bell.qubits[0])
    qis.cx(bell.qubits[0], bell.qubits[1])
    qis.mz(bell.qubits[0], bell.results[0])
    qis.mz(bell.qubits[1], bell.results[1])

    # Sample QIR content for a Bell pair circuit
    # Expected QASM output
    expected_qasm = """
        OPENQASM 3.0;
        qubit[2] Qubits;
        bit[2] Results;
        h Qubits[0];
        cx Qubits[0], Qubits[1];
        Results[0] = measure Qubits[0];
        Results[1] = measure Qubits[1];
    """

    file_path = "test/resources/qir_test_file"
    benchmark_name = "bitcode_load"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.bc")

    with open(qir_file_path, "wb") as f:
        f.write(bell.bitcode())

    # Load the QIR module
    module = load(str(qir_file_path))

    # Convert to QASM using the Exporter
    exporter = Exporter()
    qasm_output = exporter.dumps(module)

    # Validate the complete output
    assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()


def test_load_error():
    """Test end-to-end conversion of a Bell pair QIR program to QASM."""
    bell = pyqir.SimpleModule("bell", num_qubits=2, num_results=2)
    qis = pyqir.BasicQisBuilder(bell.builder)

    # Add instructions to the module to create a Bell pair and measure both qubits.
    qis.h(bell.qubits[0])
    qis.cx(bell.qubits[0], bell.qubits[1])
    qis.mz(bell.qubits[0], bell.results[0])
    qis.mz(bell.qubits[1], bell.results[1])

    file_path = "test/resources/qir_test_file"
    benchmark_name = "load_error"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.qir")

    with open(qir_file_path, "wb") as f:
        f.write(bell.bitcode())

    # Convert to QASM using the Exporter
    with pytest.raises(ValueError, match=r"Unsupported file extension: .qir"):
        load(str(qir_file_path))

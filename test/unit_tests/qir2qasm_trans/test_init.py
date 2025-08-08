import tempfile
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
        include "stdgates.inc";
        qubit[2] Qubits;
        bit[2] Results;
        h Qubits[0];
        cx Qubits[0], Qubits[1];
        Results[0] = measure Qubits[0];
        Results[1] = measure Qubits[1];
    """

    # Create a temporary QIR file
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".bc", delete=True) as temp_file:
        temp_file.write(bell.bitcode())
        temp_file.flush()  # Ensure content is written to disk

        # Load the QIR module
        module = load(temp_file.name)

        # Convert to QASM using the Exporter
        exporter = Exporter()
        qasm_output = exporter.dumps(module)

        # Validate the complete output
        assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()
    # File automatically deleted here


def test_load_error():
    """Test end-to-end conversion of a Bell pair QIR program to QASM."""
    bell = pyqir.SimpleModule("bell", num_qubits=2, num_results=2)
    qis = pyqir.BasicQisBuilder(bell.builder)

    # Add instructions to the module to create a Bell pair and measure both qubits.
    qis.h(bell.qubits[0])
    qis.cx(bell.qubits[0], bell.qubits[1])
    qis.mz(bell.qubits[0], bell.results[0])
    qis.mz(bell.qubits[1], bell.results[1])

    # Create a temporary QIR file
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".qir", delete=True) as temp_file:
        temp_file.write(bell.bitcode())
        temp_file.flush()  # Ensure content is written to disk

        # Load the QIR module

        # Convert to QASM using the Exporter
        with pytest.raises(ValueError, match=r"Unsupported file extension: .qir"):
            module = load(temp_file.name)
    # File automatically deleted here
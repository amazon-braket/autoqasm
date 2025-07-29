import tempfile
import os
import textwrap
from autoqasm.qir2qasm_trans.qir_trans import load
from autoqasm.qir2qasm_trans.qir_trans.translator import Exporter


def test_bell_pair_qir_to_qasm_conversion():
    """Test end-to-end conversion of a Bell pair QIR program to QASM."""

    # Sample QIR content for a Bell pair circuit
    qir_content = """
        ; ModuleID = 'bell'
        source_filename = "bell"

        %Qubit = type opaque
        %Result = type opaque

        define void @main() #0 {
        entry:
          call void @__quantum__qis__cnot__body(%Qubit* null, %Qubit* inttoptr (i64 1 to %Qubit*))
          call void @__quantum__qis__cz__body(%Qubit* null, %Qubit* inttoptr (i64 1 to %Qubit*))
          call void @__quantum__qis__rz__body(double 1.000000e+01, %Qubit* null)
          call void @__quantum__qis__h__body(%Qubit* null)
          call void @__quantum__qis__mz__body(%Qubit* null, %Result* null)
          call void @__quantum__qis__mz__body(%Qubit* inttoptr (i64 1 to %Qubit*), %Result* inttoptr (i64 1 to %Result*))
          ret void
        }

        declare void @__quantum__qis__cnot__body(%Qubit*, %Qubit*)
        declare void @__quantum__qis__cz__body(%Qubit*, %Qubit*)
        declare void @__quantum__qis__rz__body(double, %Qubit*)
        declare void @__quantum__qis__h__body(%Qubit*)
        declare void @__quantum__qis__mz__body(%Qubit*, %Result* writeonly) #1

        attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="2" "required_num_results"="2" }
        attributes #1 = { "irreversible" }

        !llvm.module.flags = !{!0, !1, !2, !3}

        !0 = !{i32 1, !"qir_major_version", i32 1}
        !1 = !{i32 7, !"qir_minor_version", i32 0}
        !2 = !{i32 1, !"dynamic_qubit_management", i1 false}
        !3 = !{i32 1, !"dynamic_result_management", i1 false}
    """

    # Expected QASM output
    expected_qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] Qubit;
        bit[2] Result;
        cx Qubit[0], Qubit[1];
        cz Qubit[0], Qubit[1];
        rz(10.0) Qubit[0];
        h Qubit[0];
        Result[0] = measure Qubit[0];
        Result[1] = measure Qubit[1];
    """

    # Create a temporary QIR file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=True) as temp_file:
        temp_file.write(textwrap.dedent(qir_content))
        temp_file.flush()  # Ensure content is written to disk

        # Load the QIR module
        module = load(temp_file.name)

        # Convert to QASM using the Exporter
        exporter = Exporter()
        qasm_output = exporter.dumps(module)

        # Validate the complete output
        assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()
    # File automatically deleted here


def test_simple_hadamard_qir_to_qasm():
    """Test conversion of a simple Hadamard gate QIR program."""

    # Simple QIR content with just a Hadamard gate
    qir_content = """
        ; ModuleID = 'simple'
        source_filename = "simple"

        %Qubit = type opaque
        %Result = type opaque

        define void @main() #0 {
        entry:
          call void @__quantum__qis__h__body(%Qubit* null)
          call void @__quantum__qis__mz__body(%Qubit* null, %Result* null)
          ret void
        }

        declare void @__quantum__qis__h__body(%Qubit*)
        declare void @__quantum__qis__mz__body(%Qubit*, %Result* writeonly) #1

        attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="1" "required_num_results"="1" }
        attributes #1 = { "irreversible" }

        !llvm.module.flags = !{!0, !1, !2, !3}

        !0 = !{i32 1, !"qir_major_version", i32 1}
        !1 = !{i32 7, !"qir_minor_version", i32 0}
        !2 = !{i32 1, !"dynamic_qubit_management", i1 false}
        !3 = !{i32 1, !"dynamic_result_management", i1 false}
    """

    # Expected QASM output
    expected_qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] Qubit;
        bit[1] Result;
        h Qubit[0];
        Result[0] = measure Qubit[0];
    """

    # Create a temporary QIR file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=True) as temp_file:
        temp_file.write(textwrap.dedent(qir_content))
        temp_file.flush()  # Ensure content is written to disk

        # Load and convert
        module = load(temp_file.name)
        exporter = Exporter()
        qasm_output = exporter.dumps(module)

        # Validate the complete output
        assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()
    # File automatically deleted here


def test_existing_qir_file_conversion():
    """Test conversion using an existing QIR example file."""

    # Use the existing bell_pair.ll file
    qir_file_path = "src/qir2qasm_trans/QIR-example/bell_pair.ll"

    # Check if the file exists
    if not os.path.exists(qir_file_path):
        # Skip test if example file doesn't exist
        return

    # Expected QASM output (should match the bell_pair.ll file content)
    expected_qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] Qubit;
        bit[2] Result;
        cx Qubit[0], Qubit[1];
        cz Qubit[0], Qubit[1];
        rz(10.0) Qubit[0];
        h Qubit[0];
        Result[0] = measure Qubit[0];
        Result[1] = measure Qubit[1];
    """

    # Load and convert
    module = load(qir_file_path)
    exporter = Exporter()
    qasm_output = exporter.dumps(module)

    # Validate the complete output
    assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()

import os
import tempfile
import textwrap
from pathlib import Path

import pytest
from autoqasm.qir2qasm_trans.qir_trans import load
from autoqasm.qir2qasm_trans.qir_trans.translator import Exporter


def test_rxx_qir_to_qasm():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "rxx"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")
    qasm_file_path = os.path.join(file_path, f"{benchmark_name}.qasm")

    # Load and convert
    module = load(qir_file_path)
    exporter = Exporter()
    qasm_output = exporter.dumps(module)

    with open(qasm_file_path, "r") as f:
        expected_qasm = f.read()

    # Validate the complete output
    assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()


def test_arguments_qir_to_qasm():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "arguments"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")
    qasm_file_path = os.path.join(file_path, f"{benchmark_name}.qasm")

    # Load and convert
    module = load(qir_file_path)
    exporter = Exporter()
    qasm_output = exporter.dumps(module)

    with open(qasm_file_path, "r") as f:
        expected_qasm = f.read()

    # Validate the complete output
    assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()


def test_include_qir_to_qasm():
    # Sample QIR content for a Bell pair circuit
    qir_content = """
        ; ModuleID = 'bell'
        source_filename = "bell"

        %Qubit = type opaque
        %Result = type opaque

        define void @main() #0 {
        entry:
        call void @__quantum__qis__h__body(%Qubit* null)
        call void @__quantum__qis__cnot__body(%Qubit* null, %Qubit* inttoptr (i64 1 to %Qubit*))
        call void @__quantum__qis__mz__body(%Qubit* null, %Result* null)
        call void @__quantum__qis__mz__body(%Qubit* inttoptr (i64 1 to %Qubit*), %Result* inttoptr (i64 1 to %Result*))
        ret void
        }

        declare void @__quantum__qis__h__body(%Qubit*)

        declare void @__quantum__qis__cnot__body(%Qubit*, %Qubit*)

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
        qubit[2] Qubits;
        bit[2] Results;
        h Qubits[0];
        cx Qubits[0], Qubits[1];
        Results[0] = measure Qubits[0];
        Results[1] = measure Qubits[1];
    """

    with tempfile.TemporaryDirectory() as tmp_dir:
        qir_path = Path(tmp_dir) / "bell.ll"
        qir_path.write_text(textwrap.dedent(qir_content), encoding="utf-8")

        # Load the QIR module
        module = load(str(qir_path))

        # Convert to QASM using the Exporter
        exporter = Exporter(includes=["stdgates.inc"])
        qasm_output = exporter.dumps(module)

        # Validate the complete output
        assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()



def test_return_value_error():
    qir_content = """
        ; ModuleID = 'return_value_error'
        source_filename = "return_value_error.ll"

        %Result = type opaque

        declare void @my_test(%Result*, %Result*)

        define void @main() #0 {
        entry:
        call void @my_test(%Result* null, %Result* null)
        ret void
        }

        attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="1" }

        !llvm.module.flags = !{!0, !1, !2, !3}

        !0 = !{i32 1, !"qir_major_version", i32 1}
        !1 = !{i32 7, !"qir_minor_version", i32 0}
        !2 = !{i32 1, !"dynamic_qubit_management", i1 false}
        !3 = !{i32 1, !"dynamic_result_management", i1 false}
    """

    # Create a temporary QIR file
    with tempfile.TemporaryDirectory() as tmp_dir:
        qir_path = Path(tmp_dir) / "return_value_error.ll"
        qir_path.write_text(textwrap.dedent(qir_content), encoding="utf-8")

        # Load the QIR module
        module = load(str(qir_path))

        # Convert to QASM using the Exporter
        exporter = Exporter()
        with pytest.raises(Exception, match=r"Too much return value!"):
            exporter.dumps(module)


def test_main_func_error():
    qir_content = """
        ; ModuleID = 'main_func_error'
        source_filename = "main_func_error.ll"

        define void @main() #0 {
        entry:
        ret void
        }

        attributes #0 = {"output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="0" }

        !llvm.module.flags = !{!0, !1, !2, !3}

        !0 = !{i32 1, !"qir_major_version", i32 1}
        !1 = !{i32 7, !"qir_minor_version", i32 0}
        !2 = !{i32 1, !"dynamic_qubit_management", i1 false}
        !3 = !{i32 1, !"dynamic_result_management", i1 false}
    """

    # Create a temporary QIR file
    with tempfile.TemporaryDirectory() as tmp_dir:
        qir_path = Path(tmp_dir) / "main_func_error.ll"
        qir_path.write_text(textwrap.dedent(qir_content), encoding="utf-8")

        # Load the QIR module
        module = load(str(qir_path))

        # Convert to QASM using the Exporter
        exporter = Exporter()
        with pytest.raises(Exception, match=r"No main function defined!"):
            exporter.dumps(module)


def test_llvm_inst_error():
    qir_content = """
        ; ModuleID = 'llvm_inst_error'
        source_filename = "llvm_inst_error.ll"
        %MyStruct = type { i32, float }

        @g_i32     = global i32 42, align 4
        @g_struct  = global %MyStruct { i32 1, float 1.000000e+00 }, align 8
        @g_array   = global [4 x i8] zeroinitializer, align 1

        define void @main() #0 {
        entry:
        %0 = load i32, i32* @g_i32, align 4
        ret void
        }

        attributes #0 = {"entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="0" }
    """

    # Create a temporary QIR file
    with tempfile.TemporaryDirectory() as tmp_dir:
        qir_path = Path(tmp_dir) / "llvm_inst_error.ll"
        qir_path.write_text(textwrap.dedent(qir_content), encoding="utf-8")

        # Load the QIR module
        module = load(str(qir_path))

        # Convert to QASM using the Exporter
        exporter = Exporter()
        with pytest.raises(Exception, match=r"Undefined llvm instruction: load"):
            exporter.dumps(module)

import tempfile
import os
import textwrap

import pyqir
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


def test_rxx_qir_to_qasm():
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=True) as temp_file:
        temp_file.write(textwrap.dedent(qir_content))
        temp_file.flush()  # Ensure content is written to disk

        # Load the QIR module
        module = load(temp_file.name)

        # Convert to QASM using the Exporter
        exporter = Exporter()
        with pytest.raises(Exception, match=r"Too much return value!"):
            qasm_output = exporter.dumps(module)


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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=True) as temp_file:
        temp_file.write(textwrap.dedent(qir_content))
        temp_file.flush()  # Ensure content is written to disk

        # Load the QIR module
        module = load(temp_file.name)

        # Convert to QASM using the Exporter
        exporter = Exporter()
        with pytest.raises(Exception, match=r"No main function defined!"):
            qasm_output = exporter.dumps(module)


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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=True) as temp_file:
        temp_file.write(textwrap.dedent(qir_content))
        temp_file.flush()  # Ensure content is written to disk

        # Load the QIR module
        module = load(temp_file.name)

        # Convert to QASM using the Exporter
        exporter = Exporter()
        with pytest.raises(Exception, match=r"Undefined llvm instruction: load"):
            qasm_output = exporter.dumps(module)
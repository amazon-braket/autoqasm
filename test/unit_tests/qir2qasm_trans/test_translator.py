import os
import textwrap

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
    file_path = "test/resources/qir_test_file"
    benchmark_name = "include"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")
    qasm_file_path = os.path.join(file_path, f"{benchmark_name}.qasm")

    # Load and convert
    module = load(qir_file_path)
    exporter = Exporter(includes=['stdgates.inc'])
    qasm_output = exporter.dumps(module)

    with open(qasm_file_path, "r") as f:
        expected_qasm = f.read()

    # Validate the complete output
    assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()


def test_return_value_error():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "return_value_error"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")

    # Load the QIR module
    module = load(str(qir_file_path))

    # Convert to QASM using the Exporter
    exporter = Exporter()
    with pytest.raises(Exception, match=r"Too much return value!"):
        exporter.dumps(module)


def test_main_func_error():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "main_func_error"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")

    # Load the QIR module
    module = load(str(qir_file_path))

    # Convert to QASM using the Exporter
    exporter = Exporter()
    with pytest.raises(Exception, match=r"No main function defined!"):
        exporter.dumps(module)


def test_llvm_inst_error():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "llvm_inst_error"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")

    # Load the QIR module
    module = load(str(qir_file_path))

    # Convert to QASM using the Exporter
    exporter = Exporter()
    with pytest.raises(Exception, match=r"Undefined llvm instruction: load"):
        exporter.dumps(module)

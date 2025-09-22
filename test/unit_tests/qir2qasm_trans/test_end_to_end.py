import os
import textwrap

import pyqir
from autoqasm.qir2qasm_trans.qir_trans import load
from autoqasm.qir2qasm_trans.qir_trans.translator import Exporter


def test_bell_pyqir_to_qasm():
    """Test end-to-end conversion of a Bell pair pyqir program to QASM."""
    bell = pyqir.SimpleModule("bell", num_qubits=2, num_results=2)
    qis = pyqir.BasicQisBuilder(bell.builder)

    # Add instructions to the module to create a Bell pair and measure both qubits.
    qis.h(bell.qubits[0])
    qis.cx(bell.qubits[0], bell.qubits[1])
    qis.mz(bell.qubits[0], bell.results[0])
    qis.mz(bell.qubits[1], bell.results[1])

    file_path = "test/resources/qir_test_file"
    benchmark_name = "bell"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")
    qasm_file_path = os.path.join(file_path, f"{benchmark_name}.qasm")

    with open(qir_file_path, "w") as f:
        f.write(bell.ir())

    # Load and convert
    module = load(qir_file_path)
    exporter = Exporter()
    qasm_output = exporter.dumps(module)

    with open(qasm_file_path, "r") as f:
        expected_qasm = f.read()

    # Validate the complete output
    assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()


def test_arithmetic_pyqir_to_qasm():
    """Test end-to-end conversion of an arithmetic pyqir program to QASM."""

    mod = pyqir.SimpleModule("arithmetic", num_qubits=0, num_results=0)
    # Declare functions that can produce and consume integers at runtime.
    i32 = pyqir.IntType(mod.context, 32)
    get_int = mod.add_external_function("get_int", pyqir.FunctionType(i32, []))
    take_int = mod.add_external_function(
        "take_int", pyqir.FunctionType(pyqir.Type.void(mod.context), [i32])
    )

    # Add 3 to a number and multiply the result by 2.
    a = mod.builder.call(get_int, [])
    assert a is not None
    # Python numbers need to be converted into QIR constant values. Since it's being
    # added to a 32-bit integer returned by get_int, its type needs to be the same.
    three = pyqir.const(i32, 3)
    b = mod.builder.add(three, a)
    c = mod.builder.mul(pyqir.const(i32, 2), b)

    # Negation can be done by subtracting an integer from zero.
    x = mod.builder.call(get_int, [])
    assert x is not None
    negative_x = mod.builder.sub(pyqir.const(i32, 0), x)

    # Consume the results.
    mod.builder.call(take_int, [c])
    mod.builder.call(take_int, [negative_x])

    # Sample QIR content for the arithmetic circuit
    file_path = "test/resources/qir_test_file"
    benchmark_name = "arithmetic"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")
    qasm_file_path = os.path.join(file_path, f"{benchmark_name}.qasm")

    with open(qir_file_path, "w") as f:
        f.write(mod.ir())

    # Load and convert
    module = load(qir_file_path)
    exporter = Exporter()
    qasm_output = exporter.dumps(module)

    with open(qasm_file_path, "r") as f:
        expected_qasm = f.read()

    # Validate the complete output
    assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()


def test_bernstein_vazirani_qir_to_qasm():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "bernstein_vazirani"
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


def test_external_functions_qir_to_qasm():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "external_functions"
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


def test_dynamic_allocation_qir_to_qasm():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "dynamic_allocation"
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


def test_dynamic_if_then_qir_to_qasm():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "if_then"
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

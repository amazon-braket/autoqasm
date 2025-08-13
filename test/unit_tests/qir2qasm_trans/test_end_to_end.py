import os
import tempfile
import textwrap
from pathlib import Path

import pyqir
from autoqasm.qir2qasm_trans.qir_trans import load
from autoqasm.qir2qasm_trans.qir_trans.translator import Exporter


def test_bell_qir_to_qasm():
    """Test end-to-end conversion of a Bell pair QIR program to QASM."""

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
        exporter = Exporter()
        qasm_output = exporter.dumps(module)

        # Validate the complete output
        assert qasm_output.strip() == textwrap.dedent(expected_qasm).strip()


def test_bell_pyqir_to_qasm():
    """Test end-to-end conversion of a Bell pair pyqir program to QASM."""
    bell = pyqir.SimpleModule("bell", num_qubits=2, num_results=2)
    qis = pyqir.BasicQisBuilder(bell.builder)

    # Add instructions to the module to create a Bell pair and measure both qubits.
    qis.h(bell.qubits[0])
    qis.cx(bell.qubits[0], bell.qubits[1])
    qis.mz(bell.qubits[0], bell.results[0])
    qis.mz(bell.qubits[1], bell.results[1])
    qir_content = bell.ir()

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

    with tempfile.TemporaryDirectory() as tmp_dir:
        qir_path = Path(tmp_dir) / "bell.ll"
        qir_path.write_text(textwrap.dedent(qir_content), encoding="utf-8")

        # Load the QIR module
        module = load(str(qir_path))

        # Convert to QASM using the Exporter
        exporter = Exporter()
        qasm_output = exporter.dumps(module)

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
    qir_content = mod.ir()

    # Expected QASM output
    expected_qasm = """
        OPENQASM 3.0;
        array[int[32], 3] IntType_tmp;
        input int[32] IntType_i0;
        input int[32] IntType_i1;
        output int[32] IntType_o0;
        output int[32] IntType_o1;
        IntType_tmp[0] = 3 + IntType_i0;
        IntType_tmp[1] = 2 * IntType_tmp[0];
        IntType_tmp[2] = 0 - IntType_i1;
        IntType_o0 = IntType_tmp[1];
        IntType_o1 = IntType_tmp[2];
    """

    with tempfile.TemporaryDirectory() as tmp_dir:
        qir_path = Path(tmp_dir) / "arithmetic.ll"
        qir_path.write_text(textwrap.dedent(qir_content), encoding="utf-8")

        # Load the QIR module
        module = load(str(qir_path))

        # Convert to QASM using the Exporter
        exporter = Exporter()
        qasm_output = exporter.dumps(module)

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

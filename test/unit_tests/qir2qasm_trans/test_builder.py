import os
import re
import textwrap

import pytest
from autoqasm.qir2qasm_trans.qir_trans import load
from autoqasm.qir2qasm_trans.qir_trans.builder import (
    DeclBuilder,
    FunctionBuilder,
    InstructionBuilder,
    SymbolTable,
)
from autoqasm.qir2qasm_trans.qir_trans.translator import Exporter


def test_mresetz_qir_to_qasm():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "mresetz"
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


def test_FunctionBuilder_building():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "mresetz"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")

    # Load and convert
    mod = load(qir_file_path)

    for func in mod.functions:
        # check main function definition
        attr_dict = {}
        for attr in func.attributes:
            matches = re.findall(r'"(\w+)"(?:="([^"]*)")?', attr.decode())
            for k, v in matches:
                if v != "":
                    attr_dict[k] = v
                else:
                    attr_dict[k] = True

        if "entry_point" in attr_dict.keys():
            # if not func.is_declaration:
            main = func
            symbols = SymbolTable()
            func_builder = FunctionBuilder()
            inst_builder = InstructionBuilder()
            decl_builder = DeclBuilder()
            for block in main.blocks:
                for inst in block.instructions:
                    func_builder.building(symbols, inst.type, list(inst.operands))
                    inst_builder.building()
                    decl_builder.building("Qubit", 10)


def test_builder_array_error():  
    file_path = "test/resources/qir_test_file"
    benchmark_name = "builder_array_error"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")

    # Load and convert
    module = load(str(qir_file_path))

    # Convert to QASM using the Exporter
    exporter = Exporter()
    with pytest.raises(Exception, match=r"vector Undefined!"):
        exporter.dumps(module)


def test_builder_ptr2ptr_error():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "builder_ptr2ptr_error"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")

    # Load and convert
    module = load(str(qir_file_path))

    # Convert to QASM using the Exporter
    exporter = Exporter()
    with pytest.raises(Exception, match=r"Unsupported ptr to ptr!"):
        exporter.dumps(module)


def test_builder_instruction_error():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "builder_instruction_error"
    qir_file_path = os.path.join(file_path, f"{benchmark_name}.ll")

    # Load and convert
    module = load(str(qir_file_path))

    # Convert to QASM using the Exporter
    exporter = Exporter()
    with pytest.raises(Exception, match=r"Undefined llvm insturction!"):
        exporter.dumps(module)


def test_builder_defcal():
    file_path = "test/resources/qir_test_file"
    benchmark_name = "builder_defcal"
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

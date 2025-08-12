import os
import re
import tempfile
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

    # Create a temporary QIR file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=True) as temp_file:
        temp_file.write(textwrap.dedent(qir_content))
        temp_file.flush()  # Ensure content is written to disk

        # Load the QIR module
        mod = load(temp_file.name)
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
    # Sample QIR content for a Bell pair circuit
    qir_content = """
        ; ModuleID = 'test'
        source_filename = "test"

        %Qubit = type opaque
        %Result = type opaque

        @v1 = constant <8 x i32> <i32 1, i32 2, i32 3, i32 4, i32 5, i32 6, i32 7, i32 8>

        declare <8 x i32> @add_int_vectors(<8 x i32>) 

        define void @main() #0 {
        entry:
        %p1 = load <8 x i32>, <8 x i32>* @v1
        %res = call <8 x i32> @add_int_vectors(<8 x i32> %p1)
        ret void
        }

        attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="0" }
        attributes #1 = { "irreversible" }

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
        with pytest.raises(Exception, match=r"vector Undefined!"):
            exporter.dumps(module)
    # File automatically deleted here


def test_builder_ptr2ptr_error():
    # Sample QIR content for a Bell pair circuit
    qir_content = """
        ; ModuleID = 'ptr_to_ptr_example'
        source_filename = "ptr_to_ptr_example.ll"

        declare i32* @my_load(i32**)    

        @value = global i32 42        
        @p1 = global i32* @value      

        define void @main() #0 {
        entry:
        %ptr = call i32* @my_load(i32** @p1)    
        ret void
        }

        attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="0" }
        attributes #1 = { "irreversible" }

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
        with pytest.raises(Exception, match=r"Unsupported ptr to ptr!"):
            exporter.dumps(module)
    # File automatically deleted here


def test_builder_instruction_error():
    # Sample QIR content for a Bell pair circuit
    qir_content = """
        ; ModuleID = 'instruction_error'
        source_filename = "instruction_error.ll"

        @str_r1 = internal constant [3 x i8] c"r1\\00"

        declare void @my__result_record_output(i8*)

        define void @main() #0 {
        entry:
        call void @my__result_record_output(i8* getelementptr inbounds ([3 x i8], [3 x i8]* @str_r1, i32 0, i32 0))
        ret void
        }

        attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="0" }

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
        with pytest.raises(Exception, match=r"Undefined llvm insturction!"):
            exporter.dumps(module)
    # File automatically deleted here


def test_builder_defcal():
    # Sample QIR content for a Bell pair circuit
    qir_content = """
        ; ModuleID = 'instruction_error'
        source_filename = "instruction_error.ll"

        %Result = type opaque

        declare void @my_test(%Result*)

        define void @main() #0 {
        entry:
        call void @my_test(%Result* null)
        ret void
        }

        attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="0" }

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
        bit[1] Results;
        defcal my_test(bit)  -> bit {}
        Results[0] = my_test(Results[0]);
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

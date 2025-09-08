# Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import io
import re
from typing import List, Optional, Sequence, Tuple, Type

import networkx as nx
from llvmlite.binding.module import ModuleRef, ValueRef
from openqasm3 import ast
from openqasm3.printer import Printer, QASMVisitor

from .builder import (
    BinaryExpressionBuilder,
    BranchInfo,
    ClassicalDeclarationBuilder,
    DeclBuilder,
    DefCalBuilder,
    FunctionInfo,
    SymbolTable,
)
from .cfg_pattern import IfPattern1, SeqPattern
from .qir_profile import BaseProfile, Profile

# Reserved OpenQASM 3 keywords that must not be used as identifiers.
_RESERVED_KEYWORDS = frozenset(
    {
        "OPENQASM",
        "angle",
        "array",
        "barrier",
        "bit",
        "bool",
        "box",
        "break",
        "cal",
        "complex",
        "const",
        "continue",
        "creg",
        "ctrl",
        "def",
        "defcal",
        "defcalgrammar",
        "delay",
        "duration",
        "durationof",
        "else",
        "end",
        "extern",
        "float",
        "for",
        "gate",
        "gphase",
        "if",
        "in",
        "include",
        "input",
        "int",
        "inv",
        "let",
        "measure",
        "mutable",
        "negctrl",
        "output",
        "pow",
        "qreg",
        "qubit",
        "reset",
        "return",
        "sizeof",
        "stretch",
        "uint",
        "while",
    }
)

# Mapping from LLVM arithmetic opcodes to classical expression builders.
_LLVM_INSTRUCTIONS = {
    "add": BinaryExpressionBuilder("+"),
    "sub": BinaryExpressionBuilder("-"),
    "mul": BinaryExpressionBuilder("*"),
}


class Exporter:
    """QASM3 exporter main class."""

    def __init__(
        self,
        includes: Sequence[str] = (),
        profile: Profile = BaseProfile(),
        printer_class: Type[QASMVisitor] = Printer,
    ):
        """Configure exporter components.

        Args:
            includes (Sequence[str]): Standard gate library. Example: ["stdgates.inc"] to expose 
                standard gate declarations.
            profile (Profile): Target QIR profile for translation.
            printer_class (Type[QASMVisitor]): Visitor class that prints an AST to a QASM stream.
        """
        self.includes = list(includes) 
        self.profile = profile
        self.printer_class = printer_class

    def dumps(self, module):
        """Convert the module to OpenQASM 3, returning the program as a string.

        Args:
            module (ModuleRef): Source QIR module to export.

        Returns:
            str: OpenQASM 3 program text.
        """
        with io.StringIO() as stream:
            self.dump(module, stream)
            return stream.getvalue()

    def dump(self, module, stream):
        """Convert the module to OpenQASM 3 and write to a file-like stream.

        Args:
            module (ModuleRef): Source QIR module to export.
            stream: Text IO stream (e.g., file handle or StringIO).
        """
        builder = QASM3Builder(module, includeslist=self.includes, profile=self.profile)
        printer = self.printer_class(stream)
        printer.visit(builder.build_program())


class QASM3Builder:
    """QASM3 builder constructs an AST from a Module."""

    def __init__(self, module: ModuleRef, includeslist: List[str], profile: Profile):
        """Initialize builder state and symbol table.

        Args:
            module (ModuleRef): Source QIR module to translate.
            includeslist (List[str]): Target QIR profile for translation.
            profile (Profile): Profile containing lowering rules and type mappings.
        """
        self.module = module
        self.symbols = SymbolTable()
        self.includes = includeslist
        self.profile = profile

    def build_program(self) -> ast.Program:
        """Assemble the full OpenQASM 3 program AST.

        Returns:
            ast.Program: Top-level program node including version and statements.
        """
        include_statements = []
        for filename in self.includes:
            include_statements.append(ast.Include(filename))

        func_decl_statements = self.build_func_declarations()
        main_statements = self.build_main()
        var_decl_statements = self.build_var_declarations()

        statements = (
            include_statements + var_decl_statements + func_decl_statements + main_statements
        )
        return ast.Program(version="3.0", statements=statements)

    def build_var_declarations(self) -> List[ast.Statement]:
        """Emit declarations for structures, temporaries, and I/O identifiers.

        Returns:
            List[ast.Statement]: Declarations of OpenQASM variables.
        """
        building_tasks: List[Tuple[DeclBuilder, str, int]] = []

        # Structures → declare arrays for values and temporaries.
        for name, struct_info in self.symbols.structs.items():
            builder = struct_info.decl_builder
            building_tasks.append((builder, f"{name}s", self.symbols.structs_num[name]))
            building_tasks.append((builder, f"{name}s_tmp", self.symbols.structs_tmp_num[name]))

        # Classical temporaries → declare arrays like `<TypeName>_tmp[n]`.
        for name, type_ast in self.symbols.classical_tmp.items():
            builder = ClassicalDeclarationBuilder(type_ast)
            building_tasks.append((builder, f"{name}_tmp", self.symbols.classical_tmp_num[name]))

        # Materialize structure/classical temp declarations.
        statements: List[ast.Statement] = []
        for builder, name, size in building_tasks:
            if size > 0:    # Skip empty arrays
                statements.append(builder.building(name, size))

        # I/O declarations (`input` / `output`).
        for io_key in ["input", "output"]:
            for type_ast, ident_ast in self.symbols.io_variables[io_key]:
                statements.append(
                    ast.IODeclaration(
                        io_identifier=ast.IOKeyword[io_key], type=type_ast, identifier=ident_ast
                    )
                )

        return statements

    def build_func_declarations(self) -> List[ast.Statement]:
        """Register known functions and lower unknown declarations into `defcal`.

        Returns:
            List[ast.Statement]: Gate definitions and calibration definitions.
        """
        module = self.module

        declaration_statements: List[ast.CalibrationDefinition] = []
        definition_statements: List[ast.QuantumGateDefinition] = []

        # Register profile-provided structures and classical instruction lowering strategies.
        for name, struct_info in self.profile.structs.items():
            self.symbols.register_struct(name, struct_info)
        for name, inst_info in self.profile.classical_instruction.items():
            self.symbols.instructions[name] = inst_info

        # Iterate over the function declarations.
        for func in module.functions:
            if not func.is_declaration:
                continue

            func_info = self.profile.standard_functions.get(func.name)
            if func_info:
                # Known function: record function info and collect definition if present.
                self.symbols.functions[func.name] = func_info
                def_statement = func_info.def_statement
                if def_statement:
                    definition_statements.append(def_statement)
            else:
                # Unknown function: synthesize an empty-body `defcal` signature.
                func_name = func.name
                func_type = func.type.element_type

                # Build the `CalibrationDefinition` AST node in OpenQASM3
                arguments = []
                qubits = []
                num_qubits = 0

                arg_types = [arg_type for arg_type in func_type.elements]

                # Process the return type for the "CalibrationDefinition" AST node
                ret_type = arg_types[0]
                _, ret_type_ast = self.symbols.type_qir2qasm(ret_type)
                if isinstance(ret_type_ast, str):
                    ret_type_ast = self.symbols.structs[ret_type_ast].type_ast
                if ret_type_ast == "Qubit":
                    # In QIR, a function may allocate and return a new qubit.
                    # In OpenQASM, qubit allocation via operations is not allowed.
                    # All qubits must be declared at the beginning of the program.

                    # In the translation, we assume the returned qubit is already declared,
                    # and calling this allocation function is treated as applying
                    # a virtual calibration gate to that qubit.

                    # Transform: Qubit* func(...)  =>  void func(..., Qubit)
                    qubits.append(ast.Identifier(name="q_ret"))
                    ret_type_ast = None

                # Process the arguments for the "CalibrationDefinition" AST node
                for op_type in arg_types[1:]:
                    op_type_str, op_type_ast = self.symbols.type_qir2qasm(op_type)
                    if isinstance(op_type_ast, str):
                        op_type_ast = self.symbols.structs[op_type_ast].type_ast
                    if op_type_ast == "Qubit":
                        num_qubits += 1
                    else:
                        arguments.append(op_type_ast)

                    if (op_type_str == "pointer") and isinstance(op_type_ast, ast.ClassicalType):
                        if ret_type_ast is None:
                            # Transform: void func(typeA* *a, ...) => a = typeA func(type_A a, ...)
                            ret_type_ast = op_type_ast
                        else:
                            raise Exception("Too much return value!")

                # Process the qubits for the "CalibrationDefinition" AST node
                if num_qubits == 1:
                    qubits.append(ast.Identifier(name="q"))
                else:
                    for k in range(num_qubits):
                        qubits.append(ast.Identifier(name=f"q{k}"))

                # Register the new function defined by "defcal" in symbol table
                func_info = FunctionInfo(
                    type=func_type.as_ir(self.profile.context),
                    def_statement=None,
                    builder=DefCalBuilder(func_name),
                )
                self.symbols.functions[func.name] = func_info

                # # Use subroutine for the opague function
                # declaration = ast.SubroutineDefinition(
                #     name=ast.Identifier(name=func_name),
                #     arguments=arguments + qubits,
                #     body=[],
                #     return_type=ret_type_ast
                # )   

                # Use gate Calibration for the opague function
                declaration = ast.CalibrationDefinition(
                    name=ast.Identifier(name=func_name),
                    arguments=arguments,
                    qubits=qubits,
                    return_type=ret_type_ast,
                    body="",
                )   

                declaration_statements.append(declaration)

        return declaration_statements + definition_statements

    def build_main(self) -> List[ast.Statement]:
        """Translate the `entry_point` function body into OpenQASM statements.

        Returns:
            List[ast.Statement]: OpenQASM Statements.
        """
        main_func = None
        for func in self.module.functions:
            # Collect function attributes into a dictionary.
            attr_dict = {}
            for attr in func.attributes:
                matches = re.findall(r'"(\w+)"(?:="([^"]*)")?', attr.decode())
                for k, v in matches:
                    if v != "":
                        attr_dict[k] = v
                    else:
                        attr_dict[k] = True

            if "entry_point" in attr_dict.keys():
                main_func = func
                break
        else:
            raise Exception("No main function defined!")

        # Track entry block name for control-flow assembly.
        self.entry_block = list(main_func.blocks)[0].name

        # Trabslate each basic block in order.
        for idx, block in enumerate(main_func.blocks):
            self.build_block(block)
            # statements.extend(self.build_block(block))

        # TODO: Assemble control flow
        self.build_control()
        assert self.symbols.cfg.number_of_nodes() == 1
        return self.symbols.block_statements[self.entry_block]

    def build_block(self, block: ValueRef) -> List[ast.Statement]:
        """Translate a basic block into a list of QASM statements.

        Args:
            block (ValueRef): LLVM basic block.
        
        Returns:
            List[ast.Statement]: OpenQASM Statements.
        """
        statements = []
        block_name = block.name
        for inst in block.instructions:
            inst_statements, br_info = self.build_instruction(inst)
            statements.extend(inst_statements)
        assert br_info is not None
        self.symbols.block_branchs[block_name] = br_info
        self.symbols.block_statements[block_name] = statements
        return statements

    def build_control(self):
        """Construct control-flow artifacts.
        # TODO: Currently builds a CFG only
        """
        # Create a directed CFG from collected branch information.
        cfg = nx.DiGraph()
        for block, block_info in self.symbols.block_branchs.items():
            cfg.add_node(block)
        for block, block_info in self.symbols.block_branchs.items():
            for tgt_block in block_info.branch_targets:
                cfg.add_edge(block, tgt_block)
        self.symbols.cfg = cfg

        is_updated = True
        while is_updated:
            is_updated = SeqPattern().building(self.symbols)
            is_updated = is_updated or IfPattern1().building(self.symbols)

    def build_instruction(self, instruction: ValueRef) -> Tuple[List[ast.Statement], Optional[BranchInfo]]:
        """Translate a single LLVM instruction.

        Args:
            instruction (ValueRef): LLVM instruction.
            block_name (str): Name of the containing basic block.

        Returns:
            List[ast.Statement]: Emitted statements
        """
        statements: List[ast.Statement] = []
        br_info: Optional[BranchInfo] = None

        if instruction.opcode in _LLVM_INSTRUCTIONS.keys():
            statements.extend(self.build_llvm_inst(instruction))
        elif instruction.opcode == "call":
            statements.extend(self.build_func_call(instruction))
        elif instruction.opcode == "br":
            br_info = self.build_branch(instruction)
        elif instruction.opcode == "ret":
            br_info = BranchInfo(None, [])
        else:
            raise Exception(f"Undefined llvm instruction: {instruction.opcode}")

        return statements, br_info

    def build_func_call(self, inst: ValueRef) -> List[ast.Statement]:
        """Translate a QIR `call` instruction into OpenQASM statements.

        Args:
            inst (ValueRef): LLVM call instruction.

        Returns:
            List[ast.Statement]: Emitted statements implementing the call.
        """
        operands = list(inst.operands)
        func = operands.pop(-1) # Callee is last in llvmlite's operand list.
        func_name = func.name

        # Lookup builder for the callee.
        func_info = self.symbols.functions[func_name]
        func_builder = func_info.builder
        ret_type = inst.type

        # Type check: ensure the callee's type matches the registered signature.
        assert func.type.element_type.as_ir(self.profile.context) == func_info.type

        # Delegate to the builder to produce statements and result identifier.
        ret_ident, statements = func_builder.building(self.symbols, ret_type, operands)
        if ret_ident:
            self.symbols.record_variables(inst, ret_ident)
        return statements

    def build_llvm_inst(self, inst: ValueRef) -> List[ast.Statement]:
        """Translate a supported LLVM arithmetic instruction to QASM statements.

        Args:
            inst (ValueRef): LLVM instruction (e.g., `add`, `sub`, `mul`).

        Returns:
            List[ast.Statement]: Emitted statements and records the SSA result.
        """
        operands = list(inst.operands)
        func_builder = _LLVM_INSTRUCTIONS[inst.opcode]
        ret_type = inst.type
        ret_ident, statements = func_builder.building(self.symbols, ret_type, operands)
        # if ret_ident:
        #     self.symbols.record_variables(inst, ret_ident)
        self.symbols.record_variables(inst, ret_ident)
        return statements

    def build_branch(self, inst: ValueRef) -> BranchInfo:
        """Extract branch information (targets and optional condition).

        Args:
            inst (ValueRef): LLVM `br` instruction (conditional or unconditional).

        Returns:
            BranchInfo: Condition expression (if any) and target block names.
        """
        operands = list(inst.operands)
        len_op = len(operands)
        if len_op == 1:
            # Unconditional branch: br label %target
            br_info = BranchInfo(None, [operands[0].name])
        else:
            # Conditional branch: br i1 %cond, label %true, label %false
            # llvmlite load operands as (%cond, %false, %true)
            assert len_op == 3
            br_info = BranchInfo(
                self.symbols.value_qir2qasm(operands[0]), [operands[2].name, operands[1].name]
            )
        return br_info

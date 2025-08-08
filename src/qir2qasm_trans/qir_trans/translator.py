import io
import re
from typing import List, Sequence, Tuple

# from pyqir import Module, FunctionType, PointerType, StructType, Type
import networkx as nx
from llvmlite.binding.module import ModuleRef, ValueRef
from openqasm3 import ast
from openqasm3.printer import Printer

from .builder import (
    BranchInfo,
    ClassicalDeclarationBuilder,
    DeclBuilder,
    DefCalBuilder,
    FunctionInfo,
    SymbolTable,
)
from .qir_profile import BaseProfile, Profile
from .builder import BinaryExpressionBuilder

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

_LLVM_INSTRUCTIONS = {
    "add": BinaryExpressionBuilder("+"),
    "sub": BinaryExpressionBuilder("-"),
    "mul": BinaryExpressionBuilder("*"),
}

class Exporter:
    """QASM3 exporter main class."""

    def __init__(
        self, includes: Sequence[str] = ("stdgates.inc",), profile: Profile = BaseProfile()
    ):
        self.includes = list(includes)
        self.profile = profile

    def dumps(self, module):
        """Convert the module to OpenQASM 3, returning the result as a string."""
        with io.StringIO() as stream:
            self.dump(module, stream)
            return stream.getvalue()

    def dump(self, module, stream):
        """Convert the module to OpenQASM 3, dumping the result to a file or text stream."""
        builder = QASM3Builder(module, includeslist=self.includes, profile=self.profile)
        Printer(stream).visit(builder.build_program())


class QASM3Builder:
    """QASM3 builder constructs an AST from a Module."""

    def __init__(self, module: ModuleRef, includeslist, profile: Profile):
        self.module = module
        self.symbols = SymbolTable()
        self.includes = includeslist
        self.profile = profile

    def build_program(self) -> ast.Program:
        """Builds a Program"""
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
        building_task: List[Tuple[DeclBuilder, str, int]] = []
        for name, struct_info in self.symbols.structures.items():
            builder = struct_info.decl_builder
            building_task.append((builder, f"{name}s", self.symbols.structures_num[name]))
            building_task.append((builder, f"{name}s_tmp", self.symbols.structures_tmp_num[name]))

        for name, type_ast in self.symbols.classical_tmp.items():
            builder = ClassicalDeclarationBuilder(type_ast)
            building_task.append((builder, f"{name}_tmp", self.symbols.classical_tmp_num[name]))

        statements = []
        for builder, name, size in building_task:
            if size > 0:
                statements.append(builder.building(name, size))
        
        for io_key in ["input", "output"]:
            for type_ast, ident_ast in self.symbols.io_variables[io_key]:
                statements.append(
                    ast.IODeclaration(
                        io_identifier = ast.IOKeyword[io_key],
                        type = type_ast,
                        identifier = ident_ast
                    )
                )

        return statements

    def build_func_declarations(self) -> List[ast.Statement]:
        module = self.module

        statements_declaration = []
        statements_definition = []

        for name, struct_info in self.profile.structures.items():
            self.symbols.register_structure(name, struct_info)  # Register Structure in SymbolTable

        for name, inst_info in self.profile.classical_instruction.items():
            self.symbols.instructions[name] = inst_info  # Register Instruction in SymbolTable

        for func in module.functions:
            if func.is_declaration:
                func_info = self.profile.standard_functions.get(func.name)

                if func_info:
                    # If func is defined in QIR Profile
                    self.symbols.functions[func.name] = (
                        func_info  # Register Function in SymbolTable
                    )
                    def_statement = func_info.def_statement
                    if def_statement:
                        statements_definition.append(def_statement)
                else:
                    # If func is not defined in QIR Profile
                    func_name = func.name
                    func_type = func.type.element_type

                    # Build the "defcal" QASM ast node
                    arguments = []
                    qubits = []
                    num_qubits = 0

                    arg_types = [arg_type for arg_type in func_type.elements]

                    # Return Type
                    ret_type = arg_types[0]
                    _, ret_type_ast = self.symbols.type_qir2qasm(ret_type)
                    if isinstance(ret_type_ast, str):
                        ret_type_ast = self.symbols.structures[ret_type_ast].type_ast
                    if ret_type_ast == "Qubit":
                        # Qubit* func(...) => void func (..) Qubit
                        qubits.append(ast.Identifier(name="q_ret"))
                        ret_type_ast = None

                    # Argument Type
                    for op_type in arg_types[1:]:
                        op_type_str, op_type_ast = self.symbols.type_qir2qasm(op_type)
                        if isinstance(op_type_ast, str):
                            op_type_ast = self.symbols.structures[op_type_ast].type_ast
                        if op_type_ast == "Qubit":
                            num_qubits += 1
                        else:
                            arguments.append(op_type_ast)

                        if (op_type_str == "pointer") and isinstance(
                            op_type_ast, ast.ClassicalType
                        ):
                            if ret_type_ast is None:
                                # void func(typeA*, ...) => typeA func(type_A, ...)
                                ret_type_ast = op_type_ast
                            else:
                                raise Exception("Too much return value!")

                    if num_qubits == 1:
                        qubits.append(ast.Identifier(name="q"))
                    else:
                        for k in range(num_qubits):
                            qubits.append(ast.Identifier(name=f"q{k}"))

                    ident = ast.Identifier(name=func_name)
                    func_builder = DefCalBuilder(func_name)
                    func_info = FunctionInfo(
                        type=func_type.as_ir(self.profile.context),
                        def_statement=None,
                        builder=func_builder,
                    )
                    self.symbols.functions[func.name] = (
                        func_info  # Register Function in SymbolTable
                    )

                    statements_declaration.append(
                        ast.CalibrationDefinition(
                            name=ident,
                            arguments=arguments,
                            qubits=qubits,
                            return_type=ret_type_ast,
                            body="",
                        )
                    )

        return statements_declaration + statements_definition

    def build_main(self) -> List[ast.Statement]:
        main_func = None
        for func in self.module.functions:
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
                main_func = func
                break
        else:
            raise Exception("No main function defined!")

        statements = []
        self.entry_block = main_func.name
        for block in main_func.blocks:
            # self.build_block(block)
            statements.extend(self.build_block(block))

        self.build_control()
        return statements

    def build_block(self, block: ValueRef) -> List[ast.Statement]:
        statements = []
        block_name = block.name
        for inst in block.instructions:
            statements.extend(self.build_instruction(inst, block_name))
        self.symbols.block_statements[block_name] = statements
        return statements

    def build_control(self):
        is_updated = True
        while is_updated:
            cfg = self.create_CFG()
            is_updated = False

    def create_CFG(self) -> nx.DiGraph:
        cfg = nx.DiGraph()
        for block, block_info in self.symbols.block_branchs.items():
            for tgt_block in block_info.br_tgt:
                cfg.add_edge(block, tgt_block)
        return cfg

    def build_instruction(self, instruction: ValueRef, block_name: str):
        statements = []
        if instruction.opcode in _LLVM_INSTRUCTIONS.keys():
            statements.extend(self.build_llvm_inst(instruction))
        elif instruction.opcode == "call":
            statements.extend(self.build_func_call(instruction))
        elif instruction.opcode == "br":
            self.symbols.block_branchs[block_name] = self.build_branch(instruction)
        elif instruction.opcode == "ret":
            self.symbols.block_branchs[block_name] = BranchInfo(None, [])
        else:
            raise Exception(f"Undefined llvm instruction: {instruction.opcode}")
        return statements

    def build_func_call(self, inst: ValueRef) -> List[ast.Statement]:
        operands = list(inst.operands)
        func = operands.pop(-1)
        func_name = func.name
        func_info = self.symbols.functions[func_name]
        func_builder = func_info.builder
        ret_type = inst.type
        # print(func_type.as_ir(self.profile.context), '==', func_info.type)
        assert func.type.element_type.as_ir(self.profile.context) == func_info.type
        ret_ident, statements = func_builder.building(self.symbols, ret_type, operands)
        if ret_ident:
            self.symbols.record_variables(inst, ret_ident)
        return statements
    
    def build_llvm_inst(self, inst: ValueRef) -> List[ast.Statement]:
        operands = list(inst.operands)
        func_builder = _LLVM_INSTRUCTIONS[inst.opcode]
        ret_type = inst.type
        ret_ident, statements = func_builder.building(self.symbols, ret_type, operands)
        # if ret_ident:
        #     self.symbols.record_variables(inst, ret_ident)
        self.symbols.record_variables(inst, ret_ident)
        return statements

    def build_branch(self, inst: ValueRef) -> BranchInfo:
        operands = list(inst.operands)
        l = len(operands)
        if l == 1:
            br_info = BranchInfo(None, [operands[0].name])
        elif l == 3:
            br_info = BranchInfo(
                self.symbols.value_qir2qasm(operands[0]), [operands[1].name, operands[2].name]
            )
        else:
            raise Exception
        return br_info

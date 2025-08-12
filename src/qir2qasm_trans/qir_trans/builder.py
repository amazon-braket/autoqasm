import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

from llvmlite.binding.module import ValueRef
from llvmlite.binding.typeref import TypeRef
from llvmlite.ir import FunctionType, IdentifiedStructType
from openqasm3 import ast


class FunctionBuilder:
    def building(
        self,
        symbols, 
        ret_type: TypeRef,
        operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        return None, []


@dataclass
class FunctionInfo:
    type: FunctionType
    def_statement: Optional[ast.QuantumGateDefinition]
    builder: FunctionBuilder


class InstructionBuilder:
    def building(
        self,
        **kwargs,
    ) -> Optional[ast.IndexedIdentifier]:
        return None


@dataclass
class InstructionInfo:
    builder: InstructionBuilder


class DeclBuilder:
    def building(self, name: str, size: int) -> ast.Statement:
        return None


@dataclass
class StructureInfo:
    type_qir: IdentifiedStructType
    type_ast: Union[ast.ClassicalType, str]
    decl_builder: DeclBuilder
    # call_builder


@dataclass
class BranchInfo:
    br_condition: Optional[ast.Expression]
    br_tgt: List[str]


class SymbolTable:
    def __init__(self):
        self.structures: OrderedDict[str, StructureInfo] = {}
        self.instructions: OrderedDict[str, InstructionInfo] = {}
        self.functions: OrderedDict[str, FunctionInfo] = {}
        self.variables: OrderedDict[str, Union[ast.IndexedIdentifier, ast.Identifier]] = {}
        self.io_variables: OrderedDict[str, List[Tuple[ast.ClassicalType, ast.Identifier]]] = {"input": [], "output": []}

        self.structures_num: OrderedDict[str, int] = {}
        self.structures_tmp_num: OrderedDict[str, int] = {}
        self.classical_tmp: OrderedDict[str, ast.ClassicalType] = {}
        self.classical_tmp_num: OrderedDict[str, int] = {}
        
        self.entry_block: str = None
        self.block_statements: OrderedDict[str, List[ast.Statement]] = {}
        self.block_branchs: OrderedDict[str, BranchInfo] = {}

    def register_structure(self, name: str, info: StructureInfo):
        self.structures[name] = info
        self.structures_num[name] = 0
        self.structures_tmp_num[name] = 0

    def record_variables(self, inst: ValueRef, ident: Union[ast.IndexedIdentifier, ast.Identifier]):
        self.variables[str(inst)] = ident

    def get_variables(
        self, inst_str: str
    ) -> Optional[Union[ast.IndexedIdentifier, ast.Identifier]]:
        return self.variables.get(inst_str)

    def type_qir2qasm(self, tp: TypeRef):
        type_kind = tp.type_kind
        type_str = type_kind.name

        _FLOAT_BIT_WIDTHS = {
            "half": 16,
            "float": 32,
            "double": 64,
            "x86_fp80": 80,
            "fp128": 128,
            "ppc_fp128": 128,
        }

        if type_str == "void":
            type_ast = None
        elif type_str in _FLOAT_BIT_WIDTHS.keys():
            width = _FLOAT_BIT_WIDTHS[type_str]
            type_ast = ast.FloatType(size=ast.IntegerLiteral(value=width))
        elif type_str == "integer":
            if tp.type_width == 1:
                type_ast = ast.BoolType()
            else:
                type_ast = ast.IntType(size=ast.IntegerLiteral(value=tp.type_width))
        elif type_str == "struct":
            type_ast = tp.name
            # struct_name = tp.name
            # type_ast = self.structures.get(struct_name).type_ast
            # if type_ast is None:
            #     raise Exception(f"Unsupported struct")
        # elif type_str == "array":
        #     pass # TODO
        elif type_str == "pointer":
            type_qasm = self.type_qir2qasm(tp.element_type)
            if type_qasm[0] != "pointer":
                type_ast = type_qasm[1]
            else:
                raise Exception("Unsupported ptr to ptr!")
        # elif type_str == "vector":
        #     pass # TODO
        else:
            raise Exception(f"{type_str} Undefined!")
        return type_str, type_ast

    def value_qir2qasm(self, value_qir: ValueRef) -> Union[ast.IndexedIdentifier, ast.Expression]:
        if value_qir.is_constant:
            value = value_qir.get_constant_value()
            value_ast = None

            if isinstance(value, int):
                value_ast = ast.IntegerLiteral(value)
            elif isinstance(value, float):
                value_ast = ast.FloatLiteral(value)
            else:
                assert isinstance(value, str)
                for inst_builder_info in self.instructions.values():
                    inst_builder = inst_builder_info.builder
                    value_ast = inst_builder.building(self, value_qir)
                    if value_ast:
                        break
                else:
                    raise Exception("Undefined llvm insturction!")
            # else:
            #     raise Exception(f"{value} Undefined!")
        else:
            value_ast = self.get_variables(str(value_qir))
        return value_ast

    def alloc_tmp_var(self, type_ast: Union[ast.ClassicalType, str]) -> ast.IndexedIdentifier:
        if isinstance(type_ast, str):
            # Structure
            name = type_ast
            idx = self.structures_tmp_num[
                name
            ]  # Structure should be in symbol table due to declaration of structure
            self.structures_tmp_num[name] += 1
            var_ast = ast.IndexedIdentifier(
                name=ast.Identifier(name=f"{name}_tmp"), indices=[[ast.IntegerLiteral(value=idx)]]
            )
        else:
            assert isinstance(type_ast, ast.ClassicalType)
            name = type_ast.__class__.__name__
            idx = self.classical_tmp_num.get(name)
            if idx is None:
                idx = 0
                self.classical_tmp_num[name] = 1
                self.classical_tmp[name] = type_ast
            else:
                self.classical_tmp_num[name] += 1
            var_ast = ast.IndexedIdentifier(
                name=ast.Identifier(name=f"{name}_tmp"), indices=[[ast.IntegerLiteral(value=idx)]]
            )
        return var_ast
    
    def alloc_io_var(self, type_ast: ast.ClassicalType, io_key: str) -> ast.Identifier:
        name = type_ast.__class__.__name__
        idx = len(self.io_variables[io_key])
        ident_name = f"{name}_{io_key[0]}{idx}"
        var_ast = ast.Identifier(name=ident_name)
        self.io_variables[io_key].append((type_ast, var_ast))
        return var_ast

    # def alloc_tmp_structure(self, name) -> ast.IndexedIdentifier:
    #     idx = self.structures_tmp_num[name]
    #     self.structures_tmp_num[name] += 1
    #     return ast.IndexedIdentifier(name=ast.Identifier(name=f"{name}_tmp"), indices=[[ast.IntegerLiteral(value=idx)]])

    # def alloc_tmp_classical(self, ret_type: TypeRef) -> ast.IndexedIdentifier:
    #     _, type_ast = self.type_qir2qasm(ret_type)
    #     assert isinstance(type_ast, ast.ClassicalType)

    #     type_name = type_ast.__class__.__name__

    #     idx = self.classical_tmp_num.get(type_name)
    #     if idx is None:
    #         idx = 0
    #         self.classical_tmp_num[type_name] = 1
    #         self.classical_tmp[type_name] = type_ast
    #     else:
    #         self.classical_tmp_num[type_name] += 1

    #     return ast.IndexedIdentifier(name=ast.Identifier(name=f"{type_name}_tmp"), indices=[[ast.IntegerLiteral(value=idx)]])


## StructureBuilder
class QubitDeclarationBuilder(DeclBuilder):
    def building(self, name: str, size: int) -> ast.Statement:
        ident = ast.Identifier(name=name)
        size_exp = ast.IntegerLiteral(value=size)
        return ast.QubitDeclaration(qubit=ident, size=size_exp)


class ResultDeclarationBuilder(DeclBuilder):
    def building(self, name: str, size: int) -> ast.Statement:
        ident = ast.Identifier(name=name)
        size_exp = ast.IntegerLiteral(value=size)
        decl_type = ast.BitType(size=size_exp)
        return ast.ClassicalDeclaration(type=decl_type, identifier=ident)


class ClassicalDeclarationBuilder(DeclBuilder):
    def __init__(self, base_type: ast.ClassicalType):
        self.base_type = base_type

    def building(self, name: str, size: int) -> ast.Statement:
        ident = ast.Identifier(name=name)
        size_exp = ast.IntegerLiteral(value=size)
        decl_type = ast.ArrayType(base_type=self.base_type, dimensions=[size_exp])
        return ast.ClassicalDeclaration(type=decl_type, identifier=ident)


## InstructionBuilder
class InttoptrBuilder(InstructionBuilder):
    def __init__(
        self,
    ):
        self.null_pattern = r"(?P<ret_type>%\w+\*)\s+null"
        self.pattern = (
            r"(?P<ret_type>%\w+\*)\s+"
            r"inttoptr\s+\(i64\s+(?P<index>\d+)\s+to\s+"
            r"(?P=ret_type)"
            r"\)"
        )

    def building(
        self,
        symbols: SymbolTable,
        op: ValueRef,
    ) -> Optional[ast.IndexedIdentifier]:
        op_type = op.type
        op_value = op.get_constant_value()
        op_name = op_type.element_type.name

        escaped_type = re.escape(str(op_type))
        m1 = re.match(self.null_pattern.format(ret_type=escaped_type), op_value.strip())
        m2 = re.match(self.pattern.format(ret_type=escaped_type), op_value.strip())
        if m1:
            idx = 0
        elif m2:
            idx = int(m2.group("index"))
        else:
            return None

        symbols.structures_num[op_name] = max(symbols.structures_num[op_name], idx + 1)

        return ast.IndexedIdentifier(
            name=ast.Identifier(name=f"{op_name}s"), indices=[[ast.IntegerLiteral(value=idx)]]
        )


# def type_qir2qasm(tp: TypeRef) -> Tuple[str, Optional[Union[ast.ClassicalType, str]]]:
#     type_kind = tp.type_kind
#     _FLOAT_BIT_WIDTHS = {
#         "half": 16,
#         "float": 32,
#         "double": 64,
#         "x86_fp80": 80,
#         "fp128": 128,
#         "ppc_fp128": 128,
#     }
#     type_str = type_kind.name
#     type_ast = None

#     if type_str == "void":
#         pass
#     elif type_str in _FLOAT_BIT_WIDTHS.keys():
#         width = _FLOAT_BIT_WIDTHS[type_str]
#         type_ast = ast.FloatType(size=ast.IntegerLiteral(value=width))
#     elif type_str == "integer":
#         if tp.type_width == 1:
#             type_ast = ast.BoolType()
#         else:
#             type_ast = ast.IntType(tp.type_width)
#     elif type_str == "struct":
#         if tp.name == "Qubit":
#             type_ast = "Qubit"
#         elif tp.name == "Result":
#             type_ast = ast.BitType()
#         else:
#             raise Exception(f"Unsupported struct")
#     elif type_str == "array":
#         pass # TODO
#     elif type_str == "pointer":
#         type_qasm = type_qir2qasm(tp.element_type)
#         if type_qasm[0] != "pointer":
#             type_ast = type_qasm[1]
#         else:
#             raise Exception(f"Unsupported ptr to ptr")
#     elif type_str == "vector":
#         pass # TODO
#     else:
#         raise Exception(f"{type_str} Undefined!")
#     return type_str, type_ast


# def get_return_type(func_type: TypeRef) -> TypeRef:
#     return [tp for tp in func_type.element_type.elements][0]


def identifier2expression(ident: Union[ast.IndexedIdentifier, ast.Identifier, ast.Expression]) -> ast.Expression:
    if isinstance(ident, ast.Identifier) or isinstance(ident, ast.Expression):
        return ident
    else:
        return ast.IndexExpression(collection=ident.name, index=ident.indices[0])


def preprocess_params(
    symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
) -> Tuple[
    Optional[Union[ast.IndexedIdentifier, ast.Identifier]],
    List[ast.Expression],
    List[Union[ast.IndexedIdentifier, ast.Identifier]],
    Optional[TypeRef],
    Optional[Union[ast.IndexedIdentifier, ast.Identifier]],
]:
    ret_ident = None
    assign_ident = None
    arguments = []
    qubits = []

    # Return Type
    ret_type_str, ret_type_ast = symbols.type_qir2qasm(ret_type)
    if ret_type_str == "void":
        ret_ident = None
    else:
        struct_name = ret_type_ast
        ret_ident = symbols.alloc_tmp_var(struct_name)
        if struct_name == "Qubit":
            # Qubit* func(...) => void func (..) Qubit
            qubits.append(ret_ident)
        else:
            assign_ident = ret_ident

    # Qubits & Arguments
    for op in operands:
        op_type_str, op_type_ast = symbols.type_qir2qasm(op.type)

        # Value
        op_ident = symbols.value_qir2qasm(op)
        if op_type_ast == "Qubit":
            qubits.append(op_ident)
        else:
            op_ident = identifier2expression(op_ident)
            arguments.append(op_ident)

            # Return & Assignment
            if (op_type_str == "pointer"):
                # if assign_ident is None:
                # void func(typeA*, ...) => typeA func(type_A, ...)
                assign_ident = symbols.value_qir2qasm(op)
                # else:
                #     raise Exception("Too much return value!")

    return ret_ident, arguments, qubits, assign_ident


class GateBuilder(FunctionBuilder):
    def __init__(self, gate: str, adjoint: bool = False):
        if adjoint:
            self.ident = ast.Identifier(name=gate + "dg")
        else:
            self.ident = ast.Identifier(name=gate)

    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        assert ret_type.type_kind.name == "void"

        arguments = []
        qubits = []
        for op in operands:
            _, type_ast = symbols.type_qir2qasm(op.type)
            op_ast = symbols.value_qir2qasm(op)
            if type_ast == "Qubit":
                qubits.append(op_ast)
            else:
                op_ast = identifier2expression(op_ast)
                arguments.append(op_ast)

        return None, [
            ast.QuantumGate(modifiers=[], name=self.ident, arguments=arguments, qubits=qubits)
        ]


class ResetBuilder(FunctionBuilder):
    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        return None, [ast.QuantumReset(qubits=symbols.value_qir2qasm(operands[0]))]


class MeasurementBuilder(FunctionBuilder):
    def __init__(self, name: str):
        self.name = name

    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        if self.name == "m":
            ret_ident = symbols.alloc_tmp_var("Result")
            tgt_ident = ret_ident
        else:
            ret_ident = None
            tgt_ident = symbols.value_qir2qasm(operands[1])

        qubit_ast = symbols.value_qir2qasm(operands[0])
        measure = ast.QuantumMeasurement(qubit=qubit_ast)
        statements = [ast.QuantumMeasurementStatement(measure=measure, target=tgt_ident)]

        if self.name == "mresetz":
            statements.append(ast.QuantumReset(qubits=qubit_ast))

        return ret_ident, statements


class DefCalBuilder(FunctionBuilder):
    def __init__(self, name: str):
        self.ident = ast.Identifier(name=name)

    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        ret_ident, arguments, qubits, assign_ident = preprocess_params(symbols, ret_type, operands)

        # expression = ast.QuantumGate(
        #     modifiers=[],
        #     name=self.ident,
        #     arguments=arguments,
        #     qubits=qubits
        # )
        expression = ast.FunctionCall(
            name=self.ident, arguments=arguments + [identifier2expression(q) for q in qubits]
        )

        # Assignment
        if assign_ident is not None:
            statement = ast.ClassicalAssignment(
                lvalue=assign_ident, op=ast.AssignmentOperator["="], rvalue=expression
            )
        else:
            statement = ast.ExpressionStatement(expression)

        return ret_ident, [statement]


class LoadBuilder(FunctionBuilder):
    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        assert len(operands) == 1
        ret_ident = symbols.value_qir2qasm(operands[0])

        return ret_ident, []


class ConstantBuilder(FunctionBuilder):
    def __init__(self, constant: ast.Expression):
        self.constant = constant

    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        _, type_ast = symbols.type_qir2qasm(ret_type)
        ret_ident = symbols.alloc_tmp_var(type_ast)

        statement = ast.ClassicalAssignment(
            lvalue=ret_ident, op=ast.AssignmentOperator["="], rvalue=self.constant
        )
        return ret_ident, [statement]


class BinaryExpressionBuilder(FunctionBuilder):
    def __init__(self, op: str):
        self.op = ast.BinaryOperator[op]

    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        _, type_ast = symbols.type_qir2qasm(ret_type)
        ret_ident = symbols.alloc_tmp_var(type_ast)

        lhs = identifier2expression(symbols.value_qir2qasm(operands[0]))
        rhs = identifier2expression(symbols.value_qir2qasm(operands[1]))
        statement = ast.ClassicalAssignment(
            lvalue=ret_ident,
            op=ast.AssignmentOperator["="],
            rvalue=ast.BinaryExpression(op=self.op, lhs=lhs, rhs=rhs),
        )

        return ret_ident, [statement]


class RecordBuilder(FunctionBuilder):
    pass


class InputBuilder(FunctionBuilder):
    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        _, type_ast = symbols.type_qir2qasm(ret_type)
        ret_ident = symbols.alloc_io_var(type_ast, "input")
        return ret_ident, []
    
    
class OutputBuilder(FunctionBuilder):
    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        _, op_type = symbols.type_qir2qasm(operands[0].type)
        op_value = identifier2expression(symbols.value_qir2qasm(operands[0]))

        assign_ident = symbols.alloc_io_var(op_type, "output")
        statement = ast.ClassicalAssignment(
            lvalue=assign_ident, op=ast.AssignmentOperator["="], rvalue=op_value
        )
        return None, [statement]
    

# Declaration Builder
def build_rotation_2Q_definition(name: str) -> ast.QuantumGateDefinition:
    ident = ast.Identifier(name=name)

    # Define the parameter θ (negated if adjoint)
    theta = ast.Identifier(name="θ")

    # Qubit identifiers
    q0 = ast.Identifier(name="q0")
    q1 = ast.Identifier(name="q1")

    # Base Rzz-like body: CX - Rz(θ) - CX
    body = [
        ast.QuantumGate(
            modifiers=[], name=ast.Identifier(name="cx"), arguments=[], qubits=[q0, q1]
        ),
        ast.QuantumGate(
            modifiers=[], name=ast.Identifier(name="rz"), arguments=[theta], qubits=[q1]
        ),
        ast.QuantumGate(
            modifiers=[], name=ast.Identifier(name="cx"), arguments=[], qubits=[q0, q1]
        ),
    ]

    # Construct π/2 and −π/2 literals
    pi_over_2 = ast.BinaryExpression(
        op="/", lhs=ast.Identifier("pi"), rhs=ast.IntegerLiteral(value=2)
    )
    neg_pi_over_2 = ast.UnaryExpression(op="-", expression=pi_over_2)

    # Gate-specific pre/post rotations
    if name == "rxx":
        before = [
            ast.QuantumGate(modifiers=[], name=ast.Identifier(name="h"), arguments=[], qubits=[q])
            for q in [q0, q1]
        ]
        after = [
            ast.QuantumGate(modifiers=[], name=ast.Identifier(name="h"), arguments=[], qubits=[q])
            for q in [q0, q1]
        ]
    elif name == "ryy":
        before = [
            ast.QuantumGate(
                modifiers=[], name=ast.Identifier(name="rx"), arguments=[pi_over_2], qubits=[q]
            )
            for q in [q0, q1]
        ]
        after = [
            ast.QuantumGate(
                modifiers=[], name=ast.Identifier(name="rx"), arguments=[neg_pi_over_2], qubits=[q]
            )
            for q in [q0, q1]
        ]
    else:
        before = []
        after = []

    # Combine and return the full definition
    return ast.QuantumGateDefinition(
        name=ident, arguments=[theta], qubits=[q0, q1], body=before + body + after
    )

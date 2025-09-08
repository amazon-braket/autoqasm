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

"""Builders for QIR → OpenQASM 3 translator"""

import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple, Union

import networkx as nx
from llvmlite.binding.module import ValueRef
from llvmlite.binding.typeref import TypeRef
from llvmlite.ir import FunctionType, IdentifiedStructType
from openqasm3 import ast


class FunctionBuilder:
    """Building interface for the QIR function-call instruction (``call ...``)

    Subclasses should override ``building``
    """

    def building(
        self, symbols, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        """Build OpenQASM statements for a single QIR ``call`` instruction

        Args:
            symbols (SymbolTable): Translation context.
            ret_type (TypeRef): Return type of the QIR instruction.
            operands (List[ValueRef]): Operands of the QIR instruction.

        Returns:
            A tuple (ret_ident, statements) where:
            - ret_ident: OpenQASM identifier for the result of the QIR instruction
                (i.e., ``%1 = call ...``).
            - statements: List of OpenQASM statements for the QIR instruction.
        """
        return None, []


@dataclass
class FunctionInfo:
    """Registry entry for a QIR function"""

    type: FunctionType  # LLVM function type
    def_statement: Optional[ast.QuantumGateDefinition]  # QASM gate definitions (i.e. Rzz gate)
    builder: FunctionBuilder  # Calling builder for the function


class InstructionBuilder:
    """Building interface for the LLVM IR instructions (i.e. ``inttoptr``)

    Subclasses should override ``building``
    """

    def building(
        self,
        **kwargs,
    ) -> Optional[ast.IndexedIdentifier]:
        return None


@dataclass
class InstructionInfo:
    """Registry entry for a LLVM IR instruction"""

    builder: InstructionBuilder


class DeclBuilder:
    """Building interface for the QIR struct declarations (i.e. ``Qubit``, ``Result``)

    Subclasses should override ``building``
    """

    def building(self, name: str, size: int) -> ast.Statement:
        return None


@dataclass
class StructInfo:
    """Registry entry for a QIR struct"""

    type_qir: IdentifiedStructType  # LLVM identified struct type
    type_ast: Union[ast.ClassicalType, str]  # Target OpenQASM AST representation
    decl_builder: DeclBuilder  # Declaration builder for the struct
    static_name: str  # Static register name for the struct


@dataclass
class BranchInfo:
    """Branch metadata for a basic block."""
    branch_condition: Optional[ast.Expression]  # Conditional expression 
    branch_targets: List[str]   # Target block labels (true/false)


class SymbolTable:
    """Holds all translation-time symbols and contextual counters."""

    def __init__(self):
        # Struct / LLVM IR / QIR function registries
        self.structs: OrderedDict[str, StructInfo] = {}
        self.instructions: OrderedDict[str, InstructionInfo] = {}
        self.functions: OrderedDict[str, FunctionInfo] = {}

        # OpenQASM identifier for the SSA value (i.e. ``%1 = ...``)
        self.variables: OrderedDict[str, Union[ast.IndexedIdentifier, ast.Identifier]] = {}

        # I/O Tags for the OpenQASM variables
        self.io_variables: OrderedDict[str, List[Tuple[ast.ClassicalType, ast.Identifier]]] = {
            "input": [],
            "output": [],
        }

        # Register naming function
        self.tmp_naming: Callable = lambda sname: f"{sname}_tmp"
        self.io_naming: Callable = lambda sname, io_key, idx: f"{sname}_{io_key[0]}{idx}"

        # Counters for sizing OpenQASM temporaries and constants (i.e. `qubit[n]`)
        self.structs_num: OrderedDict[str, int] = {}
        self.structs_tmp_num: OrderedDict[str, int] = {}
        self.classical_tmp: OrderedDict[str, ast.ClassicalType] = {}
        self.classical_tmp_num: OrderedDict[str, int] = {}

        # Control-flow scaffolding
        self.entry_block: str = None
        self.block_statements: OrderedDict[str, List[ast.Statement]] = {}
        self.block_branchs: OrderedDict[str, BranchInfo] = {}
        self.cfg: nx.DiGraph = nx.DiGraph()

    def register_struct(self, name: str, info: StructInfo):
        """Register a struct type and initialize counters."""
        self.structs[name] = info
        self.structs_num[name] = 0
        self.structs_tmp_num[name] = 0

    def record_variables(self, inst: ValueRef, ident: Union[ast.IndexedIdentifier, ast.Identifier]):
        """Record the QASM identifier produced for the SSA value of an LLVM instruction"""
        self.variables[str(inst)] = ident

    def get_variables(
        self, inst_str: str
    ) -> Optional[Union[ast.IndexedIdentifier, ast.Identifier]]:
        """Lookup the QASM identifier previously bound to the given SSA string."""
        return self.variables.get(inst_str)

    def type_qir2qasm(self, tp: TypeRef):
        """Translate a QIR (LLVM) TypeRef into a (kind_str, AST type) pair.
        Args:
            tp (TypeRef): LLVM type need to translated.

        Returns:
            (type_str, type_ast)
            - type_str: string name of the LLVM type kind (e.g., "integer", "struct", "pointer").
            - type_ast: OpenQASM AST type to use, or a struct name (str), or None for void.
        """
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
        # elif type_str == "array":
        #     TODO: Support array types if needed.
        elif type_str == "pointer":
            type_qasm = self.type_qir2qasm(tp.element_type)
            if type_qasm[0] != "pointer":
                # return the ``ast_type`` of the element
                type_ast = type_qasm[1]
            else:
                # Reject pointer-to-pointer
                raise Exception("Unsupported ptr to ptr!")
        # elif type_str == "vector":
        #     TODO: Support vector types if needed.
        else:
            raise Exception(f"{type_str} Undefined!")
        return type_str, type_ast

    def value_qir2qasm(self, value_qir: ValueRef) -> Union[ast.IndexedIdentifier, ast.Expression]:
        """Translate a QIR value into an OpenQASM expression or identifier.

        Args:
            value_qir (ValueRef): LLVM/QIR value to translate.

        Returns:
            Union[ast.IndexedIdentifier, ast.Expression]:
                - If the value is a constant integer or float, returns the
                corresponding OpenQASM literal (``IntegerLiteral`` or ``FloatLiteral``).
                - If the value encodes a supported LLVM IR (e.g., ``inttoptr``),
                dispatches to the appropriate ``InstructionBuilder`` and returns the
                resulting identifier.
                - Otherwise, returns the identifier previously recorded in the
                symbol table via ``record_variables()``.
        """
        if value_qir.is_constant:
            value = value_qir.get_constant_value()
            value_ast = None

            if isinstance(value, int):
                value_ast = ast.IntegerLiteral(value)
            elif isinstance(value, float):
                value_ast = ast.FloatLiteral(value)
            else:
                # Many QIR "constant strings" are actually instruction encodings (e.g., inttoptr).
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
            # Non-constant: expect it was recorded earlier via `record_variables()`.
            value_ast = self.get_variables(str(value_qir))
        return value_ast

    def alloc_tmp_var(self, type_ast: Union[ast.ClassicalType, str]) -> ast.IndexedIdentifier:
        """Allocate a temporary variable for either a classical type or a struct.

        Args:
            type_ast (Union[ast.ClassicalType, str]): The type of the temporary.
                - If a string, it is interpreted as the name of a registered
                struct (e.g., "Qubit").
                - If an OpenQASM classical type, a temporary of that type is allocated.

        Returns:
            ast.IndexedIdentifier: An indexed identifier referencing the allocated
            temporary. The identifier name follows:
                - ``<StructName>_tmp[<idx>]`` for struct temporaries.
                - ``<TypeName>_tmp[<idx>]`` for classical temporaries.
        """
        if isinstance(type_ast, str):
            # Struct temporary buffer.
            name = type_ast
            idx = self.structs_tmp_num[name]
            self.structs_tmp_num[name] += 1
            ident_name = self.tmp_naming(self.structs[name].static_name)
            var_ast = ast.IndexedIdentifier(
                name=ast.Identifier(name=ident_name), indices=[[ast.IntegerLiteral(value=idx)]]
            )
        else:
            # Classical temporary buffer.
            assert isinstance(type_ast, ast.ClassicalType)
            name = type_ast.__class__.__name__
            idx = self.classical_tmp_num.get(name)
            if idx is None:
                idx = 0
                self.classical_tmp_num[name] = 1
                self.classical_tmp[name] = type_ast
            else:
                self.classical_tmp_num[name] += 1
            ident_name = self.tmp_naming(name)
            var_ast = ast.IndexedIdentifier(
                name=ast.Identifier(name=ident_name), indices=[[ast.IntegerLiteral(value=idx)]]
            )
        return var_ast

    def alloc_io_var(self, type_ast: ast.ClassicalType, io_key: str) -> ast.Identifier:
        """Allocate a fresh I/O identifier for inputs or outputs.

        Args:
            type_ast (ast.ClassicalType): The OpenQASM classical type of the variable
                (e.g., IntType, FloatType).
            io_key (str): Either ``"input"`` or ``"output"``, indicating the I/O role.

        Returns:
            ast.Identifier: A new identifier with the naming convention
            ``<TypeName>_<i/o><index>``, for example:
                - ``IntType_i0`` for the first integer input.
                - ``FloatType_o1`` for the second float output.
        """
        name = type_ast.__class__.__name__
        idx = len(self.io_variables[io_key])
        ident_name = self.io_naming(name, io_key, idx)
        var_ast = ast.Identifier(name=ident_name)
        self.io_variables[io_key].append((type_ast, var_ast))
        return var_ast

    # def alloc_tmp_struct(self, name) -> ast.IndexedIdentifier:
    #     idx = self.structs_tmp_num[name]
    #     self.structs_tmp_num[name] += 1
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


## StructBuilder implementations


class QubitDeclarationBuilder(DeclBuilder):
    """Declare `qubit name[size]`."""

    def building(self, name: str, size: int) -> ast.Statement:
        ident = ast.Identifier(name=name)
        size_exp = ast.IntegerLiteral(value=size)
        return ast.QubitDeclaration(qubit=ident, size=size_exp)


class ResultDeclarationBuilder(DeclBuilder):
    """Declare a classical bit array for measurement results: `bit[size] name;`."""

    def building(self, name: str, size: int) -> ast.Statement:
        ident = ast.Identifier(name=name)
        size_exp = ast.IntegerLiteral(value=size)
        decl_type = ast.BitType(size=size_exp)
        return ast.ClassicalDeclaration(type=decl_type, identifier=ident)


class ClassicalDeclarationBuilder(DeclBuilder):
    """Declare an array of a given classical base type: `<T>[size] name;`."""

    def __init__(self, base_type: ast.ClassicalType):
        self.base_type = base_type

    def building(self, name: str, size: int) -> ast.Statement:
        ident = ast.Identifier(name=name)
        size_exp = ast.IntegerLiteral(value=size)
        decl_type = ast.ArrayType(base_type=self.base_type, dimensions=[size_exp])
        return ast.ClassicalDeclaration(type=decl_type, identifier=ident)


## InstructionBuilder implementations


class InttoptrBuilder(InstructionBuilder):
    """Translate an `inttoptr`-encoded constant into an OpenQASM indexed identifier.

    Interprets strings like:
      - `%StructName* null`
      - `inttoptr (i64 <idx> to %StructName*)`

    Produces:
      `<StructName>s[<idx>]`  (pluralized buffer of structs)
    """

    def __init__(
        self,
    ):
        # Pattern for `%Struct* null`
        self.null_pattern = r"(?P<ret_type>%\w+\*)\s+null"

        # Pattern for `inttoptr (i64 <idx> to %Struct*)`
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

        # Track the maximum used index for this struct to size declarations later.
        symbols.structs_num[op_name] = max(symbols.structs_num[op_name], idx + 1)

        # Return `<StructName>s[idx]`
        ident_name = symbols.structs[op_name].static_name
        return ast.IndexedIdentifier(
            name=ast.Identifier(name=ident_name), indices=[[ast.IntegerLiteral(value=idx)]]
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


def identifier2expression(
    ident: Union[ast.IndexedIdentifier, ast.Identifier, ast.Expression],
) -> ast.Expression:
    """Convert an identifier to an expression node in OpenQASM."""
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
    """Preprocess parameters for lowering a QIR call to an unknown OpenQASM function.

    This helper analyzes the return type and operands to split them into
    classical arguments, qubit operands, and potential assignment targets.

    Args:
        symbols (SymbolTable): Translation context.
        ret_type (TypeRef): Return type of the QIR instruction.
        operands (List[ValueRef]): Operands of the QIR instruction.

    Returns:
        A tuple (ret_ident, arguments, qubits, assign_ident) where:
        - ret_ident: Optional identifier for the return SSA value
            (``None`` for void-returning calls).
        - arguments: Classical expressions to be passed as arguments.
        - qubits: List of qubit identifiers collected from operands.
        - assign_ident: Identifier representing the assignment resulting
            from a function return or a pointer argument
            (e.g., ``typeA func(...)`` or ``void func(typeA* &arg_A, ...)``).
    """
    ret_ident = None
    assign_ident = None
    arguments = []
    qubits = []

    # Return Type
    ret_type_str, ret_type_ast = symbols.type_qir2qasm(ret_type)
    if ret_type_str == "void":
        ret_ident = None
    else:
        # Allocate a temp to hold the return value.
        struct_name = ret_type_ast
        ret_ident = symbols.alloc_tmp_var(struct_name)
        if struct_name == "Qubit":
            # Pattern: `Qubit* func(...)` becomes `void func(..., Qubit qubit)` in QASM.
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
            # Classical argument
            op_ident = identifier2expression(op_ident)
            arguments.append(op_ident)

            # Return & Assignment
            if op_type_str == "pointer":
                # Pattern: `void func(typeA* &arg_A, ...)` becomes `typeA func(type_A arg_A, ...)`
                assert assign_ident is None
                assign_ident = symbols.value_qir2qasm(op)

    return ret_ident, arguments, qubits, assign_ident


class GateBuilder(FunctionBuilder):
    """Translate a simple quantum gate call.

    Example:
        GateBuilder("rx").building(...) ⇒ `rx(theta) q;`
        GateBuilder("u3", adjoint=True) ⇒ `u3dg(...) q;`  # using "dg" suffix
    """

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
    """Translate a single-qubit reset operation `reset q;`."""

    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        return None, [ast.QuantumReset(qubits=symbols.value_qir2qasm(operands[0]))]


class MeasurementBuilder(FunctionBuilder):
    """Translate measurement operations: `m` or `mresetz`.

    - For `m`, allocate a temporary result and assign `measure q -> result`.
    - For `mresetz`, measure and then reset the same qubit to |0⟩.
    """

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
    """Translate a ``defcal`` function call."""

    def __init__(self, name: str):
        self.ident = ast.Identifier(name=name)

    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        ret_ident, arguments, qubits, assign_ident = preprocess_params(symbols, ret_type, operands)

        # Treat call as a classical function with (args + qubits) as parameters.
        expression = ast.FunctionCall(
            name=self.ident, arguments=arguments + [identifier2expression(q) for q in qubits]
        )

        # expression = ast.QuantumGate(
        #     modifiers=[],
        #     name=self.ident,
        #     arguments=arguments,
        #     qubits=qubits
        # )

        # Assignment vs. pure call
        if assign_ident is not None:
            statement = ast.ClassicalAssignment(
                lvalue=assign_ident, op=ast.AssignmentOperator["="], rvalue=expression
            )
        else:
            statement = ast.ExpressionStatement(expression)

        return ret_ident, [statement]


class LoadBuilder(FunctionBuilder):
    """Translate a simple load-like operation that aliases the operand as the result.

    Semantics:
      result := operand[0]
    """

    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        assert len(operands) == 1
        ret_ident = symbols.value_qir2qasm(operands[0])

        return ret_ident, []


class ConstantBuilder(FunctionBuilder):
    """Emit an assignment from a constant expression into a fresh temporary."""

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
    """Emit `tmp = (lhs <op> rhs)` for a classical binary expression."""

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
    """Do nothing, as OpenQASM does not need to load from memory to register"""

    pass


class InputBuilder(FunctionBuilder):
    """Emit a fresh input identifier of the given classical type."""

    def building(
        self, symbols: SymbolTable, ret_type: TypeRef, operands: List[ValueRef]
    ) -> Tuple[Optional[Union[ast.IndexedIdentifier, ast.Identifier]], List[ast.Statement]]:
        _, type_ast = symbols.type_qir2qasm(ret_type)
        ret_ident = symbols.alloc_io_var(type_ast, "input")
        return ret_ident, []


class OutputBuilder(FunctionBuilder):
    """Write a classical value to a synthesized output identifier."""

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


# ----------------------
# Gate definition helpers
# ----------------------


# Declaration Builder
def build_rotation_2Q_definition(name: str) -> ast.QuantumGateDefinition:
    """Synthesize a standard two-qubit rotation definition (rxx/ryy) via CX-Rz-CX.

    Constructs a gate `name(theta) q0, q1` with the following template:

        (optional pre-rotations)
        cx q0, q1;
        rz(theta) q1;
        cx q0, q1;
        (optional post-rotations)

    The pre/post rotations provide basis changes to realize RXX/RYY variants.

    Args:
        name: One of {"rxx", "ryy", ...}. Unknown names fall back to plain RZZ-like body.

    Returns:
        ast.QuantumGateDefinition with parameter `theta` and qubits q0, q1.
    """
    ident = ast.Identifier(name=name)

    # Define the parameter `_theta` (negated if adjoint)
    theta = ast.Identifier(name="_theta")

    # Qubit identifiers
    q0 = ast.Identifier(name="q0")
    q1 = ast.Identifier(name="q1")

    # Base Rzz-like body: CX - Rz(_theta) - CX
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

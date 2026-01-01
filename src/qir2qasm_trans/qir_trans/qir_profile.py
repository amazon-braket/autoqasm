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

from typing import Dict, List, Union

from llvmlite.ir import (
    Context,
    DoubleType,
    FunctionType,
    IdentifiedStructType,
    IntType,
    Type,
    VoidType,
)
from openqasm3 import ast

from .builder import (
    BinaryExpressionBuilder,
    ConstantBuilder,
    DeclBuilder,
    FunctionBuilder,
    FunctionInfo,
    GateBuilder,
    InputBuilder,
    InstructionBuilder,
    InstructionInfo,
    InttoptrBuilder,
    LoadBuilder,
    MeasurementBuilder,
    OutputBuilder,
    QubitDeclarationBuilder,
    RecordBuilder,
    ResetBuilder,
    ResultDeclarationBuilder,
    StructInfo,
    build_rotation_2Q_definition,
)


class Profile:
    """Base profile for mapping QIR constructs to OpenQASM 3.

    A `Profile` bundles:
      - Structure/type mappings
      - Classical instruction builders
      - Function builders

    Attributes:
        name (str): Profile name (e.g., "base_profile").
        structs (Dict[str, StructInfo]): Registered structure information by name.
        classical_instruction (Dict[str, InstructionInfo]): Builders info for
            LLVM *instructions* (e.g., ``inttoptr``).
        standard_functions (Dict[str, FunctionInfo]): Builders info for QIR
            function calls (e.g., QIS intrinsics).
        context (Context): An LLVM IR context for creating/looking up types.
    """

    def __init__(self, name: str):
        self.name = name
        self.structs: Dict[str, StructInfo] = {}
        self.classical_instruction: Dict[str, InstructionInfo] = {}
        self.standard_functions: Dict[str, FunctionInfo] = {}
        self.context = Context()

        self._define_structs()
        self._define_functions()
        self._define_classical_instructions()

    def register_function(
        self,
        func_name: str,
        ret_type: Type,
        arg_types: List[Type],
        def_statement: ast.QuantumGateDefinition,
        func_builder: FunctionBuilder,
    ):
        fn_type = FunctionType(ret_type, arg_types)
        self.standard_functions[func_name] = FunctionInfo(fn_type, def_statement, func_builder)

    def register_classical_instruction(self, name: str, inst_builder: InstructionBuilder):
        self.classical_instruction[name] = InstructionInfo(builder=inst_builder)

    def register_struct(
        self,
        name: str,
        type_qir: IdentifiedStructType,
        type_ast: Union[ast.ClassicalType, str],
        decl_builder: DeclBuilder,
    ):
        """Register a structure type and its OpenQASM declaration strategy.

        Args:
            name (str): Structure name (e.g., ``"Qubit"``).
            type_qir (IdentifiedStructType): LLVM identified struct type.
            type_ast (Union[ast.ClassicalType, str]): Target OpenQASM AST representation.
            decl_builder (DeclBuilder): Declaration builder for the struct.
        """
        # self.structs[name] = StructInfo(type_qir, None, decl_builder)
        self.structs[name] = StructInfo(type_qir, type_ast, decl_builder, f"{name}s")

    def _define_structs(self):
        """Hook for subclasses to register structure types."""
        pass

    def _define_functions(self):
        """Hook for subclasses to register QIR functions and their builders."""
        pass

    def _define_classical_instructions(self):
        """Hook for subclasses to register LLVM classical instruction lowerings."""
        pass


class BaseProfile(Profile):
    """A minimal profile that wires common QIS intrinsics to OpenQASM gates."""

    def __init__(self):
        super().__init__("base_profile")

    def _define_structs(self):
        """Register core QIR structures: Qubit and Result."""
        self.register_struct(
            "Qubit", self.context.get_identified_type("Qubit"), "Qubit", QubitDeclarationBuilder()
        )
        self.register_struct(
            "Result",
            self.context.get_identified_type("Result"),
            ast.BitType(),
            ResultDeclarationBuilder(),
        )

    def _define_functions(self):
        qubit_ptr = self.structs["Qubit"].type_qir.as_pointer()
        result_ptr = self.structs["Result"].type_qir.as_pointer()
        void_type = VoidType()
        double_type = DoubleType()

        def register_qis_std_gate_functions(
            gates: List[str], ret_type: Type, arg_types: List[Type], adjoint: bool = False
        ):
            """Convenience helper to bulk-register quantum gates."""
            for gate in gates:
                suffix = "adj" if adjoint else "body"
                func_name = f"__quantum__qis__{gate}__{suffix}"
                func_builder = GateBuilder(gate, adjoint=adjoint)
                self.register_function(func_name, ret_type, arg_types, None, func_builder)

        # 1-qubit Clifford/T-like gates and their adjoints
        register_qis_std_gate_functions(["h", "s", "t", "x", "y", "z"], void_type, [qubit_ptr])
        register_qis_std_gate_functions(["s", "t"], void_type, [qubit_ptr], adjoint=True)

        # 2-qubit and 3-qubit gates
        self.register_function(
            "__quantum__qis__cnot__body",
            void_type,
            [qubit_ptr, qubit_ptr],
            None,
            GateBuilder("cx"),
        )
        register_qis_std_gate_functions(["cy", "cz", "swap"], void_type, [qubit_ptr, qubit_ptr])

        # Parameterized 1-qubit rotations
        register_qis_std_gate_functions(["rx", "ry", "rz"], void_type, [double_type, qubit_ptr])

        # 3-qubit Toffoli
        register_qis_std_gate_functions(["ccx"], void_type, [qubit_ptr, qubit_ptr, qubit_ptr])

        # Synthesized 2-qubit XX/YY/ZZ rotations with explicit definitions
        for gate in ["rxx", "ryy", "rzz"]:
            func_name = f"__quantum__qis__{gate}__body"
            self.register_function(
                func_name,
                void_type,
                [double_type, qubit_ptr, qubit_ptr],
                build_rotation_2Q_definition(gate),
                GateBuilder(gate),
            )

        # register_qis_std_gate_functions(["barrier"], void_type, [])

        # Reset
        self.register_function(
            "__quantum__qis__reset__body", void_type, [qubit_ptr], None, ResetBuilder()
        )

        # Measurements
        self.register_function(
            "__quantum__qis__m__body", result_ptr, [qubit_ptr], None, MeasurementBuilder("m")
        )
        for op in ["mz", "mresetz"]:
            func_name = f"__quantum__qis__{op}__body"
            self.register_function(
                func_name, void_type, [qubit_ptr, result_ptr], None, MeasurementBuilder(op)
            )

        # Read result as i1
        self.register_function(
            "__quantum__qis__read_result__body", IntType(1), [result_ptr], None, LoadBuilder()
        )

        # def register_rt_functions(ops: List[str], ret_type: Type, arg_types: List[Type]):
        #     for op in ops:
        #         func_name = f"__quantum__rt__{op}"
        #         self.register_function(func_name, ret_type, arg_types, None, FunctionBuilder())

        # register_rt_functions(["initialize"], void_type, [IntType(8).as_pointer()])
        # register_rt_functions([f"{x}_record_output" for x in ["tuple", "arry"]], void_type, [IntType(64), IntType(8).as_pointer()])

        # Runtime helpers
        self.register_function(
            "__quantum__rt__result_record_output",
            void_type,
            [result_ptr, IntType(8).as_pointer()],
            None,
            RecordBuilder(),
        )

        # Others
        self.register_function(
            "__quantum__rt__result_get_one",
            result_ptr,
            [],
            None,
            ConstantBuilder(constant=ast.BooleanLiteral(value=True)),
        )
        self.register_function(
            "__quantum__rt__result_equal",
            IntType(1),
            [result_ptr, result_ptr],
            None,
            BinaryExpressionBuilder("=="),
        )
        self.register_function("get_int", IntType(32), [], None, InputBuilder())
        self.register_function("take_int", void_type, [IntType(32)], None, OutputBuilder())

    def _define_classical_instructions(self):
        self.register_classical_instruction("inttoptr", InttoptrBuilder())

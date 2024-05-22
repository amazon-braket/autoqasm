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

from copy import deepcopy
from functools import singledispatchmethod
from logging import Logger
from typing import Any, List, Optional, Union

from braket.default_simulator.openqasm._helpers.casting import cast_to, wrap_value_into_literal
from braket.default_simulator.openqasm.interpreter import Interpreter
from braket.default_simulator.openqasm.parser.openqasm_ast import (
    ArrayLiteral,
    BitType,
    BooleanLiteral,
    ClassicalDeclaration,
    IndexedIdentifier,
    IODeclaration,
    IOKeyword,
    QASMNode,
    QuantumMeasurement,
    QuantumMeasurementStatement,
    QuantumReset,
    QubitDeclaration,
)
from braket.default_simulator.openqasm.parser.openqasm_parser import parse
from braket.default_simulator.simulation import Simulation
from openqasm3.ast import IntegerLiteral

from autoqasm.simulator.program_context import McmProgramContext


class NativeInterpreter(Interpreter):
    def __init__(
        self,
        simulation: Simulation,
        context: Optional[McmProgramContext] = None,
        logger: Optional[Logger] = None,
    ):
        self.simulation = simulation
        context = context or McmProgramContext()
        super().__init__(context, logger)

    def simulate(
        self,
        source: str,
        inputs: Optional[dict[str, Any]] = None,
        is_file: bool = False,
        shots: int = 1,
    ) -> dict[str, Any]:
        """Simulates the given program.

        Args:
            source (str): The OpenQASM source program, or a filename containing the
                OpenQASM source program.
            inputs (Optional[dict[str, Any]]): The input parameter values to the OpenQASM
                source program. Defaults to None.
            is_file (bool): Whether `source` is a filename. Defaults to False.
            shots (int): Number of shots of the program to simulate. Defaults to 1.

        Returns:
            dict[str, Any]: Outputs of the program.
        """
        if inputs:
            self.context.load_inputs(inputs)

        if is_file:
            with open(source, encoding="utf-8", mode="r") as f:
                source = f.read()

        program = parse(source)
        for _ in range(shots):
            program_copy = deepcopy(program)
            self.visit(program_copy)
            self.context.save_output_values()
            self.context.num_qubits = 0
            self.simulation.reset()
        return self.context.outputs

    @singledispatchmethod
    def visit(self, node: Union[QASMNode, List[QASMNode]]) -> Optional[QASMNode]:
        """Generic visit function for an AST node"""
        return super().visit(node)

    @visit.register
    def _(self, node: QubitDeclaration) -> None:
        self.logger.debug(f"Qubit declaration: {node}")
        size = self.visit(node.size).value if node.size else 1
        self.context.add_qubits(node.qubit.name, size)
        self.simulation.add_qubits(size)

    @visit.register
    def _(self, node: QuantumMeasurement) -> Union[BooleanLiteral, ArrayLiteral]:
        self.logger.debug(f"Quantum measurement: {node}")
        self.simulation.evolve(self.context.pop_instructions())
        targets = self.context.get_qubits(self.visit(node.qubit))
        outcome = self.simulation.measure(targets)
        if len(targets) > 1 or (
            isinstance(node.qubit, IndexedIdentifier)
            and not len(node.qubit.indices[0]) == 1
            and isinstance(node.qubit.indices[0], IntegerLiteral)
        ):
            return ArrayLiteral([BooleanLiteral(x) for x in outcome])
        return BooleanLiteral(outcome[0])

    @visit.register
    def _(self, node: QuantumMeasurementStatement) -> Union[BooleanLiteral, ArrayLiteral]:
        self.logger.debug(f"Quantum measurement statement: {node}")
        outcome = self.visit(node.measure)
        current_value = self.context.get_value_by_identifier(node.target)
        result_type = (
            BooleanLiteral
            if isinstance(current_value, BooleanLiteral) or current_value is None
            else BitType(size=IntegerLiteral(len(current_value.values)))
        )
        value = cast_to(result_type, outcome)
        self.context.update_value(node.target, value)

    @visit.register
    def _(self, node: QuantumReset) -> None:
        self.logger.debug(f"Quantum reset: {node}")
        self.simulation.evolve(self.context.pop_instructions())
        targets = self.context.get_qubits(self.visit(node.qubits))
        outcome = self.simulation.measure(targets)
        for qubit, result in zip(targets, outcome):
            if result:
                self.simulation.flip(qubit)

    @visit.register
    def _(self, node: IODeclaration) -> None:
        self.logger.debug(f"IO Declaration: {node}")
        if node.io_identifier == IOKeyword.output:
            if node.identifier.name not in self.context.outputs:
                self.context.add_output(node.identifier.name)
            self.context.declare_variable(
                node.identifier.name,
                node.type,
            )
        else:  # IOKeyword.input:
            if node.identifier.name not in self.context.inputs:
                raise NameError(f"Missing input variable '{node.identifier.name}'.")
            init_value = wrap_value_into_literal(self.context.inputs[node.identifier.name])
            declaration = ClassicalDeclaration(node.type, node.identifier, init_value)
            self.visit(declaration)

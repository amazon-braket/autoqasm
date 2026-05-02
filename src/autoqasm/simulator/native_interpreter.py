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
from typing import Any

from openqasm3.ast import IntegerLiteral

from autoqasm.simulator.program_context import McmProgramContext
from braket.default_simulator.openqasm._helpers.casting import cast_to, wrap_value_into_literal
from braket.default_simulator.openqasm.interpreter import Interpreter
from braket.default_simulator.openqasm.parser.openqasm_ast import (
    ArrayLiteral,
    BitType,
    BooleanLiteral,
    ClassicalDeclaration,
    Identifier,
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


class NativeInterpreter(Interpreter):
    def __init__(
        self,
        simulation: Simulation,
        context: McmProgramContext | None = None,
        logger: Logger | None = None,
    ):
        self.simulation = simulation
        context = context or McmProgramContext()
        super().__init__(context, logger)

    def simulate(
        self,
        source: str,
        inputs: dict[str, Any] | None = None,
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
    def visit(self, node: QASMNode | list[QASMNode]) -> QASMNode | None:
        """Generic visit function for an AST node"""
        return super().visit(node)

    @visit.register
    def _(self, node: QubitDeclaration) -> None:
        self.logger.debug(f"Qubit declaration: {node}")
        size = self.visit(node.size).value if node.size else 1
        self.context.add_qubits(node.qubit.name, size)
        self.simulation.add_qubits(size)

    @visit.register
    def _(self, node: QuantumMeasurement) -> BooleanLiteral | ArrayLiteral:
        self.logger.debug(f"Quantum measurement: {node}")
        self.simulation.evolve(self.context.pop_instructions())
        targets = self.context.get_qubits(self.visit(node.qubit))
        outcome = self.simulation.measure(targets)
        if len(targets) > 1 or (
            isinstance(node.qubit, IndexedIdentifier)
            and len(node.qubit.indices[0]) != 1
            and isinstance(node.qubit.indices[0], IntegerLiteral)
        ):
            return ArrayLiteral([BooleanLiteral(x) for x in outcome])
        return BooleanLiteral(outcome[0])

    @visit.register
    def _(self, node: QuantumMeasurementStatement) -> BooleanLiteral | ArrayLiteral:
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

    def handle_builtin_gate(
        self,
        gate_name: str,
        arguments: list,
        qubits: list,
        modifiers: list,
    ) -> None:
        """Handle a call to a built-in quantum gate.

        Intercepts the IQM classical-control gates ``measure_ff`` and
        ``cc_prx`` and implements them directly against ``self.simulation``,
        bypassing the upstream ``ProgramContext`` mid-circuit-measurement
        pipeline (which is built around a one-pass, all-shots-at-once
        branching model incompatible with this per-shot interpreter).
        """
        if gate_name == "measure_ff":
            self._handle_measure_ff(arguments, qubits)
            return
        if gate_name == "cc_prx":
            self._handle_cc_prx(arguments, qubits, modifiers)
            return
        super().handle_builtin_gate(gate_name, arguments, qubits, modifiers)

    def _handle_measure_ff(self, arguments: list, qubits: list) -> None:
        """Measure the target qubit and bind the outcome under a synthetic
        bit variable ``__ff_<feedback_key>__`` in the context's symbol table.
        """
        feedback_key = int(arguments[0].value)
        ff_name = _feedback_key_name(feedback_key)
        # Flush pending gates so the measurement sees the right state.
        self.simulation.evolve(self.context.pop_instructions())
        targets = self.context.get_qubits(qubits[0])
        outcome = self.simulation.measure(targets)
        try:
            self.context.get_type(ff_name)
        except KeyError:
            self.context.declare_variable(ff_name, BitType(size=None))
        self.context.update_value(
            Identifier(name=ff_name),
            BooleanLiteral(bool(outcome[0])),
        )

    def _handle_cc_prx(
        self,
        arguments: list,
        qubits: list,
        modifiers: list,
    ) -> None:
        """Apply ``prx(angle_0, angle_1) q`` only when the feedback bit
        identified by ``feedback_key`` is ``1``.
        """
        feedback_key = int(arguments[2].value)
        ff_name = _feedback_key_name(feedback_key)
        try:
            ff_value = self.context.get_value_by_identifier(Identifier(name=ff_name))
        except KeyError as exc:
            raise ValueError(
                f"cc_prx references feedback key {feedback_key}, but no measure_ff "
                "has been recorded for that key."
            ) from exc
        if ff_value is None or not bool(getattr(ff_value, "value", ff_value)):
            return
        # Dispatch through the normal builtin-gate path so gate modifiers
        # (ctrl, pow, etc.) are honoured consistently with other gates.
        super().handle_builtin_gate("prx", arguments[:2], qubits, modifiers)


def _feedback_key_name(feedback_key: int) -> str:
    """Synthetic bit-variable name used to store a feedback key's value.

    Matches the convention used by ``braket.default_simulator``.
    """
    return f"__ff_{int(feedback_key)}__"

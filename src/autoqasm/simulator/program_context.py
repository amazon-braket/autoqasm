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

from __future__ import annotations

from collections.abc import Sequence
from functools import singledispatchmethod
from typing import Optional, Union

import numpy as np
from braket.default_simulator.openqasm._helpers.arrays import (
    convert_discrete_set_to_list,
    convert_range_def_to_slice,
)
from braket.default_simulator.openqasm.circuit import Circuit
from braket.default_simulator.openqasm.parser.openqasm_ast import (
    ClassicalType,
    DiscreteSet,
    Identifier,
    IndexedIdentifier,
    IntegerLiteral,
    RangeDefinition,
    SymbolLiteral,
)
from braket.default_simulator.openqasm.program_context import ProgramContext, Table
from braket.default_simulator.operation import GateOperation

from autoqasm.simulator.conversion import convert_to_output


class QubitTable(Table):
    def __init__(self):
        super().__init__("Qubits")

    def _validate_qubit_in_range(self, qubit: int, register_name: str) -> None:
        if qubit >= len(self[register_name]):
            raise IndexError(
                f"qubit register index `{qubit}` out of range for qubit register "
                f"of length {len(self[register_name])} `{register_name}`."
            )

    @singledispatchmethod
    def get_by_identifier(self, identifier: Union[Identifier, IndexedIdentifier]) -> tuple[int]:
        """Convenience method to get an element with a possibly indexed identifier.

        Args:
            identifier (Union[Identifier, IndexedIdentifier]): _description_

        Returns:
            tuple[int]: _description_
        """
        if identifier.name.startswith("$"):
            return (int(identifier.name[1:]),)
        return self[identifier.name]

    @get_by_identifier.register
    def _(self, identifier: IndexedIdentifier) -> tuple[int]:  # noqa: C901
        """When identifier is an IndexedIdentifier, function returns a tuple
        corresponding to the elements referenced by the indexed identifier.

        Args:
            identifier (IndexedIdentifier): _description_

        Raises:
            IndexError: Qubit register index out of range for specified register.

        Returns:
            tuple[int]: _description_
        """
        name = identifier.name.name
        indices = self.get_qubit_indices(identifier)
        primary_index = indices[0]

        if isinstance(primary_index, (IntegerLiteral, SymbolLiteral)):
            if isinstance(primary_index, IntegerLiteral):
                self._validate_qubit_in_range(primary_index.value)
            target = (self[name][0] + primary_index.value,)
        elif isinstance(primary_index, RangeDefinition):
            target = tuple(np.array(self[name])[convert_range_def_to_slice(primary_index)])
        # Discrete set
        else:
            index_list = convert_discrete_set_to_list(primary_index)
            for index in index_list:
                if isinstance(index, int):
                    self._validate_qubit_in_range(index)
            target = tuple([self[name][0] + index for index in index_list])

        if len(indices) == 2:
            # used for gate calls on registers, index will be IntegerLiteral
            secondary_index = indices[1].value
            target = (target[secondary_index],)

        # validate indices manually, since we use addition instead of indexing to
        # accommodate symbolic indices
        for q in target:
            if isinstance(q, int) and (relative_index := q - self[name][0]) >= len(self[name]):
                raise IndexError(
                    f"qubit register index `{relative_index}` out of range for qubit register "
                    f"of length {len(self[name])} `{name}`."
                )
        return target

    @staticmethod
    def get_qubit_indices(
        identifier: IndexedIdentifier,
    ) -> list[IntegerLiteral | RangeDefinition | DiscreteSet]:
        """_summary_

        Args:
            identifier (IndexedIdentifier): _description_

        Raises:
            IndexError: Index consists of multiple dimensions.

        Returns:
            list[IntegerLiteral | RangeDefinition | DiscreteSet]: _description_
        """
        primary_index = identifier.indices[0]

        if isinstance(primary_index, list):
            if len(primary_index) != 1:
                raise IndexError("Cannot index multiple dimensions for qubits.")
            primary_index = primary_index[0]

        if len(identifier.indices) == 1:
            return [primary_index]
        elif len(identifier.indices) == 2:
            # used for gate calls on registers, index will be IntegerLiteral
            secondary_index = identifier.indices[1][0]
            return [primary_index, secondary_index]
        else:
            raise IndexError("Cannot index multiple dimensions for qubits.")

    def _get_indices_length(
        self,
        indices: Sequence[IntegerLiteral | SymbolLiteral | RangeDefinition | DiscreteSet],
    ) -> int:
        last_index = indices[-1]

        if isinstance(last_index, (IntegerLiteral, SymbolLiteral)):
            return 1
        elif isinstance(last_index, RangeDefinition):
            buffer = np.sign(last_index.step.value) if last_index.step is not None else 1
            start = last_index.start.value if last_index.start is not None else 0
            stop = last_index.end.value + buffer
            step = last_index.step.value if last_index.step is not None else 1
            return (stop - start) // step
        elif isinstance(last_index, DiscreteSet):
            return len(last_index.values)

    def get_qubit_size(self, identifier: Union[Identifier, IndexedIdentifier]) -> int:
        """_summary_

        Args:
            identifier (Union[Identifier, IndexedIdentifier]): _description_

        Returns:
            int: _description_
        """
        if isinstance(identifier, IndexedIdentifier):
            indices = self.get_qubit_indices(identifier)
            return self._get_indices_length(indices)
        return len(self.get_by_identifier(identifier))


class McmProgramContext(ProgramContext):
    def __init__(self, circuit: Optional[Circuit] = None):
        """
        Args:
            circuit (Optional[Circuit]): A partially-built circuit to continue building with this
                context. Default: None.
        """
        self.outputs = {}
        self._circuit = circuit or Circuit()
        super(ProgramContext, self).__init__()

    def pop_instructions(self) -> list[GateOperation]:
        """_summary_

        Returns:
            list[GateOperation]: _description_
        """
        instructions = self.circuit.instructions
        self.circuit.instructions = []
        return instructions

    def add_output(self, output_name: str) -> None:
        """_summary_

        Args:
            output_name (str): _description_
        """
        self.outputs[output_name] = []

    def save_output_values(self) -> None:
        """_summary_"""
        if not self.outputs:
            self.outputs = {
                v: []
                for v in self.symbol_table.current_scope
                if isinstance(self.get_type(v), ClassicalType)
            }
        for output, shot_data in self.outputs.items():
            shot_data.append(convert_to_output(self.get_value(output)))

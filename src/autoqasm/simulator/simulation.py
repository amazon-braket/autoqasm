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

import numpy as np
from braket.default_simulator import StateVectorSimulation
from braket.default_simulator.gate_operations import PauliX
from braket.default_simulator.linalg_utils import marginal_probability

from autoqasm.simulator.linalg_utils import measurement_collapse_sv, measurement_sample


class Simulation(StateVectorSimulation):
    def add_qubits(self, num_qubits: int) -> None:
        """Adds the given number of qubits to the simulation.

        Args:
            num_qubits (int): The number of qubits to add.
        """
        expanded_dims = np.expand_dims(self.state_vector, -1)
        expanded_qubits = np.append(
            expanded_dims, np.zeros((expanded_dims.size, 2**num_qubits - 1)), axis=-1
        )
        self._state_vector = expanded_qubits.flatten()
        self._qubit_count += num_qubits

    def measure(self, targets: tuple[int]) -> tuple[int]:
        """Measures the specified qubits and returns the outcome.

        Args:
            targets (tuple[int]): The qubit indices to measure.

        Returns:
            tuple[int]: The measurement outcomes 0 or 1 for each measured qubit.
        """
        mprob = marginal_probability(self.probabilities, targets)
        outcome = measurement_sample(mprob, len(targets))
        self._state_vector = measurement_collapse_sv(
            self._state_vector,
            targets,
            outcome,
        )
        return outcome

    def reset(self) -> None:
        """Resets the simulation and resets the qubit count to 0."""
        self._state_vector = np.array([1], dtype=complex)
        self._qubit_count = 0

    def flip(self, target: int) -> None:
        """Performs a bit flip (PauliX operation) on the specified qubit.

        Args:
            target (int): The qubit index on which to perform a bit flip.
        """
        self.evolve([PauliX([target])])

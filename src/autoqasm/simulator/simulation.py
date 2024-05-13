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
        """_summary_

        Args:
            num_qubits (int): _description_
        """
        expanded_dims = np.expand_dims(self.state_vector, -1)
        expanded_qubits = np.append(
            expanded_dims, np.zeros((expanded_dims.size, 2**num_qubits - 1)), axis=-1
        )
        self._state_vector = expanded_qubits.flatten()
        self._qubit_count += num_qubits

    def measure(self, targets: tuple[int]) -> tuple[int]:
        """_summary_

        Args:
            targets (tuple[int]): _description_

        Returns:
            tuple[int]: _description_
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
        """_summary_"""
        self._state_vector = np.array([1], dtype=complex)
        self._qubit_count = 0

    def flip(self, target: int) -> None:
        """_summary_

        Args:
            target (int): _description_
        """
        self.evolve([PauliX([target])])

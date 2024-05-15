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

import itertools
from collections.abc import Iterable

import numpy as np


def measurement_sample(prob: float, target_count: int) -> tuple[int]:
    """_summary_

    Args:
        prob (float): _description_
        target_count (int): _description_

    Returns:
        tuple[int]: _description_
    """
    basis_states = np.array(list(itertools.product([0, 1], repeat=target_count)))
    outcome_idx = np.random.choice(list(range(2**target_count)), p=prob)
    return tuple(basis_states[outcome_idx])


def measurement_collapse_sv(
    state_vector: np.ndarray, targets: Iterable[int], outcome: np.ndarray
) -> np.ndarray:
    """_summary_

    Args:
        state_vector (np.ndarray): _description_
        targets (Iterable[int]): _description_
        outcome (np.ndarray): _description_

    Returns:
        np.ndarray: _description_
    """
    qubit_count = int(np.log2(state_vector.size))
    state_tensor = state_vector.reshape([2] * qubit_count)
    for qubit, measurement in zip(targets, outcome):
        state_tensor[(slice(None),) * qubit + (int(not measurement),)] = 0

    state_tensor /= np.linalg.norm(state_tensor)
    return state_tensor.flatten()

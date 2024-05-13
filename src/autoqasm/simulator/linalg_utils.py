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


def measurement_collapse_dm(
    dm_tensor: np.ndarray, targets: Iterable[int], outcomes: np.ndarray
) -> np.ndarray:
    """_summary_

    Args:
        dm_tensor (np.ndarray): _description_
        targets (Iterable[int]): _description_
        outcomes (np.ndarray): _description_

    Returns:
        np.ndarray: _description_
    """
    # TODO: This needs to be modified to not delete qubits

    # move the target qubit to the front of axes
    qubit_count = int(np.log2(dm_tensor.shape[0]))
    unused_idxs = [idx for idx in range(qubit_count) if idx not in targets]
    unused_idxs = [
        p + i * qubit_count for i in range(2) for p in unused_idxs
    ]  # convert indices to dm form
    target_indx = [
        p + i * qubit_count for i in range(2) for p in targets
    ]  # convert indices to dm form
    permutation = target_indx + unused_idxs
    inverse_permutation = np.argsort(permutation)

    # collapse the density matrix based on measuremnt outcome
    outcomes = tuple(i for _ in range(2) for i in outcomes)
    new_dm_tensor = np.zeros_like(dm_tensor)
    new_dm_tensor[outcomes] = np.transpose(dm_tensor, permutation)[outcomes]
    new_dm_tensor = np.transpose(new_dm_tensor, inverse_permutation)

    # normalize
    new_trace = np.trace(np.reshape(new_dm_tensor, (2**qubit_count, 2**qubit_count)))
    new_dm_tensor = new_dm_tensor / new_trace
    return new_dm_tensor


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

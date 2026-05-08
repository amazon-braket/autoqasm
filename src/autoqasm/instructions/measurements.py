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

"""Quantum measurement on qubits.

Example of measuring qubit 0:

.. code-block:: python

    @aq.main
    def my_program():
        measure(0)
"""

from __future__ import annotations

from collections.abc import Iterable

from autoqasm import program
from autoqasm import types as aq_types
from autoqasm.instructions.instructions import _qubit_instruction
from autoqasm.instructions.qubits import _as_qubit_iterable, _qubit, global_qubit_register


def measure(
    qubits: aq_types.QubitIdentifierType | Iterable[aq_types.QubitIdentifierType] | None = None,
) -> aq_types.BitVar:
    """Add qubit measurement statements to the program and assign the measurement
    results to bit variables.

    Args:
        qubits (QubitIdentifierType | Iterable[QubitIdentifierType] | None): The target qubits
            to measure. If None, all qubits will be measured. Default is None.

    Returns:
        BitVar: Bit variable the measurement results are assigned to.
    """
    qubits = _as_qubit_iterable(qubits, default=global_qubit_register())

    oqpy_program = program.get_program_conversion_context().get_oqpy_program()

    bit_var_size = len(qubits) if len(qubits) > 1 else None
    bit_var = aq_types.BitVar(
        size=bit_var_size,
        needs_declaration=True,
    )
    oqpy_program.declare(bit_var)

    qubits = [_qubit(qubit) for qubit in qubits]
    if len(qubits) == 1:
        oqpy_program.measure(qubits[0], bit_var)
    else:
        for idx, qubit in enumerate(qubits):
            oqpy_program.measure(qubit, bit_var[idx])

    return bit_var


def measure_ff(
    target: aq_types.QubitIdentifierType,
    feedback_key: int,
    **kwargs,
) -> None:
    """Measure a qubit and store its result under a classical feedback key.

    The measurement result is not bound to a Python variable; instead it is
    stored by the runtime under the integer ``feedback_key`` so that it can
    be consumed later in the same program by a classically-controlled
    operation such as :func:`autoqasm.instructions.cc_prx`.

    This is an IQM experimental capability. See
    :class:`braket.experimental_capabilities.iqm.classical_control.MeasureFF`
    for the corresponding Braket SDK surface.

    Args:
        target (QubitIdentifierType): The qubit to measure.
        feedback_key (int): Integer key under which the measurement result
            is recorded. Must match the ``feedback_key`` passed to any
            subsequent ``cc_prx`` call that depends on this measurement.

    """
    _qubit_instruction("measure_ff", [target], feedback_key, is_unitary=False, **kwargs)

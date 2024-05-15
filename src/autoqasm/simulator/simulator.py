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

from braket.default_simulator import StateVectorSimulator
from braket.ir.openqasm import Program as OpenQASMProgram
from braket.task_result import AdditionalMetadata, TaskMetadata
from braket.tasks import GateModelQuantumTaskResult

from autoqasm.simulator.native_interpreter import NativeInterpreter
from autoqasm.simulator.program_context import McmProgramContext
from autoqasm.simulator.simulation import Simulation


class McmSimulator(StateVectorSimulator):
    DEVICE_ID = "autoqasm"

    def initialize_simulation(self, **kwargs) -> Simulation:
        """
        Initialize simulation with mid-circuit measurement (MCM) support.

        Args:
            `**kwargs`: qubit_count, shots, batch_size

        Returns:
            Simulation: Initialized simulation.
        """
        qubit_count = kwargs.get("qubit_count")
        shots = kwargs.get("shots")
        batch_size = kwargs.get("batch_size")
        return Simulation(qubit_count, shots, batch_size)

    def create_program_context(self) -> McmProgramContext:
        return McmProgramContext()

    def run(
        self,
        openqasm_ir: OpenQASMProgram,
        shots: int = 0,
        *,
        batch_size: int = 1,
    ) -> GateModelQuantumTaskResult:
        """Executes the program specified by the supplied `circuit_ir` on the simulator.

        Args:
            openqasm_ir (OpenQASMProgram): ir representation of a program specifying the
                instructions to execute.
            shots (int): The number of times to run the circuit.
            batch_size (int): The size of the circuit partitions to contract,
                if applying multiple gates at a time is desired; see `StateVectorSimulation`.
                Must be a positive integer.
                Defaults to 1, which means gates are applied one at a time without any
                optimized contraction.
        Returns:
            GateModelQuantumTaskResult: object that represents the result

        Raises:
            ValueError: If result types are not specified in the IR or sample is specified
                as a result type when shots=0. Or, if StateVector and Amplitude result types
                are requested when shots>0.
        """
        is_file = openqasm_ir.source.endswith(".qasm")
        simulation = self.initialize_simulation(qubit_count=0, shots=shots, batch_size=batch_size)
        interpreter = NativeInterpreter(simulation=simulation)

        context = interpreter.simulate(
            source=openqasm_ir.source,
            inputs=openqasm_ir.inputs,
            is_file=is_file,
            shots=shots,
        )

        return GateModelQuantumTaskResult(
            task_metadata=TaskMetadata.construct(id="", shots=shots),
            additional_metadata=AdditionalMetadata.construct(),
            measurements=context,
        )

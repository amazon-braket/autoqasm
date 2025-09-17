OPENQASM 3.0;
include "stdgates.inc";
qubit[2] Qubits;
bit[2] Results;
h Qubits[0];
cx Qubits[0], Qubits[1];
Results[0] = measure Qubits[0];
Results[1] = measure Qubits[1];
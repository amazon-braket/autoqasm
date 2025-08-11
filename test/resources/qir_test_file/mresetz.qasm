OPENQASM 3.0;
include "stdgates.inc";
qubit[1] Qubits;
bit[1] Results;
Results[0] = measure Qubits[0];
reset Qubits[0];
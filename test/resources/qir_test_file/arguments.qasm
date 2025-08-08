OPENQASM 3.0;
include "stdgates.inc";
qubit[2] Qubits;
defcal my_test() q0, q1 {}
my_test(Qubits[0], Qubits[1]);
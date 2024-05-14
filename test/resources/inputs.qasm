OPENQASM 3.0;
input float theta;
output bit return_value;
qubit[1] __qubits__;
rx(theta) __qubits__[0];
bit __bit_0__;
__bit_0__ = measure __qubits__[0];
return_value = __bit_0__;

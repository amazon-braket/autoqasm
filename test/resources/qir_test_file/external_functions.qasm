OPENQASM 3.0;
include "stdgates.inc";
qubit[1] Qubits;
array[float[64], 1] FloatType_tmp;
defcal my_function()  {}
defcal my_gate(int[64]) q {}
defcal get_angle()  -> float[64] {}
my_function();
my_gate(123, Qubits[0]);
FloatType_tmp[0] = get_angle();
rz(FloatType_tmp[0]) Qubits[0];
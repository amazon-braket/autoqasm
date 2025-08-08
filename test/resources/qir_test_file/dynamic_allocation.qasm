OPENQASM 3.0;
include "stdgates.inc";
qubit[1] Qubits_tmp;
bit[2] Results_tmp;
array[bool, 1] BoolType_tmp;
defcal __quantum__rt__qubit_allocate() q_ret {}
defcal __quantum__rt__qubit_release() q {}
__quantum__rt__qubit_allocate(Qubit_tmp[0]);
h Qubit_tmp[0];
Result_tmp[0] = measure Qubit_tmp[0];
Result_tmp[1] = true;
BoolType_tmp[0] = Result_tmp[0] == Result_tmp[1];
reset Qubit_tmp[0];
__quantum__rt__qubit_release(Qubit_tmp[0]);
OPENQASM 3.0;
qubit[1] Qubits_tmp;
bit[2] Results_tmp;
array[bool, 1] BoolType_tmp;
defcal __quantum__rt__qubit_allocate() q_ret {}
defcal __quantum__rt__qubit_release() q {}
__quantum__rt__qubit_allocate(Qubits_tmp[0]);
h Qubits_tmp[0];
Results_tmp[0] = measure Qubits_tmp[0];
Results_tmp[1] = true;
BoolType_tmp[0] = Results_tmp[0] == Results_tmp[1];
reset Qubits_tmp[0];
__quantum__rt__qubit_release(Qubits_tmp[0]);
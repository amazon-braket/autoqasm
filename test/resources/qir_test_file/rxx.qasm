OPENQASM 3.0;
qubit[2] Qubits;
gate rxx(_theta) q0, q1 {
  h q0;
  h q1;
  cx q0, q1;
  rz(_theta) q1;
  cx q0, q1;
  h q0;
  h q1;
}
rxx(1.0) Qubits[0], Qubits[1];
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] Qubits;
gate rxx(θ) q0, q1 {
  h q0;
  h q1;
  cx q0, q1;
  rz(θ) q1;
  cx q0, q1;
  h q0;
  h q1;
}
rxx(1.0) Qubits[0], Qubits[1];
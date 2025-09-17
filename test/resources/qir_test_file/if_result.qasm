OPENQASM 3.0;
qubit[2] Qubits;
bit[2] Results;
h Qubits[0];
Results[0] = measure Qubits[0];
if (Results[0]) {
  x Qubits[0];
}
h Qubits[0];
Results[0] = measure Qubits[0];
h Qubits[1];
Results[1] = measure Qubits[1];
if (Results[0]) {
  if (Results[1]) {
    x Qubits[0];
    x Qubits[1];
  }
}
if (Results[0]) {
} else {
  x Qubits[0];
}
if (Results[0]) {
  z Qubits[0];
} else {
  y Qubits[0];
}
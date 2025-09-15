OPENQASM 3.0;
array[int[32], 3] IntType_tmp;
input int[32] IntType_i0;
if (0) {
  IntType_tmp[0] = 1 + IntType_i0;
  if (0) {
    IntType_tmp[1] = 2 + IntType_i0;
  }
}
IntType_tmp[2] = 3 + IntType_i0;
OPENQASM 3.0;
array[int[32], 6] IntType_tmp;
input int[32] IntType_i0;
IntType_tmp[0] = 0 + IntType_i0;
if (0) {
  IntType_tmp[1] = 1 + IntType_i0;
  if (0) {
    IntType_tmp[3] = 3 + IntType_i0;
  } else {
    IntType_tmp[4] = 4 + IntType_i0;
  }
} else {
  IntType_tmp[2] = 2 + IntType_i0;
  IntType_tmp[4] = 4 + IntType_i0;
}
IntType_tmp[5] = 5 + IntType_i0;

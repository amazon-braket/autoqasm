OPENQASM 3.0;
include "stdgates.inc";
bit[1] Results;
defcal my_test(bit)  -> bit {}
my_test(Results[0]);
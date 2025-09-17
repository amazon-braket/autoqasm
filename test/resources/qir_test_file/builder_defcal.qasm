OPENQASM 3.0;
bit[1] Results;
defcal my_test(bit)  -> bit {}
Results[0] = my_test(Results[0]);
; ModuleID = 'llvm_inst_error'
source_filename = "llvm_inst_error.ll"
%MyStruct = type { i32, float }

@g_i32     = global i32 42, align 4
@g_struct  = global %MyStruct { i32 1, float 1.000000e+00 }, align 8
@g_array   = global [4 x i8] zeroinitializer, align 1

define void @main() #0 {
entry:
%0 = load i32, i32* @g_i32, align 4
ret void
}

attributes #0 = {"entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="0" }

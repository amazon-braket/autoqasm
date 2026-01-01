; ModuleID = 'instruction_error'
source_filename = "instruction_error.ll"

@str_r1 = internal constant [3 x i8] c"r1\00"

declare void @my__result_record_output(i8*)

define void @main() #0 {
entry:
call void @my__result_record_output(i8* getelementptr inbounds ([3 x i8], [3 x i8]* @str_r1, i32 0, i32 0))
ret void
}

attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="0" }

!llvm.module.flags = !{!0, !1, !2, !3}

!0 = !{i32 1, !"qir_major_version", i32 1}
!1 = !{i32 7, !"qir_minor_version", i32 0}
!2 = !{i32 1, !"dynamic_qubit_management", i1 false}
!3 = !{i32 1, !"dynamic_result_management", i1 false}
; ModuleID = 'arithmetic'
source_filename = "arithmetic"

define void @main() #0 {
entry:
  %0 = call i32 @get_int()
  %1 = add i32 3, %0
  %2 = mul i32 2, %1
  %3 = call i32 @get_int()
  %4 = sub i32 0, %3
  call void @take_int(i32 %2)
  call void @take_int(i32 %4)
  ret void
}

declare i32 @get_int()

declare void @take_int(i32)

attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="0" }

!llvm.module.flags = !{!0, !1, !2, !3}

!0 = !{i32 1, !"qir_major_version", i32 1}
!1 = !{i32 7, !"qir_minor_version", i32 0}
!2 = !{i32 1, !"dynamic_qubit_management", i1 false}
!3 = !{i32 1, !"dynamic_result_management", i1 false}

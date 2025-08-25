; ModuleID = 'arguments'
source_filename = "arguments.ll"

%Qubit = type opaque

declare void @my_test(%Qubit*, %Qubit*)

define void @main() #0 {
entry:
call void @my_test(%Qubit* null, %Qubit* inttoptr (i64 1 to %Qubit*))
ret void
}

attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="2" "required_num_results"="0" }

!llvm.module.flags = !{!0, !1, !2, !3}

!0 = !{i32 1, !"qir_major_version", i32 1}
!1 = !{i32 7, !"qir_minor_version", i32 0}
!2 = !{i32 1, !"dynamic_qubit_management", i1 false}
!3 = !{i32 1, !"dynamic_result_management", i1 false}
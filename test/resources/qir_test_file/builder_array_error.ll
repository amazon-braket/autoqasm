; ModuleID = 'builder_array_error'
source_filename = "builder_array_error"

%Qubit = type opaque
%Result = type opaque

@v1 = constant <8 x i32> <i32 1, i32 2, i32 3, i32 4, i32 5, i32 6, i32 7, i32 8>

declare <8 x i32> @add_int_vectors(<8 x i32>) 

define void @main() #0 {
entry:
%p1 = load <8 x i32>, <8 x i32>* @v1
%res = call <8 x i32> @add_int_vectors(<8 x i32> %p1)
ret void
}

attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="0" "required_num_results"="0" }
attributes #1 = { "irreversible" }

!llvm.module.flags = !{!0, !1, !2, !3}

!0 = !{i32 1, !"qir_major_version", i32 1}
!1 = !{i32 7, !"qir_minor_version", i32 0}
!2 = !{i32 1, !"dynamic_qubit_management", i1 false}
!3 = !{i32 1, !"dynamic_result_management", i1 false}
; ModuleID = 'dynamic_allocation'
source_filename = "dynamic_allocation"

%Qubit = type opaque
%Result = type opaque

declare %Qubit* @__quantum__rt__qubit_allocate()

declare void @__quantum__rt__qubit_release(%Qubit*)

declare %Result* @__quantum__rt__result_get_one()

declare i1 @__quantum__rt__result_equal(%Result*, %Result*)

declare %Result* @__quantum__qis__m__body(%Qubit*)

define void @main() #0 {
entry:
  %0 = call %Qubit* @__quantum__rt__qubit_allocate()
  call void @__quantum__qis__h__body(%Qubit* %0)
  %1 = call %Result* @__quantum__qis__m__body(%Qubit* %0)
  %2 = call %Result* @__quantum__rt__result_get_one()
  %3 = call i1 @__quantum__rt__result_equal(%Result* %1, %Result* %2)
  call void @__quantum__qis__reset__body(%Qubit* %0)
  call void @__quantum__rt__qubit_release(%Qubit* %0)
  ret void
}

declare void @__quantum__qis__h__body(%Qubit*)

declare void @__quantum__qis__reset__body(%Qubit*)

attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="1" "required_num_results"="1" }

!llvm.module.flags = !{!0, !1, !2, !3}

!0 = !{i32 1, !"qir_major_version", i32 1}
!1 = !{i32 7, !"qir_minor_version", i32 0}
!2 = !{i32 1, !"dynamic_qubit_management", i1 true}
!3 = !{i32 1, !"dynamic_result_management", i1 true}

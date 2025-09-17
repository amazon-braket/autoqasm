; ModuleID = 'external_functions'
source_filename = "external_functions"

%Qubit = type opaque

define void @main() #0 {
entry:
  call void @my_function()
  call void @my_gate(i64 123, %Qubit* null)
  %0 = call double @get_angle()
  call void @__quantum__qis__rz__body(double %0, %Qubit* null)
  ret void
}

declare void @my_function()

declare void @my_gate(i64, %Qubit*)

declare double @get_angle()

declare void @__quantum__qis__rz__body(double, %Qubit*)

attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="1" "required_num_results"="0" }

!llvm.module.flags = !{!0, !1, !2, !3}

!0 = !{i32 1, !"qir_major_version", i32 1}
!1 = !{i32 7, !"qir_minor_version", i32 0}
!2 = !{i32 1, !"dynamic_qubit_management", i1 false}
!3 = !{i32 1, !"dynamic_result_management", i1 false}
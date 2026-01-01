; ModuleID = 'if_result'
source_filename = "if_result"

%Qubit = type opaque
%Result = type opaque

define void @main() #0 {
entry:
  call void @__quantum__qis__h__body(%Qubit* null)
  call void @__quantum__qis__mz__body(%Qubit* null, %Result* null)
  %0 = call i1 @__quantum__qis__read_result__body(%Result* null)
  br i1 %0, label %then, label %else

then:                                             ; preds = %entry
  call void @__quantum__qis__x__body(%Qubit* null)
  br label %continue

else:                                             ; preds = %entry
  br label %continue

continue:                                         ; preds = %else, %then
  call void @__quantum__qis__h__body(%Qubit* null)
  call void @__quantum__qis__mz__body(%Qubit* null, %Result* null)
  call void @__quantum__qis__h__body(%Qubit* inttoptr (i64 1 to %Qubit*))
  call void @__quantum__qis__mz__body(%Qubit* inttoptr (i64 1 to %Qubit*), %Result* inttoptr (i64 1 to %Result*))
  %1 = call i1 @__quantum__qis__read_result__body(%Result* null)
  br i1 %1, label %then1, label %else2

then1:                                            ; preds = %continue
  %2 = call i1 @__quantum__qis__read_result__body(%Result* inttoptr (i64 1 to %Result*))
  br i1 %2, label %then4, label %else5

else2:                                            ; preds = %continue
  br label %continue3

continue3:                                        ; preds = %else2, %continue6
  %3 = call i1 @__quantum__qis__read_result__body(%Result* null)
  br i1 %3, label %then7, label %else8

then4:                                            ; preds = %then1
  call void @__quantum__qis__x__body(%Qubit* null)
  call void @__quantum__qis__x__body(%Qubit* inttoptr (i64 1 to %Qubit*))
  br label %continue6

else5:                                            ; preds = %then1
  br label %continue6

continue6:                                        ; preds = %else5, %then4
  br label %continue3

then7:                                            ; preds = %continue3
  br label %continue9

else8:                                            ; preds = %continue3
  call void @__quantum__qis__x__body(%Qubit* null)
  br label %continue9

continue9:                                        ; preds = %else8, %then7
  %4 = call i1 @__quantum__qis__read_result__body(%Result* null)
  br i1 %4, label %then10, label %else11

then10:                                           ; preds = %continue9
  call void @__quantum__qis__z__body(%Qubit* null)
  br label %continue12

else11:                                           ; preds = %continue9
  call void @__quantum__qis__y__body(%Qubit* null)
  br label %continue12

continue12:                                       ; preds = %else11, %then10
  ret void
}

declare void @__quantum__qis__h__body(%Qubit*)

declare void @__quantum__qis__mz__body(%Qubit*, %Result* writeonly) #1

declare i1 @__quantum__qis__read_result__body(%Result*)

declare void @__quantum__qis__x__body(%Qubit*)

declare void @__quantum__qis__z__body(%Qubit*)

declare void @__quantum__qis__y__body(%Qubit*)

attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom" "required_num_qubits"="2" "required_num_results"="2" }
attributes #1 = { "irreversible" }

!llvm.module.flags = !{!0, !1, !2, !3}

!0 = !{i32 1, !"qir_major_version", i32 1}
!1 = !{i32 7, !"qir_minor_version", i32 0}
!2 = !{i32 1, !"dynamic_qubit_management", i1 false}
!3 = !{i32 1, !"dynamic_result_management", i1 false}
; ModuleID = 'while_test'
source_filename = "while_test"

%Qubit = type opaque
%Result = type opaque

define void @main() #0 {
A0:
  %0 = call i32 @get_int()
  %1 = add i32 0, %0
  br i1 0, label %B1, label %C2

B1:                                            
  %2 = add i32 1, %0
  br i1 0, label %B1, label %E4
  
C2:
  %3 = add i32 2, %0                                       
  br i1 0, label %E4, label %D3

D3:                                            
  %4 = add i32 3, %0
  br i1 0, label %C2, label %D3

E4:                                            
  %5 = add i32 4, %0
  ret void
}

declare i32 @get_int()

attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom"}

!llvm.module.flags = !{!0, !1, !2, !3}

!0 = !{i32 1, !"qir_major_version", i32 1}
!1 = !{i32 7, !"qir_minor_version", i32 0}
!2 = !{i32 1, !"dynamic_qubit_management", i1 true}
!3 = !{i32 1, !"dynamic_result_management", i1 true}

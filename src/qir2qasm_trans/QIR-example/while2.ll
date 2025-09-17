; ModuleID = 'dynamic_allocation'
source_filename = "dynamic_allocation"

%Qubit = type opaque
%Result = type opaque

define void @main() #0 {
A0:
  %0 = call i32 @get_int()
  br label %B1

B1:            
  %1 = add i32 1, %0      
  br label %C2

C2:         
  %2 = add i32 2, %0      
  br label %D3

D3:   
  %3 = add i32 3, %0
  br i1 0, label %B1, label %E4

E4:                                      
  %4 = add i32 4, %0
  br i1 0, label %F5, label %C2

F5:                      
  ret void
}

declare i32 @get_int()

attributes #0 = { "entry_point" "output_labeling_schema" "qir_profiles"="custom"}

!llvm.module.flags = !{!0, !1, !2, !3}

!0 = !{i32 1, !"qir_major_version", i32 1}
!1 = !{i32 7, !"qir_minor_version", i32 0}
!2 = !{i32 1, !"dynamic_qubit_management", i1 true}
!3 = !{i32 1, !"dynamic_result_management", i1 true}

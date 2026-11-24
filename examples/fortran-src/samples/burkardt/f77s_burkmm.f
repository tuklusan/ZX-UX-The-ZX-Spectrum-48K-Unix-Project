C     John Burkardt I4MAT_MM, from GNU LGPL i4lib/i4lib.f.
C     F77S numeric matrix multiplication, fixed leading extent two.
C     Source blob e0a7be6024463bc0d34ec036080d875ed66f4c31.
      PROGRAM BVMM
      INTEGER A(2,2),B(2,3),C(2,3),K,N
      DATA A/1,2,3,4/
      DATA B/1,2,3,4,5,6/
      K=2
      N=3
      CALL MATMUL(K,N,A,B,C)
      WRITE(6,10) C(1,1),C(2,2),C(1,3)
      N=1
      CALL MATMUL(K,N,A,B,C)
      WRITE(6,20) C(1,1)
   10 FORMAT(3I5)
   20 FORMAT(I5)
      CALL SLEEP(100)
      END
      SUBROUTINE MATMUL(K,N,A,B,C)
      INTEGER K,N,A(2,2),B(2,N),C(2,N),I,J,L,S
      DO 30 J=1,N
      DO 20 I=1,K
      S=0
      DO 10 L=1,K
      S=S+A(I,L)*B(L,J)
   10 CONTINUE
      C(I,J)=S
   20 CONTINUE
   30 CONTINUE
      RETURN
      END

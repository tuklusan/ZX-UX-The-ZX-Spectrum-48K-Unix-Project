C     John Burkardt LGPL R4VEC_SCALE strict F77S port.
C     Source: jburkardt-f77/r4lib/r4lib.f; GNU LGPL.
      PROGRAM SCLVEL
      REAL A(5),S
      INTEGER N
      DATA A/1.0,-2.0,3.0,4.0,-5.0/
      N=5
      S=2.0
      CALL RVSCL(N,S,A)
      WRITE(6,10) A(1),A(2),A(3),A(4),A(5)
      N=3
      S=-0.5
      CALL RVSCL(N,S,A(2))
      WRITE(6,10) A(1),A(2),A(3),A(4),A(5)
   10 FORMAT(5F8.2)
      CALL SLEEP(100)
      END
      SUBROUTINE RVSCL(N,S,A)
      INTEGER N,I
      REAL S,A(N)
      DO 20 I=1,N
      A(I)=S*A(I)
   20 CONTINUE
      RETURN
      END

C     John Burkardt LGPL R4VEC_SORT_BUBBLE_A strict F77S port.
C     Source: jburkardt-f77/r4lib/r4lib.f; GNU LGPL.
      PROGRAM RSORTP
      INTEGER N
      REAL A(5)
      DATA A/3.0,-1.0,4.0,2.0,0.0/
      N=3
      CALL RVSORT(N,A(2))
      WRITE(6,10) A(1),A(2),A(3),A(4),A(5)
      N=5
      CALL RVSORT(N,A)
      WRITE(6,10) A(1),A(2),A(3),A(4),A(5)
   10 FORMAT(5F8.2)
      CALL SLEEP(100)
      END
      SUBROUTINE RVSORT(N,A)
      INTEGER N,I,J,M,K
      REAL A(N),T
      M=N-1
      DO 30 I=1,M
      K=N-I
      DO 20 J=1,K
      IF (A(J).GT.A(J+1)) THEN
      T=A(J)
      A(J)=A(J+1)
      A(J+1)=T
      END IF
   20 CONTINUE
   30 CONTINUE
      RETURN
      END

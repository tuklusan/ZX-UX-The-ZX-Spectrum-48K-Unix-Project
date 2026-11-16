C     John Burkardt LGPL R4VEC_NORM_L1 strict F77S port.
C     Source: jburkardt-f77/r4lib/r4lib.f; GNU LGPL.
      PROGRAM BLONEM
      REAL A(5),R
      INTEGER N
      DATA A/-2.5,3.0,0.0,-4.5,2.0/
      N=5
      CALL RVNML1(N,A,R)
      WRITE(6,10) R
      N=3
      CALL RVNML1(N,A(2),R)
      WRITE(6,10) R
   10 FORMAT(F8.2)
      CALL SLEEP(100)
      END
      SUBROUTINE RVNML1(N,A,R)
      INTEGER N,I
      REAL A(N),R
      R=0.0
      DO 20 I=1,N
      R=R+ABS(A(I))
   20 CONTINUE
      RETURN
      END

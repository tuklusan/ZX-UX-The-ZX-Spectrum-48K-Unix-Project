C     John Burkardt LGPL R4VEC_NORM_L2 strict F77S port.
C     Source: jburkardt-f77/r4lib/r4lib.f; GNU LGPL.
      PROGRAM NORML2
      REAL A(5),R
      INTEGER N
      DATA A/3.0,4.0,0.0,0.0,0.0/
      N=5
      CALL RVNML2(N,A,R)
      WRITE(6,10) R
      N=4
      CALL RVNML2(N,A(2),R)
      WRITE(6,10) R
      R=SQRT(9.0)
      WRITE(6,10) R
      R=SQRT(2.0)
      WRITE(6,10) R
      R=SQRT(0.25)
      WRITE(6,10) R
      R=SQRT(10000.0)
      WRITE(6,10) R
      R=SQRT(0.0001)
      WRITE(6,10) R
   10 FORMAT(F8.2)
      CALL SLEEP(100)
      END
      SUBROUTINE RVNML2(N,A,R)
      INTEGER N,I
      REAL A(N),R
      R=0.0
      DO 20 I=1,N
      R=R+A(I)*A(I)
   20 CONTINUE
      R=SQRT(R)
      RETURN
      END

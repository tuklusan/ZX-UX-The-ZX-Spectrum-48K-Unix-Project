C     John Burkardt LGPL R4VEC_VARIANCE strict F77S port.
C     Source: jburkardt-f77/r4lib/r4lib.f; GNU LGPL.
      PROGRAM VARIAB
      REAL A(5),R
      INTEGER N
      DATA A/1.0,2.0,3.0,4.0,5.0/
      N=5
      CALL RVVARI(N,A,R)
      WRITE(6,10) R
      N=3
      CALL RVVARI(N,A(2),R)
      WRITE(6,10) R
      N=1
      CALL RVVARI(N,A,R)
      WRITE(6,10) R
   10 FORMAT(F8.2)
      CALL SLEEP(100)
      END
      SUBROUTINE RVVARI(N,A,R)
      INTEGER N,I
      REAL A(N),R,AVER
      AVER=0.0
      DO 20 I=1,N
      AVER=AVER+A(I)
   20 CONTINUE
      AVER=AVER/N
      R=0.0
      DO 30 I=1,N
      R=R+(A(I)-AVER)*(A(I)-AVER)
   30 CONTINUE
      IF (N.LE.1) GO TO 40
      R=R/(N-1)
      RETURN
   40 R=0.0
      RETURN
      END

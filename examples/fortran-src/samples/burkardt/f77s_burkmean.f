C     LGPL Burkardt R4VEC_MEAN, adapted to strict F77S.
C     Source: jburkardt-f77/r4lib/r4lib.f, R4VEC_MEAN.
      PROGRAM BMEAN
      REAL A(4),B(3),R
      INTEGER N
      DATA A/1.0,2.0,3.0,4.0/
      DATA B/-4.0,0.0,4.0/
      N=4
      CALL RVMEAN(N,A,R)
      WRITE(6,10) R
      N=3
      CALL RVMEAN(N,B,R)
      WRITE(6,10) R
   10 FORMAT(F8.2)
      CALL SLEEP(100)
      END
      SUBROUTINE RVMEAN(N,A,M)
      INTEGER N,I
      REAL A(N),M
      M=0.0
      DO 20 I=1,N
      M=M+A(I)
   20 CONTINUE
      M=M/N
      RETURN
      END

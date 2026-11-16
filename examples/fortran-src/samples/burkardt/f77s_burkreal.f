C     John Burkardt LGPL R4VEC_DOT_PRODUCT port to F77S.
C     Source: jburkardt-f77/r4lib/r4lib.f; GNU LGPL.
      PROGRAM BREAL
      REAL X(5),Y(5),S
      INTEGER N
      DATA X/1.0,2.0,3.0,4.0,5.0/
      DATA Y/0.5,1.0,1.5,2.0,2.5/
      N=5
      CALL RVDOTP(N,X,Y,S)
      WRITE(6,10) S
      N=4
      CALL RVDOTP(N,X(2),Y(2),S)
      WRITE(6,10) S
   10 FORMAT(F8.2)
      CALL SLEEP(100)
      END
      SUBROUTINE RVDOTP(N,X,Y,S)
      INTEGER N,I
      REAL X(N),Y(N),S
      S=0.0
      DO 20 I=1,N
      S=S+X(I)*Y(I)
   20 CONTINUE
      RETURN
      END

C     John Burkardt LGPL I4VEC_DOT_PRODUCT F77S adaptation.
C     Source i4lib/i4lib.f Git blob e0a7be6024463bc0d34e
C     c036080d875ed66f4c31. By-reference result DOTVEC.
      PROGRAM BDOT
      INTEGER X(5),Y(5),N,R
      DATA X/1,2,3,4,5/
      DATA Y/5,4,3,2,1/
      N=5
      CALL DOTVEC(N,X,Y,R)
      WRITE(6,10) R
      N=4
      CALL DOTVEC(N,X(2),Y(2),R)
      WRITE(6,10) R
   10 FORMAT(I4)
      CALL SLEEP(100)
      END
      SUBROUTINE DOTVEC(N,X,Y,R)
      INTEGER N,X(N),Y(N),R,I
      R=0
      DO 20 I=1,N
      R=R+X(I)*Y(I)
   20 CONTINUE
      RETURN
      END

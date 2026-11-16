C     John Burkardt LGPL I4VEC_CUM/MIN/MAX F77S adaptations.
C     From i4lib/i4lib.f, source blob e0a7be6024463bc0d34e
C     c036080d875ed66f4c31. Labelled DO, A(N) and C(N).
      PROGRAM BCUM
      INTEGER A(5),C(5),N,IMIN,IMAX
      DATA A/3,-1,4,-2,5/
      N=5
      CALL CUMVEC(N,A,C)
      CALL MINVEC(N,A,IMIN)
      CALL MAXVEC(N,A,IMAX)
      WRITE(6,10) C(1),C(3),C(5),IMIN,IMAX
      N=3
      CALL CUMVEC(N,A,C)
      CALL MINVEC(N,A,IMIN)
      CALL MAXVEC(N,A,IMAX)
      WRITE(6,20) C(3),IMIN,IMAX
   10 FORMAT(5I4)
   20 FORMAT(3I4)
      CALL SLEEP(100)
      END
      SUBROUTINE CUMVEC(N,A,C)
      INTEGER N,A(N),C(N),I
      C(1)=A(1)
      DO 10 I=2,N
      C(I)=C(I-1)+A(I)
   10 CONTINUE
      RETURN
      END
      SUBROUTINE MINVEC(N,A,AMIN)
      INTEGER N,A(N),AMIN,I
      AMIN=A(1)
      DO 10 I=2,N
      IF (A(I).LT.AMIN) AMIN=A(I)
   10 CONTINUE
      RETURN
      END
      SUBROUTINE MAXVEC(N,A,AMAX)
      INTEGER N,A(N),AMAX,I
      AMAX=A(1)
      DO 10 I=2,N
      IF (A(I).GT.AMAX) AMAX=A(I)
   10 CONTINUE
      RETURN
      END

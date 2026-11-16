C     Adapted from John Burkardt i4lib/i4lib.f GNU LGPL.
C     I4VEC_REVERSE (25 June 2009) and I4VEC_SUM (3 Jan 2007).
C     Source https://github.com/johannesgerer/jburkardt-f77
C     Git blob e0a7be6024463bc0d34ec036080d875ed66f4c31.
C     F77S changes: named DO, fixed dimension, F77S names,
C     I4VEC_SUM adapted to subroutine output argument.
      PROGRAM BVEC
      INTEGER A(5),N,TOT
      DATA A/11,12,13,14,15/
      N=5
      CALL REVERS(N,A)
      WRITE(6,30) A(1),A(3),A(5)
      CALL VECSUM(N,A,TOT)
      WRITE(6,40) TOT
   30 FORMAT(3I4)
   40 FORMAT(I4)
      CALL SLEEP(100)
      END
      SUBROUTINE REVERS(N,A)
      INTEGER N,A(5),I,T,HALF,J
      HALF=N/2
      DO 10 I=1,HALF
      J=N+1-I
      T=A(I)
      A(I)=A(J)
      A(J)=T
   10 CONTINUE
      RETURN
      END
      SUBROUTINE VECSUM(N,A,TOT)
      INTEGER N,A(5),TOT,I
      TOT=0
      DO 20 I=1,N
      TOT=TOT+A(I)
   20 CONTINUE
      RETURN
      END

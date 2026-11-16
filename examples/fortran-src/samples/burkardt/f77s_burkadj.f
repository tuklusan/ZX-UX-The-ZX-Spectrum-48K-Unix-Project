C     John Burkardt I4VEC_REVERSE and I4VEC_SUM, GNU LGPL.
C     Generalized F77S A(N) dummy array bound, tests N=5/7.
C     Source: johannesgerer/jburkardt-f77 i4lib/i4lib.f
C     Git blob e0a7be6024463bc0d34ec036080d875ed66f4c31.
      PROGRAM BVADJ
      INTEGER A(7),N,S
      DATA A/1,2,3,4,5,6,7/
      N=5
      CALL REVRSE(N,A)
      CALL SUMVEC(N,A,S)
      WRITE(6,10) A(1),A(5),S
      N=7
      CALL SUMVEC(N,A,S)
      WRITE(6,20) S
   10 FORMAT(3I4)
   20 FORMAT(I4)
      CALL SLEEP(100)
      END
      SUBROUTINE REVRSE(N,A)
      INTEGER N,A(N),I,J,T,H
      H=N/2
      DO 10 I=1,H
      J=N+1-I
      T=A(I)
      A(I)=A(J)
      A(J)=T
   10 CONTINUE
      RETURN
      END
      SUBROUTINE SUMVEC(N,A,S)
      INTEGER N,A(N),S,I
      S=0
      DO 20 I=1,N
      S=S+A(I)
   20 CONTINUE
      RETURN
      END

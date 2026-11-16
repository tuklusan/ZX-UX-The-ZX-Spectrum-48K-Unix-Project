C     Burkardt LGPL I4_GCD algorithm adapted to strict F77S.
C     Integer array GCD with adjustable and element-tail dummies.
      PROGRAM BGCD
      INTEGER A(5),B(4),N,G
      DATA A/84,30,-42,56,14/
      DATA B/18,24,30,42/
      N=5
      CALL GCDARR(N,A,G)
      WRITE(6,10) G
      N=4
      CALL GCDARR(N,B,G)
      WRITE(6,10) G
      N=3
      CALL GCDARR(N,A(3),G)
      WRITE(6,10) G
   10 FORMAT(I4)
      CALL SLEEP(100)
      END
      SUBROUTINE GCDARR(N,A,G)
      INTEGER N,A(N),G,I,H,T
      G=0
      DO 20 I=1,N
      T=A(I)
      CALL GCDVAL(G,T,H)
      G=H
   20 CONTINUE
      RETURN
      END
      SUBROUTINE GCDVAL(I,J,G)
      INTEGER I,J,G,A,B,T
      A=I
      B=J
      IF (A.LT.0) A=-A
      IF (B.LT.0) B=-B
   30 IF (B.EQ.0) GO TO 40
      T=MOD(A,B)
      A=B
      B=T
      GO TO 30
   40 G=A
      RETURN
      END

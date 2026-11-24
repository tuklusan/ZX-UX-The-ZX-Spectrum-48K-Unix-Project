      PROGRAM NCHOL
      INTEGER V,N,I,J,K,JM
      REAL A(7,7),B(7,7),C(7,7),S,E
      DO 100 V=1,2
      N=3+2*V
      DO 20 J=1,N
      DO 20 I=1,N
      A(I,J)=0.0
      C(I,J)=0.0
      IF (I.GE.J) A(I,J)=0.025*(I-J)
      IF (I.EQ.J) A(I,J)=2.0+0.1*I
   20 CONTINUE
      DO 40 J=1,N
      DO 40 I=1,N
      S=0.0
      DO 30 K=1,N
      S=S+A(I,K)*A(J,K)
   30 CONTINUE
      B(I,J)=S
   40 CONTINUE
      DO 70 J=1,N
      DO 70 I=J,N
      S=B(I,J)
      JM=J-1
      DO 50 K=1,JM
      S=S-C(I,K)*C(J,K)
   50 CONTINUE
      IF (I.EQ.J) THEN
      C(I,J)=SQRT(S)
      ELSE
      C(I,J)=S/C(J,J)
      ENDIF
   70 CONTINUE
      E=0.0
      DO 80 J=1,N
      DO 80 I=J,N
      E=MAX(E,ABS(C(I,J)-A(I,J)))
   80 CONTINUE
      WRITE(6,900) V,N,E
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('CHOLESKY ',2I3,F11.5)
      END

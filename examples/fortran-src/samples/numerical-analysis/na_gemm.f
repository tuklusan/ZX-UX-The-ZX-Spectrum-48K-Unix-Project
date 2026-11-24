      PROGRAM NGEMM
      INTEGER V,N,I,J,K
      REAL A(15,15),B(15,15),C(15,15),S,X
      DO 100 V=1,2
      N=7+4*V
      DO 20 J=1,N
      DO 20 I=1,N
      A(I,J)=0.1+0.02*(I-J)
      B(I,J)=0.01*(I+J)
      IF (I.EQ.J) B(I,J)=1.0+0.01*I
      C(I,J)=0.0
   20 CONTINUE
      DO 40 J=1,N
      DO 40 K=1,N
      DO 40 I=1,N
      C(I,J)=C(I,J)+A(I,K)*B(K,J)
   40 CONTINUE
      S=0.0
      DO 50 I=1,N
      S=S+C(I,I)
   50 CONTINUE
      X=C(N,N)
      WRITE(6,900) V,N,S,C(1,1),X
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('GEMM ',2I3,3F10.4)
      END

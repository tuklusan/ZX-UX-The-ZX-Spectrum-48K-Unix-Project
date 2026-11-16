      PROGRAM NMINI
      INTEGER V,N,I,J,K,P,L,NM,KP,IP
      REAL A(8,8),B(8),C(8),E,BIG,T,M
      DO 100 V=1,2
      N=2+3*V
      DO 20 J=1,N
      C(J)=0.125*J
      DO 20 I=1,N
      A(I,J)=0.05*(I+J)
      IF (I.EQ.J) A(I,J)=5.0+0.2*I
   20 CONTINUE
      A(1,1)=0.01
      A(2,1)=2.0
      DO 40 I=1,N
      B(I)=0.0
      DO 30 J=1,N
      B(I)=B(I)+A(I,J)*C(J)
   30 CONTINUE
   40 CONTINUE
      NM=N-1
      DO 70 K=1,NM
      KP=K+1
      P=K
      BIG=ABS(A(K,K))
      DO 50 I=KP,N
      IF (ABS(A(I,K)).GT.BIG) THEN
      BIG=ABS(A(I,K))
      P=I
      ENDIF
   50 CONTINUE
      DO 60 J=1,N
      T=A(P,J)
      A(P,J)=A(K,J)
      A(K,J)=T
   60 CONTINUE
      T=B(P)
      B(P)=B(K)
      B(K)=T
      DO 70 I=KP,N
      M=A(I,K)/A(K,K)
      DO 65 J=KP,N
      A(I,J)=A(I,J)-M*A(K,J)
   65 CONTINUE
      B(I)=B(I)-M*B(K)
      A(I,K)=0.0
   70 CONTINUE
      DO 90 K=1,N
      I=N+1-K
      T=B(I)
      IP=I+1
      DO 80 J=IP,N
      T=T-A(I,J)*B(J)
   80 CONTINUE
      B(I)=T/A(I,I)
   90 CONTINUE
      E=0.0
      DO 95 I=1,N
      E=MAX(E,ABS(B(I)-C(I)))
   95 CONTINUE
      WRITE(6,900) V,N,E,B(1)
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('MINILIN ',2I3,2F11.5)
      END

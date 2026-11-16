      PROGRAM NPOLY
      INTEGER V,N,M,I,J,K,P,L,NM,KP,IP
      REAL A(4,4),B(4),C(4),D(7),X,Y,T,H,E
      DO 100 V=1,2
      M=2+V
      N=7+2*V
      DO 20 I=1,M
      B(I)=0.0
      C(I)=0.0
      DO 20 J=1,M
      A(I,J)=0.0
   20 CONTINUE
      C(1)=1.0
      C(2)=0.5
      C(3)=-0.25
      IF (V.EQ.2) THEN
      C(1)=0.25
      C(2)=-0.4
      C(3)=0.3
      C(4)=-0.1
      ENDIF
      DO 50 K=1,N
      X=FLOAT(2*K-N-1)/FLOAT(N-1)
      D(1)=1.0
      DO 30 I=2,7
      D(I)=D(I-1)*X
   30 CONTINUE
      Y=0.0
      DO 35 I=1,M
      Y=Y+C(I)*D(I)
   35 CONTINUE
      DO 40 I=1,M
      B(I)=B(I)+Y*D(I)
      DO 40 J=1,M
      A(I,J)=A(I,J)+D(I+J-1)
   40 CONTINUE
   50 CONTINUE
      NM=M-1
      DO 80 K=1,NM
      KP=K+1
      P=K
      H=ABS(A(K,K))
      DO 60 I=KP,M
      IF (ABS(A(I,K)).GT.H) THEN
      H=ABS(A(I,K))
      P=I
      ENDIF
   60 CONTINUE
      DO 70 J=1,M
      T=A(K,J)
      A(K,J)=A(P,J)
      A(P,J)=T
   70 CONTINUE
      T=B(K)
      B(K)=B(P)
      B(P)=T
      DO 80 I=KP,M
      H=A(I,K)/A(K,K)
      DO 75 J=KP,M
      A(I,J)=A(I,J)-H*A(K,J)
   75 CONTINUE
      B(I)=B(I)-H*B(K)
   80 CONTINUE
      DO 95 K=1,M
      I=M+1-K
      T=B(I)
      IP=I+1
      DO 90 J=IP,M
      T=T-A(I,J)*B(J)
   90 CONTINUE
      B(I)=T/A(I,I)
   95 CONTINUE
      E=0.0
      DO 97 I=1,M
      E=MAX(E,ABS(B(I)-C(I)))
   97 CONTINUE
      T=B(M)
      WRITE(6,900) V,N,M,E,B(1),T
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('POLYFIT ',3I3,3F10.5)
      END

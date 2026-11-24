      PROGRAM NTHOMA
      INTEGER V,N,I,NM
      REAL A(20),B(20),C(20),D(20),E(20),T,R
      DO 100 V=1,2
      N=10*V
      DO 20 I=1,N
      A(I)=-1.0
      B(I)=4.0
      C(I)=-1.0
      E(I)=1.0+0.025*I
      D(I)=4.0*E(I)
      IF (I.GT.1) D(I)=D(I)-(1.0+0.025*(I-1))
      IF (I.LT.N) D(I)=D(I)-(1.0+0.025*(I+1))
   20 CONTINUE
      DO 30 I=2,N
      T=A(I)/B(I-1)
      B(I)=B(I)-T*C(I-1)
      D(I)=D(I)-T*D(I-1)
   30 CONTINUE
      D(N)=D(N)/B(N)
      NM=N-1
      DO 40 I=NM,1,-1
      D(I)=(D(I)-C(I)*D(I+1))/B(I)
   40 CONTINUE
      R=0.0
      DO 50 I=1,N
      R=MAX(R,ABS(D(I)-E(I)))
   50 CONTINUE
      T=D(N)
      WRITE(6,900) V,N,R,D(1),T
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('THOMAS ',2I3,3F10.5)
      END

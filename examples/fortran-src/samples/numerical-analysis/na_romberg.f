      PROGRAM NROMB
      INTEGER V,I,J,K,N,L
      REAL A(7,7),H,S,X,Y,F,Q
      DO 100 V=1,2
      A(1,1)=(1.0+EXP(1.0))/2.0
      IF (V.EQ.2) A(1,1)=3.0
      N=1
      H=1.0
      DO 40 K=2,6
      H=H/2.0
      S=0.0
      DO 20 I=1,N
      X=(2*I-1)*H
      Y=EXP(X)
      IF (V.EQ.2) Y=4.0/(1.0+X*X)
      S=S+Y
   20 CONTINUE
      A(K,1)=A(K-1,1)/2.0+H*S
      F=1.0
      DO 30 J=2,K
      F=F*4.0
      A(K,J)=A(K,J-1)+(A(K,J-1)-A(K-1,J-1))/(F-1.0)
   30 CONTINUE
      N=N*2
   40 CONTINUE
      WRITE(6,900) V,N,A(6,6)
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('ROMBERG ',2I4,F12.6)
      END

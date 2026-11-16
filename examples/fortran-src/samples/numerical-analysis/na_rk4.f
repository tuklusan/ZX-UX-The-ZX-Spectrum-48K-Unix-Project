      PROGRAM NRKFO
      INTEGER V,I,N
      REAL H,Y,Z,K1,K2,K3,K4
      DO 100 V=1,2
      N=10*V
      H=1.0/N
      Y=1.0
      IF (V.EQ.2) Y=0.25
      DO 20 I=1,N
      K1=-2.0*Y
      IF (V.EQ.2) K1=Y*(1.0-Y)
      Z=Y+H*K1/2.0
      K2=-2.0*Z
      IF (V.EQ.2) K2=Z*(1.0-Z)
      Z=Y+H*K2/2.0
      K3=-2.0*Z
      IF (V.EQ.2) K3=Z*(1.0-Z)
      Z=Y+H*K3
      K4=-2.0*Z
      IF (V.EQ.2) K4=Z*(1.0-Z)
      Y=Y+H*(K1+2.0*K2+2.0*K3+K4)/6.0
   20 CONTINUE
      WRITE(6,900) V,N,Y
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('RK4 ',2I4,F12.6)
      END

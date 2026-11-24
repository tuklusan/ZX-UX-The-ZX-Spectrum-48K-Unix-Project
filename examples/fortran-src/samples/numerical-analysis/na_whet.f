      PROGRAM NWHET
      INTEGER V,I,J,K,N
      REAL X1,X2,X3,X4,T,Y,Z,S
      DO 100 V=1,2
      N=10*V
      T=0.5
      X1=1.0
      X2=-1.0
      X3=-1.0
      X4=-1.0
      DO 30 I=1,N
      DO 20 J=1,12
      X1=(X1+X2+X3-X4)*T
      X2=(X1+X2-X3+X4)*T
      X3=(X1-X2+X3+X4)*T
      X4=(-X1+X2+X3+X4)*T
   20 CONTINUE
   30 CONTINUE
      Y=0.5
      Z=0.25
      DO 40 I=1,N
      Y=Y+0.01*Z
      Z=(Z+Y)/2.0
      Y=Y/(1.0+0.0001*Z)
   40 CONTINUE
      S=0.0
      DO 50 K=1,N
      S=S+SQRT(1.0+0.01*K)
   50 CONTINUE
      WRITE(6,900) V,X1,X2,Y,S
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('WHET ',I3,4F11.5)
      END

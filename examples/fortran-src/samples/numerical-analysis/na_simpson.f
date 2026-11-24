      PROGRAM NSIMP
      INTEGER V,I,N,NM
      REAL H,S,X,Y,R
      DO 100 V=1,2
      N=100*V
      H=1.0/N
      S=0.0
      NM=N-1
      DO 20 I=1,NM
      X=I*H
      Y=EXP(X)
      IF (V.EQ.2) Y=4.0/(1.0+X*X)
      IF (MOD(I,2).EQ.0) THEN
      S=S+2.0*Y
      ELSE
      S=S+4.0*Y
      ENDIF
   20 CONTINUE
      R=(S+1.0+EXP(1.0))*H/3.0
      IF (V.EQ.2) R=(S+6.0)*H/3.0
      WRITE(6,900) V,N,R
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('SIMPSON ',2I4,F12.6)
      END

      PROGRAM NSQUAR
      INTEGER V,I,J,N
      REAL X,S,T
      DO 100 V=1,2
      N=100*V
      S=0.0
      T=1.0-0.00002*V
      DO 30 I=1,N
      X=T
      DO 20 J=1,16
      X=X*X
   20 CONTINUE
      S=S+X
   30 CONTINUE
      WRITE(6,900) V,N,S,X
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('SQUARE ',2I4,2F12.5)
      END

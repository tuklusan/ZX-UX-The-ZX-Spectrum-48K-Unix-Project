      PROGRAM NEULER
      INTEGER V,I,N
      REAL Y,H
      DO 100 V=1,2
      N=10*V
      H=1.0/N
      Y=1.0
      DO 20 I=1,N
      Y=Y-H*Y
   20 CONTINUE
      H=ABS(Y-0.3678794)
      WRITE(6,900) V,N,Y,H
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('EULER ',2I4,2F10.5)
      END

      PROGRAM NNEW
      INTEGER V,I
      REAL X,F,D
      DO 100 V=1,2
      X=1.5
      DO 20 I=1,16
      F=X*X-2.0
      D=2.0*X
      IF (V.EQ.2) THEN
      F=X*X*X-X-2.0
      D=3.0*X*X-1.0
      ENDIF
      IF (ABS(D).LT.0.00001) GO TO 25
      X=X-F/D
   20 CONTINUE
   25 CONTINUE
      F=X*X-2.0
      IF (V.EQ.2) F=X*X*X-X-2.0
      WRITE(6,900) V,X,F
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('NEWTON ',I3,2F11.5)
      END

      PROGRAM NBRENT
      INTEGER V,I
      REAL A,B,C,FA,FB,FC,R
      DO 100 V=1,2
      A=1.0
      B=2.0
      FA=A*A-2.0
      FB=B*B-2.0
      IF (V.EQ.2) THEN
      FA=A*A*A-A-2.0
      FB=B*B*B-B-2.0
      ENDIF
      DO 30 I=1,28
      C=(A+B)/2.0
      IF (ABS(FB-FA).GT.0.000001) THEN
      R=B-FB*(B-A)/(FB-FA)
      IF (R.GT.A+0.00001.AND.R.LT.B-0.00001) C=R
      ENDIF
      FC=C*C-2.0
      IF (V.EQ.2) FC=C*C*C-C-2.0
      IF (FA*FC.LE.0.0) THEN
      B=C
      FB=FC
      ELSE
      A=C
      FA=FC
      ENDIF
   30 CONTINUE
      C=(A+B)/2.0
      FC=C*C-2.0
      IF (V.EQ.2) FC=C*C*C-C-2.0
      WRITE(6,900) V,C,FC
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('BRENT ',I2,2F11.5)
      END

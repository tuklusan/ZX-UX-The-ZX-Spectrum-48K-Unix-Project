      PROGRAM NBISEC
      INTEGER V,I
      REAL A,B,M,FA,FM,R
      DO 100 V=1,2
      A=1.0
      B=2.0
      DO 20 I=1,28
      M=(A+B)/2.0
      FA=A*A-2.0
      FM=M*M-2.0
      IF (V.EQ.2) THEN
      FA=A*A*A-A-2.0
      FM=M*M*M-M-2.0
      ENDIF
      IF (FA*FM.LT.0.0) THEN
      B=M
      ELSE
      A=M
      ENDIF
   20 CONTINUE
      M=(A+B)/2.0
      R=M*M-2.0
      IF (V.EQ.2) R=M*M*M-M-2.0
      WRITE(6,900) V,M,R
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('BISECT ',I2,2F11.5)
      END

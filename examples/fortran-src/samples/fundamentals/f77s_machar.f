C     BASIC REAL RADIX AND ROUNDING PROBE, WITH LOOP GUARDS.
      PROGRAM MACHAR
      INTEGER I,IBETA,IT,NDIG
      REAL A,B,C,D,EPS,ENEG,X,Y,BASE
      A=1.0
      DO 10 I=1,100
         B=A+1.0
         C=B-A
         IF (C .NE. 1.0) GO TO 20
         A=A*2.0
   10 CONTINUE
   20 CONTINUE
      B=1.0
      DO 30 I=1,100
         C=A+B
         D=C-A
         IF (D .NE. 0.0) GO TO 40
         B=B*2.0
   30 CONTINUE
   40 CONTINUE
      IBETA=INT(D+0.25)
      IF (IBETA .LT. 2) IBETA=2
      BASE=IBETA
      EPS=1.0
      NDIG=0
      DO 50 I=1,100
         X=EPS/BASE
         Y=1.0+X
         IF (Y .EQ. 1.0) GO TO 60
         EPS=X
         NDIG=NDIG+1
   50 CONTINUE
   60 CONTINUE
      ENEG=1.0
      DO 70 I=1,100
         X=ENEG/BASE
         Y=1.0-X
         IF (Y .EQ. 1.0) GO TO 80
         ENEG=X
   70 CONTINUE
   80 CONTINUE
      IT=NDIG+1
      WRITE(6,100) IBETA,IT,EPS,ENEG
  100 FORMAT('MACHAR ',2I6,2(1X,E14.6))
      CALL SLEEP(100)
      END

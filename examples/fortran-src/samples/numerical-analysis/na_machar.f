      PROGRAM NMACH
      INTEGER I,BETA,DIG
      REAL A,B,C,D,EPS,ENEG,X,Y
      A=1.0
      DO 10 I=1,60
      B=A+1.0
      C=B-A
      IF (C.NE.1.0) GO TO 20
      A=A*2.0
   10 CONTINUE
   20 CONTINUE
      B=1.0
      DO 30 I=1,60
      C=A+B
      D=C-A
      IF (D.NE.0.0) GO TO 40
      B=B*2.0
   30 CONTINUE
   40 CONTINUE
      BETA=INT(D+0.25)
      IF (BETA.LT.2) BETA=2
      EPS=1.0
      DIG=0
      DO 50 I=1,60
      X=EPS/BETA
      Y=1.0+X
      IF (Y.EQ.1.0) GO TO 60
      EPS=X
      DIG=DIG+1
   50 CONTINUE
   60 CONTINUE
      ENEG=1.0
      DO 70 I=1,60
      X=ENEG/BETA
      Y=1.0-X
      IF (Y.EQ.1.0) GO TO 80
      ENEG=X
   70 CONTINUE
   80 CONTINUE
      DIG=DIG+1
      WRITE(6,900) BETA,DIG,EPS,ENEG
      CALL SLEEP(100)
  900 FORMAT('MACHAR ',2I4,2E13.5)
      END

      PROGRAM NGAUSS
      INTEGER V,I
      REAL X(4),W(4),A,B,S,F,G
      DATA X/0.18343464,0.52553241,0.79666648,0.96028986/
      DATA W/0.36268378,0.31370665,0.22238103,0.10122854/
      DO 100 V=1,2
      S=0.0
      DO 20 I=1,4
      A=(1.0-X(I))/2.0
      B=(1.0+X(I))/2.0
      F=EXP(A)
      G=EXP(B)
      IF (V.EQ.2) THEN
      F=4.0/(1.0+A*A)
      G=4.0/(1.0+B*B)
      ENDIF
      S=S+W(I)*(F+G)/2.0
   20 CONTINUE
      WRITE(6,900) V,S
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('GAUSS ',I3,F12.6)
      END

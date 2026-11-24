      PROGRAM NFFT
      INTEGER V,I,J,K,M,L,H,P,Q,N
      REAL A(64),B(64),R,T,U,X,Y,W,Z,E,C,S
      N=64
      DO 100 V=1,3
      DO 10 I=1,N
      A(I)=0.0
      B(I)=0.0
   10 CONTINUE
      A(1)=1.0
      IF (V.EQ.2) A(33)=1.0
      IF (V.EQ.3) THEN
      A(1)=0.0
      A(2)=1.0
      ENDIF
      J=1
      DO 30 I=1,N
      IF (I.LT.J) THEN
      T=A(I)
      A(I)=A(J)
      A(J)=T
      T=B(I)
      B(I)=B(J)
      B(J)=T
      ENDIF
      M=N/2
   20 IF (M.GE.2 .AND. J.GT.M) THEN
      J=J-M
      M=M/2
      GO TO 20
      ENDIF
      J=J+M
   30 CONTINUE
      L=2
      DO 70 P=1,6
      H=L/2
      C=COS(-6.2831853/L)
      S=SIN(-6.2831853/L)
      W=1.0
      Z=0.0
      DO 60 J=1,H
      DO 50 I=J,N,L
      K=I+H
      R=W*A(K)-Z*B(K)
      T=W*B(K)+Z*A(K)
      U=A(I)
      X=B(I)
      A(K)=U-R
      B(K)=X-T
      A(I)=U+R
      B(I)=X+T
   50 CONTINUE
      Y=W*C-Z*S
      Z=W*S+Z*C
      W=Y
   60 CONTINUE
      L=L*2
   70 CONTINUE
      E=0.0
      DO 80 I=1,N
      R=1.0
      IF (V.EQ.2) THEN
      R=0.0
      IF (MOD(I,2).EQ.1) R=2.0
      ENDIF
      IF (V.EQ.3) R=COS(-6.2831853*(I-1)/64.0)
      T=0.0
      IF (V.EQ.3) T=SIN(-6.2831853*(I-1)/64.0)
      E=MAX(E,ABS(A(I)-R)+ABS(B(I)-T))
   80 CONTINUE
      WRITE(6,900) V,N,E,A(1),A(2)
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('FFT ',2I3,3F10.4)
      END

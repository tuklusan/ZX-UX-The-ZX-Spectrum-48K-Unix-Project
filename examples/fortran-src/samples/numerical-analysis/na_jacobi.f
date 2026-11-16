      PROGRAM NJACOB
      INTEGER V,N,I,J,K,T,NM,IT
      REAL A(16,16),B(16,16),E,X
      DO 100 V=1,2
      N=8*V
      DO 20 J=1,N
      DO 20 I=1,N
      A(I,J)=0.0
      B(I,J)=0.0
      IF (J.EQ.N) THEN
      A(I,J)=1.0
      B(I,J)=1.0
      ENDIF
   20 CONTINUE
      IT=20*V
      NM=N-1
      DO 60 K=1,IT
      E=0.0
      DO 40 J=2,NM
      DO 40 I=2,NM
      X=(A(I-1,J)+A(I+1,J)+A(I,J-1)+A(I,J+1))/4.0
      E=MAX(E,ABS(X-A(I,J)))
      B(I,J)=X
   40 CONTINUE
      DO 50 J=2,NM
      DO 50 I=2,NM
      A(I,J)=B(I,J)
   50 CONTINUE
   60 CONTINUE
      T=N/2
      X=A(T,T)
      WRITE(6,900) V,N,X,E
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('JACOBI ',2I3,2F10.5)
      END

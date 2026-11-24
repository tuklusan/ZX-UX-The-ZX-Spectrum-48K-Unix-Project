      PROGRAM NLCG
      INTEGER V,I,S,Q,R,T,C
      WRITE(6,900) MOD(-13,5)
      DO 100 V=1,3
      S=1
      IF (V.EQ.2) S=12345
      IF (V.EQ.3) S=32748
      C=0
      DO 20 I=1,64
      Q=S/436
      R=MOD(S,436)
      T=75*R-49*Q
      IF (T.LE.0) T=T+32749
      S=T
      C=MOD(C+MOD(S,97),997)
   20 CONTINUE
      WRITE(6,901) V,S,C
  100 CONTINUE
      CALL SLEEP(100)
  900 FORMAT('LCG FORTRAN-MOD ',I4)
  901 FORMAT('LCG ',3I8)
      END

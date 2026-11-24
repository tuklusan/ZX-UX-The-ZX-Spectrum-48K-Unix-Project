C     LGPL Burkardt R4VEC_MIN / R4VEC_MAX F77S port.
C     Source: jburkardt-f77/r4lib/r4lib.f; LGPL applies.
      PROGRAM BMINMX
      REAL A(5),B(4),LO,HI
      INTEGER N
      DATA A/-1.0,2.5,0.0,4.0,-3.25/
      DATA B/1.25,-2.5,3.75,2.0/
      N=5
      CALL RVSMIN(N,A,LO)
      CALL RVSMAX(N,A,HI)
      WRITE(6,10) LO,HI
      N=3
      CALL RVSMIN(N,B(2),LO)
      CALL RVSMAX(N,B(2),HI)
      WRITE(6,10) LO,HI
   10 FORMAT(2F8.2)
      CALL SLEEP(100)
      END
      SUBROUTINE RVSMIN(N,A,VALUE)
      INTEGER N,I
      REAL A(N),VALUE
      VALUE=A(1)
      DO 20 I=2,N
      IF (A(I).LT.VALUE) VALUE=A(I)
   20 CONTINUE
      RETURN
      END
      SUBROUTINE RVSMAX(N,A,VALUE)
      INTEGER N,I
      REAL A(N),VALUE
      VALUE=A(1)
      DO 30 I=2,N
      IF (A(I).GT.VALUE) VALUE=A(I)
   30 CONTINUE
      RETURN
      END

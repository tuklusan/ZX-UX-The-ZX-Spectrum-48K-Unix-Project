C     John Burkardt LGPL R4VEC_COPY strict F77S adaptation.
C     Source: jburkardt-f77/r4lib/r4lib.f; GNU LGPL.
      PROGRAM RCOPYP
      INTEGER N
      REAL A(5),B(5)
      DATA A/1.0,-2.0,3.25,4.0,-5.0/
      DATA B/5*0.0/
      N=3
      CALL RVCOPY(N,A(2),B)
      WRITE(6,10) B(1),B(2),B(3),B(4),B(5)
      N=5
      CALL RVCOPY(N,A,B)
      WRITE(6,10) B(1),B(2),B(3),B(4),B(5)
   10 FORMAT(5F8.2)
      CALL SLEEP(100)
      END
      SUBROUTINE RVCOPY(N,A,B)
      INTEGER N,I
      REAL A(N),B(N)
      DO 20 I=1,N
      B(I)=A(I)
   20 CONTINUE
      RETURN
      END

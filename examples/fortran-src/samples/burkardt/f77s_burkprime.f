C     Adapted from John Burkardt's prime_serial/prime_serial.f
C     Subroutine PRIME_NUMBER, modified to ANSI F77S/ZX-UX.
C     Original modified 20 May 2009, licensed GNU LGPL.
C     Original file: https://github.com/johannesgerer/
C    &jburkardt-f77/blob/master/prime_serial/prime_serial.f
C     Changed: numbered DO, integer bounds, fixed identifiers,
C     six-character names, removed F90 constructs and timestamp.
      PROGRAM BPRIM
      INTEGER N,TOT
      N=10
      CALL PRIMES(N,TOT)
      WRITE(6,20) TOT
      N=100
      CALL PRIMES(N,TOT)
      WRITE(6,20) TOT
   20 FORMAT(I4)
      CALL SLEEP(100)
      END
      SUBROUTINE PRIMES(N,TOT)
      INTEGER N,TOT,I,J,PRIM,JEND
      TOT=0
      DO 20 I=2,N
      PRIM=1
      JEND=I-1
      DO 10 J=2,JEND
      IF (MOD(I,J) .EQ. 0) THEN
      PRIM=0
      GO TO 10
      ENDIF
   10 CONTINUE
      TOT=TOT+PRIM
   20 CONTINUE
      RETURN
      END

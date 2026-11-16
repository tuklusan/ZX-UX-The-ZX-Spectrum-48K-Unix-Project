      PROGRAM FACT
      INTEGER N, I, RESULT
      N = 6
      RESULT = 1
      DO 100 I = 1, N
        RESULT = RESULT * I
  100 CONTINUE
      PRINT *, RESULT
      CALL SLEEP(100)
      END

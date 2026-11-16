{ BSD-3-Clause; adapted from modern-pascal/modern-pascal-course/030_fibonacci_optimized/fibonacci_optimized.dpr.
  Original copyright retained; HiSoft 16-bit Fibonacci range. }
PROGRAM FIBOPT;
VAR FIBO: ARRAY [0..23] OF INTEGER;
    I: INTEGER;
BEGIN
  FIBO[0] := 0;
  FIBO[1] := 1;
  FOR I := 2 TO 23 DO
  BEGIN
    FIBO[I] := FIBO[I-1] + FIBO[I-2];
    WRITELN('Fibonacci(', I, ') = ', FIBO[I])
  END
END.

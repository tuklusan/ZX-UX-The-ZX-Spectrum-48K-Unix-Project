{ BSD-3-Clause; adapted from modern-pascal/modern-pascal-course/040_fibonacci_large/fibonacci_large.dpr.
  Original copyright retained; UInt64 changed to 16-bit INTEGER. }
PROGRAM FIBLARGE;
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

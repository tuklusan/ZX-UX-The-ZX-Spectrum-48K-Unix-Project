{ BSD-3-Clause; adapted from modern-pascal/modern-pascal-course/030_fibonacci_optimized/fibonacci_optimized.dpr.
  Original copyright retained; HiSoft 16-bit array adaptation. }
PROGRAM RUN21;
VAR ARR: ARRAY [0..20] OF INTEGER;
    K: INTEGER;
BEGIN
  ARR[0] := 0;
  ARR[1] := 1;
  FOR K := 2 TO 20 DO
  BEGIN
    ARR[K] := ARR[K-1] + ARR[K-2];
    WRITELN('Series(', K, ') = ', ARR[K])
  END
END.

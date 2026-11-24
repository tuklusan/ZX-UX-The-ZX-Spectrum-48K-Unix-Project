\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/GEMM8BIT.F83
\ Expected output: original/F83_Z80_SUITE/reference/EXPECTED.csv
( REQUIRED FORTH-83 WORDS ONLY. 16-BIT CELL, Q=1000. )
DECIMAL
: F* 1000 */ ;
: F/ 1000 SWAP */ ;
: A@ SWAP 2 * + @ ;
: A! SWAP 2 * + ! ;
: M@ >R 16 * + 2 * R> + @ ;
: M! >R 16 * + 2 * R> + ! ;
VARIABLE SQN VARIABLE SQR
: FSQRT ( n -- qsqrt )
  DUP 0= IF EXIT THEN SQN ! 1000 SQR !
  10 0 DO SQN @ 1000 SQR @ */ SQR @ + 2 / SQR ! LOOP
  SQR @ ;
VARIABLE EXX VARIABLE EXT VARIABLE EXS
: FEXP ( x -- qexp for 0 <= x <= 1000 )
  EXX ! 1000 EXT ! 1000 EXS !
  8 1 DO EXT @ EXX @ F* I / EXT !
         EXS @ EXT @ + EXS ! LOOP EXS @ ;
: FTEST ( x mode -- y )
  1 = IF FEXP ELSE DUP F* 1000 + 4000 SWAP F/ THEN ;

( 11X11 AND 15X15, COLUMN/ROW STRIDES. )
CREATE GA 512 ALLOT CREATE GB 512 ALLOT CREATE GC 512 ALLOT
VARIABLE GN VARIABLE GM VARIABLE GK VARIABLE GJ
VARIABLE GT VARIABLE GS
: GEMM
  3 1 DO I GM ! I 4 * 7 + GN !
    GN @ 0 DO GN @ 0 DO
      I J - 20 * 100 + I J GA M!
      I J + 10 * I J = IF DROP 1000 I 10 * + THEN I J GB M!
      0 I J GC M!
    LOOP LOOP
    GN @ 0 DO I GJ ! GN @ 0 DO I GK !
      GN @ 0 DO
        I GJ @ GC M@ I GK @ GA M@
        GK @ GJ @ GB M@ F* + I GJ @ GC M!
      LOOP LOOP LOOP
    0 GS ! GN @ 0 DO GS @ I I GC M@ + GS ! LOOP
    ." GEMM " GM @ . GN @ . GS @ .
    0 0 GC M@ . GN @ 1- DUP GC M@ . CR
  LOOP ;
GEMM

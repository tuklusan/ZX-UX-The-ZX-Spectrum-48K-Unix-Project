\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/CHOLESKY.F83
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

( SPD MATRIX GENERATE / CHOLESKY, N=5/7. )
CREATE CL0 128 ALLOT CREATE CA 128 ALLOT
CREATE CL 128 ALLOT
VARIABLE CN VARIABLE CM VARIABLE CI VARIABLE CJ
VARIABLE CK VARIABLE CS VARIABLE CE
: C8@ >R 8 * + 2 * R> + @ ;
: C8! >R 8 * + 2 * R> + ! ;
: CHOLESKY
  3 1 DO I CM ! I 2 * 3 + CN !
    CN @ 0 DO CN @ 0 DO
      I J < IF 0 ELSE
        I J = IF I 100 * 2000 + ELSE I J - 25 * THEN
      THEN I J CL0 C8!
      0 I J CL C8!
    LOOP LOOP
    CN @ 0 DO
      I CJ !
      CN @ 0 DO
        I CI ! 0 CS !
        CN @ 0 DO
          CI @ I CL0 C8@ CJ @ I CL0 C8@ F*
          CS @ + CS !
        LOOP
        CS @ CI @ CJ @ CA C8!
      LOOP
    LOOP
    CN @ 0 DO
      I CJ ! CN @ I DO
        I CI ! CI @ CJ @ CA C8@ CS !
        CJ @ 0> IF
          CJ @ 0 DO
            CS @ CI @ I CL C8@ CJ @ I CL C8@ F* - CS !
          LOOP
        THEN
        CI @ CJ @ = IF CS @ FSQRT ELSE
          CS @ CJ @ CJ @ CL C8@ F/ THEN
        CI @ CJ @ CL C8!
      LOOP
    LOOP
    0 CE ! CN @ 0 DO CN @ I DO
      I J CL C8@ I J CL0 C8@ - ABS CE @ MAX CE !
    LOOP LOOP
    ." CHOLESKY " CM @ . CN @ . CE @ . CR
  LOOP ;
CHOLESKY

\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/NEWTON.F83
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

( TWO NEWTON SOLVES. )
VARIABLE NX VARIABLE NF VARIABLE ND VARIABLE NM
: NEWTON
  3 1 DO I NM ! 1500 NX !
    8 0 DO
      NX @ DUP F* NF !
      NM @ 1 = IF NF @ 2000 - NF ! NX @ 2 * ND !
      ELSE NF @ NX @ F* NX @ - 2000 - NF !
           NX @ DUP F* 3 * 1000 - ND ! THEN
      ND @ 0= IF 1 ND ! THEN
      NX @ NF @ ND @ F/ - NX !
    LOOP
    ." NEWTON " NM @ . NX @ . NF @ . CR
  LOOP ;
NEWTON

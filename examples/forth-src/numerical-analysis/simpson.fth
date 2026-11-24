\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/SIMPSON.F83
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

( SIMPSON Q1000 WITH SIGNED TERMS AND UNSIGNED DOUBLE SUM. )
CREATE SDACC 4 ALLOT
VARIABLE SN VARIABLE SH VARIABLE SM VARIABLE SX
: SDGET SDACC @ SDACC 2 + @ ;
: SDSET SDACC 2 + ! SDACC ! ;
: SDADD ( positive-n -- ) 0 SDGET D+ SDSET ;
: SIMPSON
  3 1 DO I SM ! I 100 * SN ! 1000 SN @ / SH !
    0 0 SDSET
    SN @ 1 DO
      I SH @ * SX ! SX @ SM @ FTEST
      I 2 MOD 0= IF 2 * ELSE 4 * THEN
      SDADD
    LOOP
    0 SM @ FTEST 1000 SM @ FTEST + SDADD
    SDGET SN @ 3 * UM/MOD SWAP DROP
    ." SIMPSON " SM @ . SN @ . . CR
  LOOP ;
SIMPSON

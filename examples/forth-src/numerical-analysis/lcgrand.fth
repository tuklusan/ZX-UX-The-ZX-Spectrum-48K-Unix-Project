\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/LCGRAND.F83
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

( PARK MILLER SCHRAGE IN SIGNED 16 BIT RANGE. )
VARIABLE SEED VARIABLE QQ VARIABLE RR VARIABLE TT
VARIABLE CHECK VARIABLE LM
: LCSTEP
  SEED @ 436 / QQ ! SEED @ 436 MOD RR !
  RR @ 75 * QQ @ 49 * - TT !
  TT @ 0> 0= IF TT @ 32749 + TT ! THEN
  TT @ SEED ! ;
: LCGDEMO
  ." LCG FLOOR-MOD " -13 5 MOD . CR
  4 1 DO I LM !
    I 1 = IF 1 SEED ! ELSE
      I 2 = IF 12345 SEED ! ELSE 32748 SEED ! THEN THEN
    0 CHECK !
    64 0 DO LCSTEP CHECK @ SEED @ 97 MOD + 997 MOD CHECK ! LOOP
    ." LCG " LM @ . SEED @ . CHECK @ . CR
  LOOP ;
LCGDEMO

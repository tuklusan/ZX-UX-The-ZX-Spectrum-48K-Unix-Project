\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/BRENTROT.F83
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

( SAFEGUARDED SECANT/BISECTION, FIXED POINT. )
VARIABLE BRMODE VARIABLE BRA VARIABLE BRB
VARIABLE BRFA VARIABLE BRFB VARIABLE BRC VARIABLE BRFC
VARIABLE BRIT
: BR-F ( x -- y )
  DUP DUP F* BRMODE @ 1 = IF SWAP DROP 2000 -
  ELSE OVER F* SWAP - 2000 - THEN ;
: BRENT-ROOT
  3 1 DO I BRMODE ! 1000 BRA ! 2000 BRB !
    BRA @ BR-F BRFA ! BRB @ BR-F BRFB !
    16 0 DO
      I BRIT !
      BRFA @ BRFB @ - 0= IF
        BRA @ BRB @ + 2 /
      ELSE
        BRFB @ BRB @ BRA @ - BRFB @ BRFA @ - */
        BRB @ SWAP -
      THEN BRC !
      BRC @ BRA @ 1+ < BRC @ BRB @ 1- > OR
      IF BRA @ BRB @ + 2 / BRC ! THEN
      BRC @ BR-F BRFC !
      BRFA @ 0< BRFC @ 0< =
      IF BRC @ BRA ! BRFC @ BRFA !
      ELSE BRC @ BRB ! BRFC @ BRFB ! THEN
    LOOP
    ." BRENT " BRMODE @ . BRA @ BRB @ + 2 / .
    BRA @ BRB @ + 2 / BR-F . CR
  LOOP ;
BRENT-ROOT

\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/GAUSS1D.F83
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

( FOUR POSITIVE NODES OF EIGHT-POINT GAUSS-LEGENDRE. )
CREATE GX 183 , 526 , 797 , 960 ,
CREATE GW 363 , 314 , 222 , 101 ,
VARIABLE GM VARIABLE GSUM VARIABLE GZ
: GAUSS
  3 1 DO I GM ! 0 GSUM !
    4 0 DO
      1000 I GX A@ - 2 / GZ !
      GZ @ GM @ FTEST
      1000 I GX A@ + 2 / GM @ FTEST +
      I GW A@ F* GSUM @ + GSUM !
    LOOP
    ." GAUSS " GM @ . GSUM @ 2 / . CR
  LOOP ;
GAUSS

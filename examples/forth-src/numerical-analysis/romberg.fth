\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/ROMBERG.F83
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

( FIVE ROMBERG LEVELS, 5X5 ARRAY. )
CREATE RA 512 ALLOT
VARIABLE RM VARIABLE RN VARIABLE RH VARIABLE RS
VARIABLE RF VARIABLE RX
: ROMBERG
  3 1 DO I RM !
    0 RM @ FTEST 1000 RM @ FTEST + 2 / 0 0 RA M!
    1 RN ! 1000 RH !
    5 1 DO
      RH @ 2 / RH ! 0 RS !
      RN @ 0 DO
        I 2 * 1+ RH @ * RX !
        RS @ RX @ RM @ FTEST + RS ! LOOP
      I 1- 0 RA M@ 2 / RH @ RS @ F* + I 0 RA M!
      4 RF !
      I 0 DO
        I 1+ 1- RX !
        J RX @ RA M@ J 1- RX @ RA M@ -
        1 RF @ 1- */
        J RX @ RA M@ + J RX @ 1+ RA M!
        RF @ 4 * RF !
      LOOP
      RN @ 2 * RN !
    LOOP
    ." ROMBERG " RM @ . RN @ . 4 4 RA M@ . CR
  LOOP ;
ROMBERG

\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/THOMASTR.F83
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

( IN-PLACE TRIDIAGONAL SOLVE; N=10/20. )
CREATE TA 40 ALLOT CREATE TB 40 ALLOT
CREATE TC 40 ALLOT CREATE TD 40 ALLOT
VARIABLE TN VARIABLE TM VARIABLE TT VARIABLE TE VARIABLE TV
: THOMAS
  3 1 DO I TM ! I 10 * TN !
    TN @ 0 DO
      -1000 I TA A! 4000 I TB A! -1000 I TC A!
      1000 I 25 * + TV !
      TV @ 4 * I 0> IF 1000 I 1- 25 * + - THEN
      I TN @ 1- < IF 1000 I 1+ 25 * + - THEN I TD A!
    LOOP
    TN @ 1 DO
      I TA A@ I 1- TB A@ F/ TT !
      I TB A@ TT @ I 1- TC A@ F* - I TB A!
      I TD A@ TT @ I 1- TD A@ F* - I TD A!
    LOOP
    TN @ 1- DUP TD A@ SWAP TB A@ F/ TN @ 1- TD A!
    TN @ 1- 0 DO
      TN @ 2 - I - TE !
      TE @ TD A@ TE @ TC A@ TE @ 1+ TD A@ F* -
      TE @ TB A@ F/ TE @ TD A!
    LOOP
    0 TE ! TN @ 0 DO
      I TD A@ 1000 I 25 * + - ABS TE @ MAX TE ! LOOP
    ." THOMAS " TM @ . TN @ . TE @ .
    0 TD A@ . TN @ 1- TD A@ . CR
  LOOP ;
THOMAS

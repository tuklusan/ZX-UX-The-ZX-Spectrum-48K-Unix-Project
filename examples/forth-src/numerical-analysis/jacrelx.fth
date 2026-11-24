\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/JACRELX.F83
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

( DOUBLE BUFFER JACOBI FOR 8X8 AND 16X16. )
CREATE JA 512 ALLOT CREATE JB 512 ALLOT
VARIABLE JN VARIABLE JM VARIABLE JK VARIABLE JD
VARIABLE JV VARIABLE JS
: JACOBI
  3 1 DO I JM ! I 8 * JN !
    JN @ 0 DO JN @ 0 DO
      J JN @ 1- = IF 1000 ELSE 0 THEN
      DUP I J JA M! I J JB M!
    LOOP LOOP
    I 20 * 0 DO
      0 JD !
      JN @ 1- 1 DO JN @ 1- 1 DO
        I 1- J JA M@ I 1+ J JA M@ +
        I J 1- JA M@ + I J 1+ JA M@ + 4 /
        DUP JV ! I J JA M@ - ABS JD @ MAX JD !
        JV @ I J JB M!
      LOOP LOOP
      JN @ 1- 1 DO JN @ 1- 1 DO
        I J JB M@ I J JA M! LOOP LOOP
    LOOP
    JN @ 2 / DUP JA M@ JS !
    ." JACOBI " JM @ . JN @ . JS @ . JD @ . CR
  LOOP ;
JACOBI

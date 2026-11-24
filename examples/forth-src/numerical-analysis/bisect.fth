\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/BISECT.F83
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

( BISECTION: ROOTS OF X^2-2 AND X^3-X-2. )
VARIABLE BA VARIABLE BB VARIABLE BM VARIABLE BF
VARIABLE BT VARIABLE BMODE VARIABLE BROOT
: B-F ( x -- f )
  DUP DUP F* BMODE @ 1 = IF SWAP DROP 2000 -
  ELSE OVER F* SWAP - 2000 - THEN ;
: BISECT
  3 1 DO I BMODE ! 1000 BA ! 2000 BB !
    16 0 DO BA @ BB @ + 2 / BM !
      BA @ B-F BM @ B-F F* 0<
      IF BM @ BB ! ELSE BM @ BA ! THEN LOOP
    BA @ BB @ + 2 / BROOT !
    ." BISECT " BMODE @ . BROOT @ . BROOT @ B-F . CR
  LOOP ;
BISECT

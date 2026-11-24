\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/WHETSTON.F83
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

( WHETSTONE STYLE: MIXED ARITHMETIC AND SQRT. )
VARIABLE W1 VARIABLE W2 VARIABLE W3 VARIABLE W4
VARIABLE WT VARIABLE WY VARIABLE WZ VARIABLE WS VARIABLE WM
: WCORE
  W1 @ W2 @ + W3 @ + W4 @ - WT @ F* W1 !
  W1 @ W2 @ + W3 @ - W4 @ + WT @ F* W2 !
  W1 @ W2 @ - W3 @ + W4 @ + WT @ F* W3 !
  W1 @ NEGATE W2 @ + W3 @ + W4 @ + WT @ F* W4 ! ;
: WHETSTONE
  3 1 DO I WM ! 500 WT !
    1000 W1 ! -1000 W2 ! -1000 W3 ! -1000 W4 !
    I 10 * 0 DO 12 0 DO WCORE LOOP LOOP
    500 WY ! 250 WZ !
    I 10 * 0 DO
      WY @ WZ @ 100 / + WY !
      WZ @ WY @ + 2 / WZ !
      WY @ 1000 WZ @ 10000 / + F/ WY ! LOOP
    0 WS !
    I 10 * 0 DO 1000 I 10 * + FSQRT WS @ + WS ! LOOP
    ." WHET " WM @ . W1 @ . W2 @ . WY @ . WS @ . CR
  LOOP ;
WHETSTONE

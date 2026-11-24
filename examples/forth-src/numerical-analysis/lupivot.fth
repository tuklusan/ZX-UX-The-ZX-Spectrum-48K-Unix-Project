\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/LUPIVOT.F83
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

( OPTIONAL SHARED 8X8 LINEAR SOLVER WITH PARTIAL ROW SELECTION. )
( LOAD AFTER COMMON, BEFORE LUPIVOT MINILIN POLYFIT. )
CREATE LA 512 ALLOT CREATE LB 16 ALLOT
VARIABLE LN VARIABLE LK VARIABLE LP VARIABLE LR
VARIABLE LM VARIABLE LV VARIABLE LMAX VARIABLE LT
VARIABLE LI
: LINSOLVE ( n -- )
  LN !
  LN @ 1- 0 DO
    I LK ! I LP ! I I LA M@ ABS LMAX !
    LN @ LK @ 1+ DO
      I LK @ LA M@ ABS DUP LMAX @ >
      IF LMAX ! I LP ! ELSE DROP THEN
    LOOP
    LP @ LK @ = 0= IF
      LN @ 0 DO
        LK @ I LA M@ LT !
        LP @ I LA M@ LK @ I LA M!
        LT @ LP @ I LA M!
      LOOP
      LK @ LB A@ LT !
      LP @ LB A@ LK @ LB A!
      LT @ LP @ LB A!
    THEN
    LN @ LK @ 1+ DO
      I LR !
      LR @ LK @ LA M@ LK @ LK @ LA M@ F/ LM !
      LN @ LK @ 1+ DO
        LR @ I LA M@ LM @ LK @ I LA M@ F* -
        LR @ I LA M!
      LOOP
      LR @ LB A@ LM @ LK @ LB A@ F* - LR @ LB A!
      0 LR @ LK @ LA M!
    LOOP
  LOOP
  LN @ 0 DO
    LN @ 1- I - LI ! LI @ LB A@ LV !
    LI @ LN @ 1- < IF
      LN @ LI @ 1+ DO
        LV @ LI @ I LA M@ I LB A@ F* - LV !
      LOOP
    THEN
    LV @ LI @ LI @ LA M@ F/ LI @ LB A!
  LOOP ;

( TWO GAUSSIAN ELIMINATION CASES WITH PARTIAL ROW SELECTION. )
VARIABLE UN VARIABLE UM VARIABLE UX VARIABLE UE
: LU-PIVOT
  3 1 DO I UM ! I 2 * 4 + UN !
    UN @ 0 DO UN @ 0 DO
      I J + 50 * I J = IF DROP 4000 THEN
      J 0= I 0= AND IF DROP 0 THEN
      J 0= I 1 = AND IF DROP 2000 THEN
      I J LA M!
    LOOP LOOP
    UN @ 0 DO
      0 UX ! UN @ 0 DO
        J I LA M@ 200 I 100 * + F* UX @ + UX !
      LOOP UX @ I LB A!
    LOOP
    UN @ LINSOLVE
    0 UE ! UN @ 0 DO
      I LB A@ 200 I 100 * + - ABS UE @ MAX UE ! LOOP
    ." LUPIVOT " UM @ . UN @ . UE @ . 0 LB A@ . CR
  LOOP ;
LU-PIVOT

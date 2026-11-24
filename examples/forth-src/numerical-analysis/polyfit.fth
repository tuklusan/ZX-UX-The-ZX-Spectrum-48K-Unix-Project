\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/POLYFIT.F83
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

( LEAST SQUARES NORMAL EQUATIONS, NC=3/4. )
CREATE PC 10 ALLOT CREATE PP 18 ALLOT
VARIABLE PN VARIABLE PM VARIABLE PNC VARIABLE PX
VARIABLE PY VARIABLE PT VARIABLE PE VARIABLE PK
: POLY-FIT
  3 1 DO I PM ! I 2 + PNC ! I 2 * 7 + PN !
    0 0 PC A! 0 1 PC A! 0 2 PC A! 0 3 PC A!
    I 1 = IF
      1000 0 PC A! 500 1 PC A! -250 2 PC A!
    ELSE
      250 0 PC A! -400 1 PC A!
      300 2 PC A! -100 3 PC A! THEN
    PNC @ 0 DO
      0 I LB A!
      PNC @ 0 DO 0 I J LA M! LOOP LOOP
    PN @ 0 DO
      I 2 * PN @ 1- - 1000 PN @ 1- */ PX !
      1000 0 PP A!
      8 1 DO I 1- PP A@ PX @ F* I PP A! LOOP
      0 PY ! PNC @ 0 DO
        I PC A@ I PP A@ F* PY @ + PY ! LOOP
      PNC @ 0 DO I PK !
        I LB A@ PY @ I PP A@ F* + I LB A!
        PNC @ 0 DO
          I PK @ LA M@ PK @ PP A@ I PP A@ F* +
          I PK @ LA M!
        LOOP LOOP
    LOOP
    PNC @ LINSOLVE
    0 PE ! PNC @ 0 DO
      I LB A@ I PC A@ - ABS PE @ MAX PE ! LOOP
    ." POLYFIT " PM @ . PN @ . PNC @ . PE @ .
    0 LB A@ . PNC @ 1- LB A@ . CR
  LOOP ;
POLY-FIT

\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/RK4FIXED.F83
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

( RK4 FOR DECAY AND LOGISTIC ODE. )
VARIABLE RY VARIABLE RH VARIABLE RN VARIABLE RM
VARIABLE RK1 VARIABLE RK2 VARIABLE RK3 VARIABLE RKFOUR
: DERIV ( y -- dy )
  RM @ 1 = IF -2 * ELSE DUP 1000 SWAP - F* THEN ;
: RK4
  3 1 DO I RM ! 10 I * RN ! 1000 RN @ / RH !
    I 1 = IF 1000 ELSE 250 THEN RY !
    RN @ 0 DO
      RY @ DERIV RK1 !
      RY @ RH @ RK1 @ F* 2 / + DERIV RK2 !
      RY @ RH @ RK2 @ F* 2 / + DERIV RK3 !
      RY @ RH @ RK3 @ F* + DERIV RKFOUR !
      RK1 @ RK2 @ 2 * + RK3 @ 2 * + RKFOUR @ +
      RH @ F* 6 / RY @ + RY !
    LOOP
    ." RK4 " RM @ . RN @ . RY @ . CR
  LOOP ;
RK4

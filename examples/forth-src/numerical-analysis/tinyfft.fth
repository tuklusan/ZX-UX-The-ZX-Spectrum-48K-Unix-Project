\ Adapted from the user-supplied F83_Z80_SUITE archive.
\ Support is concatenated because rfc is a batch compiler without INCLUDE.
\ Original source: original/F83_Z80_SUITE/TINYFFT.F83
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

( IN-PLACE 64-POINT RADIX-2 FFT; TWO EXACT INPUTS. )
CREATE FTWRE
1000 , 995 , 981 , 957 , 924 , 882 , 831 , 773 ,
707 , 634 , 556 , 471 , 383 , 290 , 195 , 98 ,
0 , -98 , -195 , -290 , -383 , -471 , -556 , -634 ,
-707 , -773 , -831 , -882 , -924 , -957 , -981 , -995 ,
CREATE FTWIM
0 , -98 , -195 , -290 , -383 , -471 , -556 , -634 ,
-707 , -773 , -831 , -882 , -924 , -957 , -981 , -995 ,
-1000 , -995 , -981 , -957 , -924 , -882 , -831 , -773 ,
-707 , -634 , -556 , -471 , -383 , -290 , -195 , -98 ,
CREATE FRE 128 ALLOT CREATE FIM 128 ALLOT
VARIABLE FREV VARIABLE FIN VARIABLE FN VARIABLE FM
VARIABLE FLEN VARIABLE FHALF VARIABLE FSTEP
VARIABLE FI VARIABLE FJ VARIABLE FK VARIABLE FE
VARIABLE FWR VARIABLE FWI VARIABLE FTR VARIABLE FTI
VARIABLE FAR VARIABLE FAI VARIABLE FTEMP VARIABLE FERR
VARIABLE FER VARIABLE FEI
: REV6 ( i -- reversed bits )
  FIN ! 0 FREV !
  6 0 DO
    FREV @ 2 * FIN @ 2 MOD + FREV !
    FIN @ 2 / FIN !
  LOOP FREV @ ;
: FFT64
  4 1 DO I FM !
    64 0 DO 0 I FRE A! 0 I FIM A! LOOP
    I 1 = IF 1000 0 FRE A! THEN
    I 2 = IF 1000 0 FRE A! 1000 32 FRE A! THEN
    I 3 = IF 1000 1 FRE A! THEN
    64 0 DO I REV6 FJ !
      I FJ @ < IF
        I FRE A@ FTEMP ! FJ @ FRE A@ I FRE A!
        FTEMP @ FJ @ FRE A!
        I FIM A@ FTEMP ! FJ @ FIM A@ I FIM A!
        FTEMP @ FJ @ FIM A!
      THEN
    LOOP
    2 FLEN !
    BEGIN FLEN @ 65 < WHILE
      FLEN @ 2 / FHALF ! 64 FLEN @ / FSTEP !
      FHALF @ 0 DO
        I FSTEP @ * DUP FTWRE A@ FWR !
        FTWIM A@ FWI !
        I FJ !
        BEGIN FJ @ 64 < WHILE
          FJ @ FHALF @ + FK !
          FK @ FRE A@ FWR @ F* FK @ FIM A@ FWI @ F* - FTR !
          FK @ FRE A@ FWI @ F* FK @ FIM A@ FWR @ F* + FTI !
          FJ @ FRE A@ FAR ! FJ @ FIM A@ FAI !
          FAR @ FTR @ - FK @ FRE A!
          FAI @ FTI @ - FK @ FIM A!
          FAR @ FTR @ + FJ @ FRE A!
          FAI @ FTI @ + FJ @ FIM A!
          FJ @ FLEN @ + FJ !
        REPEAT
      LOOP
      FLEN @ 2 * FLEN !
    REPEAT
    0 FERR ! 64 0 DO
      FM @ 3 = IF
        I 32 < IF
          I FTWRE A@ FER ! I FTWIM A@ FEI !
        ELSE
          I 32 - FTWRE A@ NEGATE FER !
          I 32 - FTWIM A@ NEGATE FEI !
        THEN
      ELSE
        FM @ 1 = IF 1000 ELSE
          I 2 MOD 0= IF 2000 ELSE 0 THEN THEN FER !
        0 FEI !
      THEN
      FER @ I FRE A@ - ABS FEI @ I FIM A@ - ABS +
      FERR @ MAX FERR !
    LOOP
    ." FFT " FM @ . 64 . FERR @ .
    0 FRE A@ . 1 FRE A@ . CR
  LOOP ;
FFT64

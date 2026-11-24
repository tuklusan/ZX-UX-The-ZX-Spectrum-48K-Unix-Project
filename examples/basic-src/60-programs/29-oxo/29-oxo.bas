   5 REM NOUGHTS+CROSSES             @ 1982 BY MICHAEL BEWS
  10 DIM a$(9): DIM a(9): LET d=0: LET h=0: LET m=0: LET n=0: LET t=0
  12 PAPER 1: BORDER 1: INK 7: CLS 
  15 LET Y$=CHR$ 143+"     "+CHR$ 143+"     "+CHR$ 143+"     "+CHR$ 143
  20 LET Z$="{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}": REM y${C6}z${CC}form grid
  25 FOR x=0 TO 7: READ a: POKE USR "c"+x,a: NEXT x: FOR x=0 TO 7: READ a: POKE USR "a"+x,a: NEXT x: REM {C0}defined x{C6}o
  30 GO TO 200
  34 REM ******** main routine ***
  35 BEEP .1,t*4: LET t=t+1: LET a$(n)=CHR$ (a+145): LET a(n)=SGN a: LET a=-a: IF a<0 THEN PRINT AT 10,30;" ";
  40 FOR x=0 TO 2: FOR y=1 TO 3: LET z=x*3+y: FLASH 1 AND z=n: PRINT AT 5+5*x,3+6*y;a$(z): NEXT y: NEXT x: FLASH 0
  49 REM ****check for win****
  50 FOR x=0 TO 2: IF ABS (a(3*x+1)+a(3*x+2)+a(3*x+3))=3 OR ABS (a(x+1)+a(x+4)+a(x+7))=3 THEN GO TO 300
  60 IF x>1 THEN GO TO 80
  70 IF ABS (a(5)+a(5+2*(x+1))+a(5-2*(x+1)))=3 THEN GO TO 300
  80 NEXT x: IF t=9 THEN GO TO 118: REM ****check for a draw****
  85 IF a<0 THEN GO TO 150: REM ****players turn****
  90 IF t>0 THEN GO TO 96
  92 LET n=1+2*INT (RND*5): IF n=5 THEN GO TO 92: REM ***choose a corner square on first move***
  94 GO TO 35
  95 REM ***check for possible win(k=2),then check for possible opponent's win (k=-2)
  96 LET k=2: LET n=0
 100 FOR x=0 TO 2: IF a(3*x+1)+a(3*x+2)+a(3*x+3)=k THEN GO TO 120
 105 IF a(x+1)+a(x+4)+a(x+7)=k THEN GO TO 130
 110 IF x=2 THEN GO TO 112
 111 IF a(5)+a(5+2*(x+1))+a(5-2*(x+1))=k THEN GO TO 140
 112 NEXT x: LET k=-k: IF k<0 THEN GO TO 100
 113 REM ***choose a corner square if possible (40 attempts)***
 114: FOR x=1 TO 40: LET n=1+2*INT (RND*5): IF n<>5 AND a(n)=0 THEN GO TO 35
 115 NEXT x
 116 FOR x=1 TO 9: IF a(x)=0 THEN LET n=x: GO TO 35: REM ***choose any vacant square*****
 117 NEXT x
 118 PRINT AT 19,13; FLASH 1;"DRAW!"; FLASH 0: LET d=d+1: FOR x=13 TO 1 STEP -1: BEEP .1,x-8: NEXT x: GO TO 320
 119 REM ***select the vacant square in potential win row****
 120 FOR y=3 TO 1 STEP -1: IF a(3*x+y)=0 THEN LET n=3*x+y: GO TO 35
 125 NEXT y
 130 FOR y=3 TO 1 STEP -1: IF a(x+y*3-2)=0 THEN LET n=x+3*y-2: GO TO 35
 135 NEXT y
 140 IF a(5)=0 THEN LET n=5: GO TO 35
 142 IF a(5+2*(x+1))=0 THEN LET n=5+2*(x+1): GO TO 35
 144 IF a(5-2*(x+1))=0 THEN LET n=5-2*(x+1): GO TO 35
 149 REM ***player's turn***
 150 LET x$=INKEY$: IF x$="" OR x$<"1" OR x$>"9" THEN GO TO 150
 160 LET n=VAL x$
 170 PRINT AT 11,26;"      ";AT 10,26;"You ";n;: IF a$(n)>"9" THEN PRINT AT 11,26;"AGAIN!";: FOR x=1 TO 5: FOR y=1 TO 3: NEXT y: BEEP .1,30: NEXT x: GO TO 150
 180 GO TO 35
 199 REM ****INITIALISATION*****
 200 PRINT TAB 7;"NOUGHTS & CROSSES";AT 0,7; OVER 1;"_________________"; OVER 0
 210 FOR x=1 TO 9: LET a$(x)=STR$ x: NEXT x
 230 PRINT : PRINT : FOR X=1 TO 3: PRINT TAB 6; INK 6;Z$;TAB 6; INK 4;Y$;TAB 6; INK 2;Y$;TAB 6; INK 5;Y$;TAB 6; INK 3;Y$: NEXT X: PRINT TAB 6; INK 6;Z$
 240 PRINT AT 1,1;"I am";TAB 25;"You are";AT 3,2;"{92}";AT 3,28;"{90}"; FLASH 0
 250 LET a=(2*INT (1+RND*2)-3)
 260 LET p$="Me": IF a<0 THEN LET p$="You"
 270 PRINT AT 2,8;p$;" to go FIRST";: GO TO 40
 299 REM ****END OF GAME ROUTINE***
 300 LET p$="YOU WIN": IF a<0 THEN LET p$="I WIN": LET m=m+1: GO TO 310
 305 LET h=h+1
 310 PRINT AT 19,13; FLASH 1;p$; FLASH 0: FOR x=1 TO 4: FOR y=1 TO 10: BEEP .04,y*2: NEXT y: NEXT x
 320 PRINT AT 20,0;"Score: You ";h;"   Me ";m;"    Draw ";d;AT 21,3;"Press any key for new game";
 330 LET x$=INKEY$: IF x$="" THEN GO TO 330
 335 FOR x=1 TO 9: LET a(x)=0: NEXT x
 340 LET n=0: LET t=0: CLS : GO TO 200
 350 DATA 24,126,102,195,195,102,126,24,129,195,102,60,24,60,102,195

   1 REM Colony Invaders
   2 REM Typed and fixed by Paul Jenkinso 2023
   3 LET high=0
   9 GO SUB 5000
  10 DATA {C4}00000001,{C4}00000011,{C4}00000111,{C4}00001111,{C4}00011111,{C4}00111111,{C4}01111111,{C4}11111111
  20 DATA {C4}10000000,{C4}11000000,{C4}11100000,{C4}11110000,{C4}11111000,{C4}11111100,{C4}11111110,{C4}11111111
  30 FOR x=0 TO 7: READ y: POKE USR "a"+x,y: NEXT x
  40 FOR x=0 TO 7: READ y: POKE USR "b"+x,y: NEXT x
  50 BORDER 0: PAPER 5: INK 1: CLS 
  60 PRINT AT 12,0;"      {90}{91}                             {90}{8F}{8F}{91}        {90}{91}         {90}{91}      {90}{8F}{8F}{8F}{8F}{91}      {90}{8F}{8F}{91}  {90}{91}   {90}{8F}{8F}{91} {90}{91} {90}{8F}{8F}{8F}{8F}{8F}{8F}{91}{90}{91}{90}{91}{90}{8F}{8F}{8F}{8F}{91}{90}{8F}{8F}{91} {90}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}"
  70 PRINT PAPER 4;"                                                                                                                                "
  80 FOR x=0 TO 20: CIRCLE INK 6;200,140,x: NEXT x
  90 DATA {C4}00011000,{C4}00111100,{C4}01100110,{C4}01111110,{C4}00111100,{C4}00100100,{C4}01000010,{C4}00100100
  95 DATA {C4}00101010,{C4}00011100,{C4}00001000,{C4}00101010,{C4}00011100,{C4}00001000,{C4}00101010,{C4}00011100,{C4}00001000,{C4}00011000,{C4}00001000
  97 FOR x=0 TO 7: READ y: POKE USR "c"+x,y: NEXT x
 100 FOR x=0 TO 7: READ y: POKE USR "d"+x,y: NEXT x
 101 PRINT INK 6; PAPER 4;AT 19,1;"{93}";AT 20,4;"{93}";AT 19,15;"{93}";AT 19,9;"{93}";AT 18,4;"{93}";AT 20,13;"{93}";AT 19,24;"{93}";AT 18,30;"{93}";AT 21,28;"{93}"
 103 LET c=15: LET d=5: LET score=0: LET life=9
 104 RESTORE 245: PRINT AT 0,0;"Score: ";score;AT 0,15; INVERSE 1;"High: ";high
 105 LET x=5: LET y=0
 107 LET x=(INT (RND*3)-1)+x: IF x>7 THEN LET x=x-2: GO TO 107
 108 IF x<3 THEN LET x=x+1: GO TO 107
 110 IF ATTR (x+1,y+2)=46 OR ATTR (x-1,y+2)=46 OR ATTR (x,y+1)=46 THEN GO TO 200
 115 GO SUB 500
 117 IF x=d AND y=c THEN LET score=score+(25-y): PRINT AT 0,6;score: BEEP .2,10: BEEP .3,20: GO TO 105
 120 PRINT INK 2;AT x,y;"{92}"
 130 BEEP .1,x*5: PRINT AT x,y;" ": LET y=y+1: GO TO 107
 200 PRINT AT x,y; BRIGHT 1; INK 2; PAPER 6;"*": READ e,f: PRINT AT e,f; INK 3; PAPER 4;"{93}"
 210 FOR t=0 TO 1 STEP .05: BEEP .01,t: NEXT t: FOR t=0 TO 1 STEP -.05: BEEP .01,t: NEXT t
 220 PRINT AT x,y; PAPER 5;" "
 240 LET life=life-1: IF life=0 THEN GO TO 1000
 245 DATA 19,1,20,4,19,15,19,9,18,4,20,13,19,24,18,30,21,28
 250 GO TO 105
 500 PRINT AT d,c;" "
 505 IF INKEY$="5" THEN LET c=c-1: IF c<0 THEN LET c=0
 510 IF INKEY$="6" THEN LET d=d+1: IF d>7 THEN LET d=7
 520 IF INKEY$="7" THEN LET d=d-1: IF d<3 THEN LET d=3
 530 IF INKEY$="8" THEN LET c=c+1: IF c>20 THEN LET c=20
 550 IF INKEY$=CHR$ 8 THEN LET c=c-2: IF c<0 THEN LET c=0
 560 IF INKEY$=CHR$ 9 THEN LET c=c+2: IF c>20 THEN LET c=20
 570 IF INKEY$=CHR$ 10 THEN LET d=d+2: IF d>7 THEN LET d=7
 580 IF INKEY$=CHR$ 11 THEN LET d=d-2: IF d<3 THEN LET d=3
 590 PRINT AT d,c; INK 7;"#"
 600 RETURN 
1000 RESTORE 
1020 PRINT AT 10,10; FLASH 1; INK 0; OVER 1; PAPER 8;"Crops burnt";AT 11,10;"by radiation"
1030 FOR e=1 TO 1000: NEXT e
1040 GO TO 9
5000 BORDER 7: PAPER 7: INK 0: FLASH 0: OVER 0: INVERSE 0: CLS 
5010 PRINT "         COLONY INVADERS"'"        {7F}1983 R.Blachford"' FLASH 1;"      Personal Computer News   "
5020 PRINT ''
5030 PRINT "You are in charge of the defencesection of an Earth colony. The colony has just established     itself in a valley.             Unfortunately there is a sudden invasion of peculiar beings     which fly beyond the mountins."
5031 PRINT "When they get too   close to thesun, they blow up giving off    rays which do harm to the crops."
5032 PRINT "Your task is to point the targetspot(#) at the invaders the gun will fire automatically."
5040 PRINT #0;" Press any key to continue..."
5050 PAUSE 0: CLS 
5060 PRINT "You have nine lives represented by an ear of yellow corn in the valley. The black (burnt) ears  represent lost lives. A life    is lost when an invader gets"
5061 PRINT "too close to the sun and blows  up. Your final score is the     score that is displayed when allthe nine lives are lost and the"
5062 PRINT "colony starves becasue of there being no harvest."
5063 PRINT "You direct the target using the following keys :-"'
5070 PRINT '"""5"" - Left","""6"" - Down","""7"" - Up","""8"" - Right"''"Press CAPS SHIFT at the same    time to move ""#"" twice as fast."
5080 PAUSE 0: RETURN 

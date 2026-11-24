   1 BORDER 0: PAPER 0: INK 7: CLS 
   5 GO SUB 9000
  10 GO SUB 8000
  20 GO SUB 7000
1000 PRINT AT 14,t;" ": LET t=INT (RND*28)+2: PRINT AT 14,t;"X"
1050 FOR f=0 TO 30: PRINT AT 0,f;" {98}"
1060 IF INKEY$="a" THEN GO TO 2000
1065 BEEP ta,25
1070 NEXT f: GO TO 3000
2000 FOR g=0 TO 14
2010 PRINT INK 4;AT g,f+1;"{99}"
2020 BEEP .05,g
2025 PRINT AT g,f+1;" "
2030 NEXT g
2040 IF f+1<>t THEN GO TO 3000
2100 LET xa=xa-1: LET xb=xb-1: FOR f=20 TO 30: BEEP .01,f: NEXT f
2110 PRINT AT 14,t;" "
2200 PRINT INK 2;AT 16,xa;a$(1);" ";AT 17,xa;a$(2);" "; INK 6;AT 16,xb;b$(1);" ";AT 17,xb;b$(2);" "
2210 PLOT (xa+LEN a$(1))*8,41: DRAW (xb-xa-LEN a$(1))*8-1,0
2220 IF ATTR (18,xb)=3 THEN GO TO 3000
2225 LET u=16: PRINT AT 16,18;" ";AT 17,18;" ": GO SUB 6000
2230 IF tb=.02 THEN DIM b$(2,4): LET b$(1)="{94}{95}{94}{95}": LET b$(2)="{96}{97}{96}{97}"
2232 IF tb=.002 THEN DIM b$(2,2): LET b$(1)="{94}{95}": LET b$(2)="{96}{97}"
2233 IF tb=.0002 THEN LET w=1: GO TO 6500
2235 LET tb=tb/10
2237 LET xb=xb+2
2240 PRINT INK 2;AT 16,xa;a$(1);"  ";AT 17,xa;a$(2);"  "; INK 6;AT 16,xb;b$(1);"  ";AT 17,xb;b$(2);"  "
2250 PLOT (xa+LEN a$(1))*8,41: DRAW (xb-xa-LEN a$(1))*8-1,0
2260 GO TO 3000
3000 PRINT AT 14,t;" ": LET t=INT (RND*28)+2: PRINT AT 14,t;"X"
3050 FOR f=30 TO 0 STEP -1: PRINT AT 0,f;"{98} "
3060 IF INKEY$="l" THEN GO TO 4000
3065 BEEP tb,25
3070 NEXT f: GO TO 1000
4000 FOR g=0 TO 14
4010 PRINT INK 5;AT g,f;"{99}"
4020 BEEP .05,g
4025 PRINT AT g,f;" "
4030 NEXT g
4040 IF f<>t THEN GO TO 1000
4100 LET xa=xa+1: LET xb=xb+1: FOR f=20 TO 30: BEEP .01,f: NEXT f
4200 PRINT INK 2;AT 16,xa-1;" ";a$(1);AT 17,xa-1;" ";a$(2); INK 6;AT 16,xb-1;" ";b$(1);AT 17,xb-1;" ";b$(2)
4210 PLOT (xa+LEN a$(1))*8,41: DRAW (xb-xa-LEN a$(1))*8-1,0
4220 IF ATTR (18,xa+LEN a$(1)-1)=3 THEN GO TO 1000
4225 LET u=14: PRINT AT 16,13;" ";AT 17,13;" ": GO SUB 6000
4230 IF ta=.02 THEN DIM a$(2,4): LET a$(1)="{90}{91}{90}{91}": LET a$(2)="{92}{93}{92}{93}"
4232 IF ta=.002 THEN DIM a$(2,2): LET a$(1)="{90}{91}": LET a$(2)="{92}{93}"
4233 IF ta=.0002 THEN LET w=2: GO TO 6500
4235 LET ta=ta/10
4240 PRINT INK 2;AT 16,xa;a$(1);AT 17,xa;a$(2); INK 6;AT 16,xb;b$(1);AT 17,xb;b$(2)
4250 PLOT (xa+LEN a$(1))*8,41: DRAW (xb-xa-LEN a$(1))*8-1,0
4260 GO TO 1000
6000 FOR f=16 TO 20: PRINT INK 5;AT f,u;"{9A}{9B}"; INK 3;AT f+1,u;"{9C}{9D}"
6010 BEEP .1,10-f
6020 PRINT AT f,u;"  ";AT f+1,u;"  "
6025 NEXT f
6030 RETURN 
6500 FOR f=0 TO 7: PRINT AT 2,2; INK f;"WELL DONE PLAYER ";W;"! YOU WON!": FOR g=1 TO 8: BEEP .04,g*f: NEXT g: NEXT f
6600 PRINT AT 5,2; INK 5;"PRESS ANY KEY TO PLAY AGAIN."
6700 PAUSE 0: PAUSE 0: CLS : GO TO 20
7000 INK 3: FOR f=0 TO 31: PLOT 0,f: DRAW 106+RND*5,0: NEXT f
7010 FOR f=0 TO 31: PLOT 255,f: DRAW -(106+RND*5),0: NEXT f
7012 PLOT 0,31: DRAW 111,0: PLOT 255,31: DRAW -110,0
7015 INK 7
7017 DIM a$(2,6): DIM b$(2,6)
7020 LET a$(1)="{90}{91}{90}{91}{90}{91}": LET a$(2)="{92}{93}{92}{93}{92}{93}": LET b$(1)="{94}{95}{94}{95}{94}{95}": LET b$(2)="{96}{97}{96}{97}{96}{97}"
7030 LET xa=7: LET xb=19
7040 PRINT INK 2,AT 16,xa;a$(1);AT 17,xa;a$(2); INK 6;AT 16,xb;b$(1);AT 17,xb;b$(2)
7050 PLOT (xa+LEN a$(1))*8,41: DRAW (xb-xa-LEN a$(1))*8-1,0
7060 LET ta=.02: LET tb=ta: LET t=0
7300 RETURN 
8000 FOR f=USR "a" TO USR "n"+7: READ g: POKE f,g: NEXT f
8010 DATA 24,52,62,60,24,31,255,15,0,0,0,0,0,248,255,240,15,7,7,3,0,0,0,0,0,128,192,224,112,24,12,7
8020 DATA 0,0,0,0,0,31,255,15,24,44,124,60,24,248,255,240,0,1,3,7,14,24,48,224,240,224,224,192,0,0,0,0
8030 DATA 0,129,66,36,102,255,126,60,16,124,254,0,16,56,16,40
8040 DATA 1,195,101,55,27,15,7,3,128,195,166,236,152,240,224,192,3,3,3,7,14,28,184,112,192,192,192,224,112,56,29,14
8100 RETURN 
9000 PRINT "    TUG________OF________WAR"
9005 PRINT INK 3'"  B Y  P A U L  S T A N L E Y   "
9006 PLOT 0,151: DRAW 255,0: DRAW 0,24: DRAW -255,0: DRAW 0,-24
9010 PRINT INK 6'"A simple game for 2 players who have to win at tug-of-war, not  by strength, but by reactions."
9020 PRINT INK 4'"A UFO will fly across the top ofthe screen and a target will    appear at the bottom. Player 1  can parachute out onto the      target by pressing ""A"", and     player 2 with ""L"""
9030 PRINT INK 6'"If the parachutist lands on the target you will pull the other  team. If any men fall down the  canyon that team will find it   harder to win"
9040 PRINT INVERSE 1;AT 21,3;"PRESS ANY KEY TO START": PAUSE 0: CLS : RANDOMIZE : RETURN 

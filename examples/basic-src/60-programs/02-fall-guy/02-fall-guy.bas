   1 BORDER 0: PAPER 0: INK 7: CLS 
   2 REM @ PAUL STANLEY 1983
   5 GO SUB 9000
  15 INPUT "Please enter your names.        First, the player on the left:",b$: INPUT "And now the player on the right:"'c$
  17 PRINT AT 10,10;"PLEASE WAIT"
  20 GO SUB 8000
  30 GO SUB 7000
  40 LET y=INT (RND*19)+2: LET y1=INT (RND*19)+2
  42 LET g=7: LET g1=24: LET f=1: LET f1=1
  44 LET w$=" {90}{90}{90}{90}{90}{90}{90}{90}{90}{90}{90}{90}{90}{90}{90}{90}{90}{90}{90}"
  45 FOR i=10 TO 30: BEEP .07,i: NEXT i
  50 PRINT INK 3;AT y,4;"{92}"; INK 6;AT y1,27;"{93}"
  60 PRINT BRIGHT 1; INK 3;AT f,g;"{91}"; INK 6;AT f1,g1;"{91}"
  70 IF SCREEN$ (f+1,g)=" " THEN PRINT AT f,g;" ": LET f=f+1: PRINT AT f,g; BRIGHT 1; INK 3;"{91}": BEEP .01,10
  73 IF SCREEN$ (f+1,g)="O" THEN FOR i=3 TO 9: BEEP .01,i*5: NEXT i: PRINT AT f,g;" "; BRIGHT 1; INK 6;AT 1,7;"{91}": LET f=1: LET g=7
  75 IF SCREEN$ (f1+1,g1)=" " THEN PRINT AT f1,g1;" ": LET f1=f1+1: PRINT AT f1,g1; BRIGHT 1; INK 6;"{91}": BEEP .01,20
  76 IF SCREEN$ (f1+1,g1)="O" THEN FOR i=3 TO 9: BEEP .01,i*5: NEXT i: PRINT AT f1,g1;" "; BRIGHT 1; INK 6;AT 1,24;"{91}": LET f1=1: LET g1=24
  77 IF f=21 OR f1=21 THEN GO TO 5000
  80 IF IN 63486=253 AND y>2 THEN PRINT AT y,4;" ": LET y=y-1
  85 IF IN 61438=254 AND y1>2 THEN PRINT AT y1,27;" ": LET y1=y1-1
  90 IF IN 65022=254 AND y<20 THEN PRINT AT y,4;" ": LET y=y+1
  95 IF IN 49150=253 AND y1<20 THEN PRINT AT y1,27;" ": LET y1=y1+1
 100 IF IN 64510=254 THEN GO SUB 1000
 105 IF IN 57342=253 THEN GO SUB 2000
 110 IF IN 64510=253 THEN GO SUB 1100
 115 IF IN 57342=254 THEN GO SUB 2100
 200 LET w$=w$(2 TO )+w$(1): PRINT AT 21,6; INK 4;w$
 999 GO TO 50
1000 LET i=y-1: IF y=f THEN IF g=6 THEN IF a$(i,2)<>" " THEN RETURN 
1001 IF y=f1 THEN IF g1=6 THEN IF a$(i,2)<>" " THEN RETURN 
1002 LET a$(i)=a$(i,2 TO )+a$(i,1)
1005 IF y=f THEN IF a$(i,g-5)<>" " THEN LET g=g-1
1007 IF y=f1 THEN IF a$(i,g1-5)<>" " THEN LET g1=g1-1
1010 PRINT AT y,6;a$(i): RETURN 
1100 LET i=y-1: IF y=f THEN IF g=25 THEN IF a$(i,19)<>" " THEN RETURN 
1101 IF y=f1 THEN IF g1=25 THEN IF a$(i,19)<>" " THEN RETURN 
1102 LET a$(i)=a$(i,20)+a$(i, TO 19)
1105 IF y=f THEN IF a$(i,g-5)<>" " THEN LET g=g+1
1107 IF y=f1 THEN IF a$(i,g1-5)<>" " THEN LET g1=g1+1
1110 PRINT AT y,6;a$(i): RETURN 
2000 LET i=y1-1: IF y1=f1 THEN IF g1=6 THEN IF a$(i,2)<>" " THEN RETURN 
2001 IF y1=f THEN IF g=6 THEN IF a$(i,2)<>" " THEN RETURN 
2002 LET a$(i)=a$(i,2 TO )+a$(i,1)
2005 IF y1=f1 THEN IF a$(i,g1-5)<>" " THEN LET g1=g1-1
2007 IF y1=f THEN IF a$(i,g-5)<>" " THEN LET g=g-1
2010 PRINT AT y1,6;a$(i): RETURN 
2100 LET i=y1-1: IF y1=f1 THEN IF g1=25 THEN IF a$(i,19)<>" " THEN RETURN 
2101 IF y1=f THEN IF g=25 THEN IF a$(i,19)<>" " THEN RETURN 
2102 LET a$(i)=a$(i,20)+a$(i, TO 19)
2105 IF y1=f1 THEN IF a$(i,g1-5)<>" " THEN LET g1=g1+1
2107 IF y1=f THEN IF a$(i,g-5)<>" " THEN LET g=g+1
2110 PRINT AT y1,6;a$(i): RETURN 
5000 IF f=21 THEN LET y=f: LET x=g: LET ink=3
5002 IF f1=21 THEN LET y=f1: LET x=g1: LET ink=6
5005 LET w$="{91}{94}": LET c=1: FOR g=0 TO 16: PRINT AT y,x; BRIGHT 1; INK ink;w$(c): LET c=(c=2)+(2 AND c=1): FOR i=1 TO 3: BEEP .02,i: NEXT i: NEXT g
5006 FOR f=0 TO 31: PRINT AT 18,f;" ";AT 19,f;" ";AT 20,f;" ";AT 21,f; INK 2;" ": NEXT f
5007 FOR f=2 TO 28 STEP 2: PRINT INK 5;AT 19,f-1;" ";AT 20,f;"{91}": BEEP .1,10: PAUSE 5: PRINT AT 20,f;" "; INK 5;AT 19,f+1;"{94}": BEEP .1,20: PAUSE 5: NEXT f
5010 CLS : LET w$=(b$ AND f=21)+(c$ AND f1=21): IF f=21 AND f1=21 THEN GO TO 5050
5020 PRINT INK 4;AT 5,0;"Well done ";w$;"!"
5030 PRINT INK 6''"You were the best Fall Guy!!"
5040 GO TO 5100
5050 PRINT INK 4;AT 5,0;"The result was a draw."' INK 6''"You both did equally well."
5100 PRINT ''"Press ""X"" to quit the program."' INK 5'"Press ""1"" for the same course."' INK 4'"Press ""2"" for a new course."
5110 IF INKEY$="x" THEN STOP 
5120 IF INKEY$="1" THEN GO TO 5500
5130 IF INKEY$="2" THEN CLS : PRINT AT 10,10;"PLEASE WAIT": GO TO 20
5140 GO TO 5110
5500 CLS : FOR f=1 TO 19: LET i=INT (RND*20)+1: LET a$(f)=a$(f,i TO )+a$(f, TO i): NEXT f
5600 GO TO 30
7000 CLS : FOR f=1 TO 19: PRINT AT f+1,6;a$(f): NEXT f
7010 FOR f=2 TO 21: PRINT INK 2; PAPER 4;AT f,5;"{90}";AT f,26;"{90}": NEXT f
7020 FOR f=5 TO 26: PRINT INK 2; PAPER 4;AT 1,f;"{90}": NEXT f
7030 PRINT AT 1,7;" ";AT 1,24;" ";AT 21,16;" "
7040 PRINT BRIGHT 1; INK 3;AT 0,0;b$; INK 6;AT 0,(32-LEN c$);c$
7999 RETURN 
8000 DIM a$(19,20): FOR f=1 TO 19
8010 FOR g=1 TO 20: LET a$(f,g)=" ": IF RND>.5 THEN LET a$(f,g)="{90}"
8015 IF RND<.02 THEN LET a$(f,g)="O"
8020 NEXT g: NEXT f
8090 RETURN 
9000 FOR f=USR "a" TO USR "e"+7: READ g: POKE f,g: NEXT f
9010 DATA 170,85,170,85,170,85,170,85
9020 DATA 24,24,255,60,60,90,66,195
9030 DATA 8,12,250,137,250,12,8,0
9040 DATA 16,48,95,147,95,48,16,0
9050 DATA 153,219,126,60,60,126,219,219
9500 PRINT INK 0;AT 17,0;"  aaa  a  a   a     aa a  a a a   a   a a a   a    a   a  a a a   aaa aaa a   a    a   a  a  a    a   a a a   a    a a a  a  a    a   a a aaa aaa   aa  aa   a"
9540 FOR f=3 TO 7: FOR g=0 TO 31
9550 IF SCREEN$ (f+14,g)="a" THEN PRINT INK f;AT f+14,g;"{91}"
9555 BEEP .06,f*2+g
9560 NEXT g: NEXT f
9570 FOR f=1 TO 17: POKE 23692,255: PRINT AT 21,31;"  ": FOR g=20 TO 30: BEEP .005,g: NEXT g: NEXT f
9580 PRINT INK 4;AT 6,0;"A Game For 2 Players Who Have ToGuide Their Man To The Bottom OfThe Grid Before Their Opponent."
9590 PRINT INK 5'"Avoid The Mines (O), For LandingOn One Of These Will Send You   Right To The Top Again."
9600 PRINT INK 6'"CONTROLS: UP  DOWN  LEFT  RIGHT"
9610 PRINT '"PLAYER 1:  2    A     Q     W"
9620 PRINT INK 4'"PLAYER 2:  0    L     O     P"
9630 PRINT '"Press Any Key To Continue....": PAUSE 0
9640 FOR f=1 TO 20: POKE 23692,255: PRINT AT 21,31;"  ": FOR g=20 TO 30: BEEP .005,g: NEXT g: NEXT f
9650 RETURN 

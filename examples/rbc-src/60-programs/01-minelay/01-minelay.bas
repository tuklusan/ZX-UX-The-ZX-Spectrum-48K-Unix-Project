   1 RANDOMIZE : BORDER 0: PAPER 0: INK 7: CLS 
   5 REM @ P.Stanley (21.3.83)
  10 GO SUB 9000
  15 LET hs=0
  20 GO TO 6030
  50 BEEP .1,-10
  55 LET li=3
  60 PRINT AT 0,13;"{91}{91}    Hi-score ";hs
 100 PRINT AT y1,x1;" "; INK 6;AT y,x;a$: LET y1=y: LET x1=x
 110 LET x=x+(IN 57342=254)-(IN 57342=251): LET y=y+(IN 65278=253)-(IN 64510=254)
 120 LET a=ATTR (y,x): IF SCREEN$ (y,x)=" " THEN GO TO 700
 122 IF a=7 THEN IF a$="{92}" THEN GO TO 5000
 125 IF a=7 THEN LET y=y1: LET x=x1
 130 IF a=70 THEN BEEP .01,20: LET sc=sc+10: PRINT INK 7;AT 0,6;sc: IF sc/500=INT (sc/500) THEN PRINT AT 0,12+li; FLASH 1;"{91}": FOR g=1 TO 5: BEEP .2,-30: NEXT g: PRINT AT 0,12+li;"{91}": LET li=li+1
 140 IF a=5 THEN GO TO 6000
 150 IF a=68 THEN BEEP .1,10: LET a$="{92}"
 700 PRINT AT my,mx;" ": IF RND>sk THEN PRINT AT my1,mx1; INK 5;"{95}"
 705 LET my1=my: LET mx1=mx
 710 LET my=my+(.5 AND my<y)-(.5 AND my>y): LET mx=mx+(.5 AND mx<x)-(.5 AND mx>x)
 715 IF ATTR (my,mx)=6 THEN GO TO 6000
 720 PRINT AT my,mx; INK 5; BRIGHT 1;"{93}"
 940 IF RND<.2 THEN PRINT AT RND*18+2,RND*28+1; INK 6; BRIGHT 1;"{94}": IF RND>.9 THEN PRINT INK 4; BRIGHT 1;AT RND*18+2,RND*28+1;"{96}"
 999 GO TO 100
5000 IF y=1 OR y=21 OR x=0 OR x=30 THEN GO TO 125
5005 FOR f=50 TO 0 STEP -5: BEEP .02,f: NEXT f
5010 LET a$="{91}"
5030 GO TO 130
5500 PRINT AT 0,12+li;" ": PRINT AT y,x;" ": LET y=2: LET x=1
5600 LET my=INT (RND*11)+10: LET mx=INT (RND*18)+12: GO TO 100
6000 PRINT AT my,mx;" ": LET my=INT (RND*11)+10: LET mx=(RND*18)+12: LET my1=my: LET mx1=mx: IF a$="{92}" THEN LET a$="{91}": FOR f=0 TO 40 STEP 5: BEEP .04,f: NEXT f: GO TO 700
6005 PRINT AT y1,x1;" ": FOR f=1 TO 7: FOR g=7 TO 0 STEP -1: PRINT INK g;AT y,x;"{91}": BEEP .02,g*f: NEXT g: NEXT f
6007 LET li=li-1: IF li<>0 THEN GO TO 5500
6010 FOR g=0 TO 60: NEXT g
6020 CLS : PRINT AT 5,8; INVERSE 1;"G A M E  O V E R"
6025 PRINT AT 8,9; INK 5; BRIGHT 1;"You scored ";sc
6026 IF sc>hs THEN LET hs=sc: PRINT ''" Well done- A new high-score!!": GO TO 6030
6027 PRINT ''"      The high-score is ";hs
6030 PRINT INK 6''''"  Press 1 for a hard game, or 2        for an easier game."
6040 IF INKEY$<>"1" AND INKEY$<>"2" THEN GO TO 6040
6045 LET sk=(.7 AND INKEY$="1")+(.85 AND INKEY$="2")
6050 CLS 
7000 FOR f=1 TO 21: PRINT AT f,0;"{90}";AT 4,30;"{90}": NEXT f
7010 FOR f=1 TO 29: PRINT AT 1,4;"{90}";AT 21,4;"{90}": NEXT f
7020 FOR g=1 TO (7 AND sk=.85)+(14 AND sk=.7): LET s=RND*28: LET f=s+RND*10: LET x=INT (RND*9)*2+1: IF f>29 THEN LET f=29
7030 FOR y=s TO f: PRINT AT x,y;"{90}"
7040 NEXT y
7050 LET s=RND*17+2: LET f=s+RND*10: LET x=INT (RND*14)*2+2: IF f>20 THEN LET f=20
7060 FOR y=s TO f: PRINT AT y,x;"{90}": NEXT y: NEXT g
7390 FOR f=1 TO 20
7400 LET y=RND*18+2: LET x=RND*28+1
7410 IF SCREEN$ (y,x)="" THEN GO TO 7400
7420 PRINT BRIGHT 1; INK 6;AT y,x;"{94}": NEXT f
7500 FOR f=1 TO 10
7510 LET y=RND*18+2: LET x=RND*28+1
7520 IF SCREEN$ (y,x)="" THEN GO TO 7510
7540 PRINT INK 5;AT y,x;"{95}": NEXT f
7550 FOR f=1 TO 5: PRINT AT RND*18+2,RND*28+1; INK 4; BRIGHT 1;"{96}": NEXT f
7800 LET y=2: LET x=1: LET y1=y: LET x1=x: LET a$="{91}"
7840 LET my=INT (RND*11)+10: LET mx=INT (RND*18)+12: LET my1=my: LET mx1=mx
7850 LET sc=0: PRINT AT 0,0;"Score ";sc
7999 GO TO 50
9000 FOR f=USR "a" TO USR "g"+7: READ g: POKE f,g: NEXT f
9010 DATA 24,36,66,153,153,66,36,24,28,28,73,62,8,28,20,54
9020 DATA 220,220,73,126,72,92,20,54,195,36,24,36,126,90,129,0
9030 DATA 0,0,0,12,62,126,62,12,0,0,8,73,42,28,62,127
9040 DATA 4,14,6,12,24,48,96,0
9500 PRINT INK 0;AT 0,0;" _ _ ___ _ _ ___   _    _  _ _   _ _  _  _ _ _     _   _ _ _ _   _ _  _  _ _ ___   _   ___  _    _ _  _  _ _ _     _   _ _  _    _ _ ___ _ _ ___   ___ _ _  _"
9600 FOR f=0 TO 4: PRINT INK 5;AT 4,0; BRIGHT 1;"{93}": FOR g=1 TO 31
9610 PRINT AT f,g-1; OVER 1; INK 0; BRIGHT 1;"{93}"; INK 5;"{93}"
9620 IF SCREEN$ (f,g-1)="_" THEN PRINT INK 2; PAPER 7;AT f,g-1;"{96}"
9630 BEEP .04,(g+f)/3
9640 NEXT g: PRINT AT f,31;" ": NEXT f
9645 PLOT 16,173: DRAW 3,-10: DRAW 4,10: PLOT 80,173: DRAW 7,-28
9650 PRINT '"Move about the maze picking up  golden eggs, avoiding the mines & also the mine-layer."
9700 PRINT INK 6'"If you pick up an axe you can   destroy the maze walls, mines,  and the mine-layer."
9750 PRINT '"You begin with 3 lives, but an  extra life is given every 500   points."
9800 PRINT INK 6'" Q.....UP           Z.....DOWN"' INK 5'" I.....LEFT         P....RIGHT"
9900 INPUT "Press ENTER to start...";a$
9910 IF INKEY$="" THEN GO TO 9910
9920 CLS 
9999 RETURN 

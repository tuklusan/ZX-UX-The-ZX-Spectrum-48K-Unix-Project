   1 BORDER 5: PAPER 6: INK 0: CLS 
   2 REM @ P. STANLEY
   5 LET s1=0: LET s2=s1
   8 GO SUB 7000
  10 GO SUB 9000
  15 LET round=1
  20 GO SUB 9500
  30 GO SUB 9550
  62 PRINT AT 17,2;round
  63 BEEP .25,0: BEEP .25,0
  65 LET y=2: LET x=7: LET y1=y: LET x1=x
  70 LET g=23: LET f=17: LET f1=f: LET g1=g
  90 LET tm=3: LET ts=2
  95 LET e=0
 100 PRINT AT y1,x1;"  ";AT y1+1,x1;" ";AT y1+2,x1;"  "; INK 2;AT y,x;"{90}{92}"; PAPER 0;AT y+1,x;"{93}"; PAPER 6;AT y+2,x;"{94}{96}": LET y1=y: LET x1=x
 120 PRINT AT f1,g1;"  ";AT f1+1,g1+1;" ";AT f1+2,g1;"  ";AT f,g;"{97}{98}"; PAPER 7;AT f+1,g+1;"{93}"; PAPER 6;AT f+2,g;"{99}{9A}": LET f1=f: LET g1=g
 130 LET ts=ts-2: IF ts=0 THEN LET tm=tm-1: LET ts=60: IF tm=-1 THEN GO TO 8500
 150 PRINT AT 17,27;tm;":";("0" AND ts<10);ts
 400 IF IN 64510=254 THEN GO SUB 1000
 410 IF IN 57342=254 THEN GO SUB 1100
 450 IF g=x+1 THEN IF RND>sk THEN GO SUB 2000
 500 LET y=y+(IN 61438=239 AND y<17)-(IN 61438=247 AND y>2)
 510 LET x=x+(IN 61438=251 AND x<22)-(IN 63486=239 AND x>7)
 550 LET f=f+INT (RND*2.5)-INT (RND*2.5)+(f<y)-(f>y)
 553 IF f<2 THEN LET f=2
 555 IF f>17 THEN LET f=17
 560 LET g=g+INT (RND*2.5)-INT (RND*2.5)+(g<x+2)-(g>x+2)
 563 IF g<x+1 THEN LET g=x+1
 565 IF g>23 THEN LET g=23
 570 IF NOT e THEN IF x>20 THEN LET e=1
 580 IF e THEN LET e=e-(e-1 AND x<20)+1: IF e=10 THEN GO SUB 3000
 690 BEEP .01,-20
 700 GO TO 100
1000 PRINT INK 2;AT y,x+1;"{91}{92}": BEEP .1,20
1010 PRINT INK 2;AT y,x+1;"{92} "
1020 IF y=f+1 AND x=g-1 THEN LET s1=s1+1: BEEP .04,0: PRINT AT 8,2;s1
1030 IF s1=k2 THEN GO TO 6000
1090 RETURN 
1100 PRINT INK 2;AT y+2,x+1;"{95}{96}": BEEP .1,20
1110 PRINT INK 2;AT y+2,x+1;"{96} "
1120 IF y=f-1 AND x=g-1 THEN LET s1=s1+1: BEEP .04,0: PRINT AT 8,2;s1
1130 IF s1=k2 THEN GO TO 6000
1190 RETURN 
2000 IF f<y THEN GO TO 2100
2010 PRINT AT f,g-1;"{97}{91}": BEEP .1,30
2020 PRINT AT f,g-1;" {97}"
2030 IF f=y+1 THEN LET s2=s2+1: BEEP .04,0: PRINT AT 8,28;s2
2035 IF s2=k1 THEN GO TO 6500
2040 RETURN 
2100 PRINT AT f+2,g-1;"{99}{95}": BEEP .1,30
2110 PRINT AT f+2,g-1;" {99}"
2130 IF f=y-1 THEN LET s2=s2+1: BEEP .04,0: PRINT AT 8,28;s2
2135 IF s2=k1 THEN GO TO 6500
2140 RETURN 
3000 PRINT AT y1,x1;"  ";AT y1+1,x1;" ";AT y1+2,x1;"  "
3010 FOR x=19 TO 12 STEP -1: LET x1=x
3020 PRINT AT y1,x1; INK 2;"{90}{92}";AT y1+2,x1;"{94}{96}";AT y1+1,x1; PAPER 0; INK 2;"{93}"; PAPER 6;" "; PAPER 2; INK 6;"{93}"; PAPER 6;"{93}";AT y1,x1+2; INK 4;"{98} ";AT y1+2,x1+2;"{9A} "
3022 BEEP .02,0
3025 NEXT x
3030 PRINT AT y1,x1+2;" ";AT y1+1,x1+2;" ";AT y1+2,x1+2;" "
3040 LET e=0: RETURN 
6000 PRINT AT f,g;"{A1}{97}{98}";AT f+2,g;"{A3}{99}{9A}"; INK 2;AT f+1,g;"{A2}"; INK 0;"{8F}{8F}"; INK 6; PAPER 3;"{93}"
6010 PRINT FLASH 1;AT 1,7;"WELL BOXED- A K.O.": BEEP .2,-20
6020 GO TO 6600
6500 PRINT AT y,x-1; INK 2;"{90}{92}{9E}";AT y+2,x-1;"{94}{96}{A0}"; INK 6; PAPER 2;AT y+1,x-2;"{93}"; PAPER 6; INK 2;"{8F}{8F}"; INK 4;"{9F}"
6510 PRINT AT 1,7; FLASH 1;"BAD LUCK- A K.O.!"
6600 FOR f=1 TO 200: NEXT f
6620 CLS : IF k1=s2 OR s2>s1 THEN GO TO 6700
6630 PRINT "Well done ! You beat ";b$;" in",round;" rounds."
6640 PRINT INK 3'"The result in points was ";s1,"for you, and ";s2;" for ";b$
6650 PRINT INK 2'"I suggest you try a tougher     opponent."
6660 GO TO 6780
6700 PRINT "Bad luck ! You were beaten in ";round,"rounds."
6710 PRINT INK 3'"The result in points was ";s1,"for you, and ";s2;" for ";b$
6740 PRINT INK 2'"I suggest you try a weaker      opponent."
6780 PRINT "Here's your choice:": RESTORE 7500: PRINT : FOR f=1 TO 10: READ a$: PRINT f;"...";("." AND f<>10);a$: NEXT f
6790 INPUT INK 7; PAPER 0;"Enter your opponent's number or 0 if you've had enough.     ";x
6800 IF x=0 THEN STOP 
6810 CLS : RESTORE 7500: FOR f=1 TO x: READ a$: NEXT f: LET b$=a$(1 TO 6): PRINT "OK - You shall fight ";b$: PRINT INVERSE 1' INK 3'"PRESS ANY KEY TO START THE BOUT."
6820 PAUSE 0: CLS 
6830 LET s1=0: LET s2=s1: LET sk=(11-x)/12: LET k2=10+INT (RND*6): LET k1=16-x+INT (RND*10): GO TO 15
7000 RESTORE 7500
7100 PRINT AT 10,0;"Enter your name(up to 6 letters)": INPUT c$: IF LEN c$>6 THEN GO TO 7100
7200 CLS 
7500 DATA "Henry Hopeless","Arnold Awful","Nigel No-Good","Philip Fair","Andrew Average","Roger Right-Hook","Brian Brick-Wall","Simon Super","Edward Excellent","Flynn Fantastic"
7510 PRINT INVERSE 1;"    C H A M P I O N S H I P               B O X I N G           "; INVERSE 0;"         @ PAUL STANLEY"
7520 PRINT INK 3'"So you want to be a champion do you?  If so this is the game foryou."; INK 2'"Which opponent do you wish to   fight first?"
7530 PRINT : FOR f=1 TO 10: READ a$: PRINT INK 1;f;"...";("." AND f<>10);a$: NEXT f
7540 INPUT x: IF x<1 OR x>10 THEN GO TO 7540
7545 LET sk=(11-x)/12
7546 LET k2=10+x+INT (RND*6): LET k1=16-x+INT (RND*10)
7550 RESTORE 7500: FOR f=1 TO x: READ a$: NEXT f: LET b$=a$(1 TO 6)
7560 CLS : PRINT "Very well, your opponent will be";a$' INK 2'"Each bout you fight is only 3   rounds. Move about the ring with5-8, and punch with Q(left hand)and P(right hand). Note that youcan move and punch at the same  time."
7570 PRINT ' INK 1;"Only punches to the head score  and K.O.s are possible."
7580 PRINT ' INVERSE 1;"PRESS ANY KEY TO START THE BOUT.": PAUSE 0: CLS 
7590 RETURN 
8500 PRINT AT 17,27;"0:00"
8505 BEEP .25,0: BEEP .25,0
8510 LET round=round+1: IF round =4 THEN LET round=3: GO TO 6620
8520 PRINT AT 21,0;"Prepare to fight the next round."; INK 6; PAPER 0;AT 2,7;"{93}";AT 19,24;"{93}": FOR i=1 TO 20
8525 LET y=y-(y>2): LET x=x-(x>7)
8530 PRINT AT y1,x1;"  ";AT y1+1,x1;" ";AT y1+2,x1;"  "; INK 2;AT y,x;"{90}{92}"; PAPER 0;AT y+1,x;"{93}"; PAPER 6;AT y+2,x;"{94}{96}": LET y1=y: LET x1=x
8535 LET f=f+(f<17): LET g=g+(g<23)
8540 PRINT AT f1,g1;"  ";AT f1+1,g1+1;" ";AT f1+2,g1;"  ";AT f,g;"{97}{98}"; PAPER 7;AT f+1,g+1;"{93}"; PAPER 6;AT f+2,g;"{99}{9A}": LET f1=f: LET g1=g
8542 IF ATTR (2,7)=50 THEN IF ATTR (19,24)=48 THEN GO SUB 9550: FOR f=-1 TO 2: PRINT AT y1+f,x1;" ": NEXT f: PRINT AT 21,0;"                                ": GO TO 62
8545 BEEP .1,-18: NEXT i
9000 RESTORE 9010: LET f=0: LET g=255: FOR y=USR "a" TO USR "t"+7: READ x: POKE y,x: NEXT y
9010 DATA f,63,127,g,g,252,254,254,f,g,g,g,g,f,f,f,28,254,254,254,254,28,f,f
9020 DATA 195,129,f,f,f,f,129,195,254,254,252,g,g,127,63,f,f,f,f,g,g,g,g,f
9030 DATA f,f,28,254,254,254,254,28,56,127,127,127,127,56,f,f
9035 DATA f,252,254,g,g,63,127,127,f,f,56,127,127,127,127,56,127,127,63,g,g,254,252,f
9045 DATA 66,129,157,165,165,94,66,60,60,60,24,24,60,126,g,g,108,108,108,40,40,40,40,108
9050 DATA 28,30,15,15,31,62,126,252,248,240,240,224,224,240,240,248,252,126,62,31,15,15,30,28
9060 DATA 56,120,240,240,248,124,126,63,31,15,15,7,7,15,15,31,63,126,124,248,240,240,120,56
9100 RETURN 
9500 INK 4: FOR f=0 TO 7 STEP 2: PLOT 55-f,15-f: DRAW 0,145+2*f: DRAW 145+2*f,0: DRAW 0,-2*f-145: DRAW -2*4-145,0: NEXT f
9510 PRINT INK 3; BRIGHT 1;AT 1,6;"{8F}";AT 1,25;"{8F}";AT 20,6;"{8F}";AT 20,25;"{8F}"
9520 INK 0
9525 PRINT AT 4,0;c$;AT 4,26;b$
9530 PRINT AT 6,0; INK 2;"POINTS"; INK 0;AT 6,26;"POINTS"; INK 3;AT 15,0;"ROUND";AT 15,27;"TIME"
9540 PRINT AT 8,2;s1;AT 8,28;s2
9545 RETURN 
9550 LET y1=16: LET x1=9: RESTORE 9560: FOR f=1 TO 4: READ y,x
9560 DATA 0,1,-1,0,0,-1,1,0
9570 FOR e=1 TO 12: PRINT AT y1,x1;"{9B}";AT y1+1,x1;"{9C}";AT y1+2,x1;"{9D}"; PAPER 2; INK 7;AT y1-1,x1;round
9580 BEEP .06,-45
9585 IF e=12 THEN FOR o=25 TO 35: BEEP .005,o: NEXT o: FOR o=1 TO 20: NEXT o: FOR o=35 TO 25 STEP -1: BEEP .005,o: NEXT o
9590 PRINT AT y1,x1;" ";AT y1+1,x1;" ";AT y1+2,x1;" ";AT y1-1,x1;" "
9600 LET y1=y1+y: LET x1=x1+x: NEXT e: NEXT f
9610 RETURN 

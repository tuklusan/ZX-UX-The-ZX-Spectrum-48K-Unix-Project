   1 REM ------- T A N X -------
   2 REM --- @  PAUL STANLEY ---
   5 RANDOMIZE 
  10 BORDER 0: INK 7: PAPER 0: CLS 
  12 GO SUB 7000
  15 LET sc1=0: LET sc2=sc1
  20 GO SUB 9000
  30 LET c=0: GO SUB 8000
  35 IF RND>.5 THEN LET c=c+1: GO SUB 700
  40 GO SUB 100
  44 LET c=c+1
  45 IF c=8 THEN CLS : GO TO 30
  46 GO SUB 700
  47 LET c=c+1
  48 IF c=8 THEN CLS : GO TO 30
  50 GO TO 40
 100 PRINT FLASH 1;AT 21,12;"PLAYER 1": INPUT "ENTER ELEVATION (0{CC}90)   ";a
 110 IF a>90 OR a<0 THEN GO TO 100
 115 INPUT "ENTER VELOCITY (2{CC}10)   ";v
 120 IF v<2 OR v>10 THEN GO TO 115
 121 LET s1=f1
 124 LET o1=f1
 130 LET max=100+5*v
 140 LET e=a/10
 160 FOR g=8 TO 255 STEP v
 175 IF s1>0 THEN IF s1<175 THEN IF g>10 THEN IF POINT (g,s1)=1 THEN LET k=g: BEEP .2,0: BEEP .2,-15: GO TO 200
 177 IF s1>0 THEN IF s1<175 THEN PLOT g,s1
 180 LET s1=s1+(e AND g<max)-(e AND g>=max)
 190 LET e=e-(e/8 AND g<max)+(e/4 AND g>=max)
 191 NEXT g
 195 LET k=255
 200 LET s1=21.5-s1/8: IF (INT s1=q2 AND k>247) OR ATTR (q2,31)=71 THEN GO TO 1000
 205 LET e=a/10: FOR g=8 TO 255 STEP v
 210 IF g=k THEN RETURN 
 220 IF o1>0 THEN IF o1<175 THEN PLOT OVER 1;g,o1
 230 LET o1=o1+(e AND g<max)-(e AND g>=max)
 240 LET e=e-(e/8 AND g<max)+(e/4 AND g>=max)
 250 NEXT g
 260 RETURN 
 488 IF c=9 THEN CLS : GO TO 30
 700 PRINT FLASH 1;AT 21,12;"PLAYER 2": INPUT "ENTER ELEVATION (0{CC}90)   ";a
 710 IF a>90 OR a<0 THEN GO TO 700
 715 INPUT "ENTER VELOCITY (2{CC}10)   ";v
 720 IF v<2 OR v>10 THEN GO TO 715
 721 LET s1=f2
 724 LET o1=f2
 730 LET max=155-5*v
 740 LET e=a/10
 760 FOR g=247 TO 0 STEP -v
 775 IF s1>0 THEN IF s1<175 THEN IF g<239 THEN IF POINT (g,s1)=1 THEN LET k=g: BEEP .2,0: BEEP .2,-15: GO TO 800
 777 IF s1>0 THEN IF s1<175 THEN PLOT g,s1
 780 LET s1=s1+(e AND g>max)-(e AND g<=max)
 790 LET e=e-(e/8 AND g>max)+(e/4 AND g<=max)
 791 NEXT g
 795 LET k=0
 800 LET s1=21.5-s1/8: IF INT (s1=q1 AND k<8) OR ATTR (q1,0)=71 THEN GO TO 2000
 805 LET e=a/10: FOR g=247 TO 0 STEP -v
 810 IF g=k THEN RETURN 
 820 IF o1>0 THEN IF o1<175 THEN PLOT OVER 1;g,o1
 830 LET o1=o1+(e AND g>max)-(e AND g<=max)
 840 LET e=e-(e/8 AND g>max)+(e/4 AND g<=max)
 850 NEXT g
 860 RETURN 
1000 PRINT AT q2,31;" "
1010 FOR f=1 TO 50: BEEP .002,RND*25: PLOT 255-RND*20,(21-q2)*8+RND*15: NEXT f
1030 LET sc1=sc1+1
1040 GO TO 2500
2000 PRINT AT q1,0;" "
2010 FOR f=1 TO 100: BEEP .002,RND*25: PLOT 0+RND*20,(21-q1)*8+RND*15: NEXT f
2030 LET sc2=sc2+1
2040 GO TO 2500
2500 CLS : PRINT AT 10,5;"PLAYER 1 HAS ";sc1;" POINT";("S" AND sc1<>1);AT 13,5;"PLAYER 2 HAS ";sc2;" POINT";("S" AND sc2<>1)
2510 IF sc1+sc2=7 THEN PRINT AT 16,8; FLASH 1;"G A M E  O V E R"; FLASH 0;AT 19,2;"PRESS ANY KEY TO PLAY AGAIN": PAUSE 0: CLS : LET sc1=0: LET sc2=sc1: GO TO 30
2520 PAUSE 200: CLS : GO TO 30
7000 LET q1=0: LET q2=10: LET e=21: LET v=31: FOR f=21 TO 1 STEP -1
7010 PRINT INK 4;AT f,q1;"T";AT f,q2; INK 5;"A"; INK 6;AT f,e;"N"; INK 7;AT f,v;"X"
7020 BEEP .03,f
7025 IF f>1 THEN PRINT AT f,q1;" ";AT f,q2;" ";AT f,e;" ";AT f,v;" "
7030 LET q1=q1+.6: LET q2=q2+.2: LET e=e-.25: LET v=v-.65
7040 NEXT f
7050 PRINT "The 2 players take it in turn toenter the angle and velocity at which they want to fire to try  and hit their opponent."
7060 PRINT "The shells must be fired over   the hills but if you are lucky  your shell may be able to go    through a hill (particularly at the higher speeds.)"
7070 PRINT "To stand the best chance of     hitting your opponent try to    use the smallest possible angle of elevation."
7077 PRINT "The flashing caption at the     bottom of the screen indicates  whose go it is."
7080 PRINT "PRESS ANY KEY TO START"
7090 PAUSE 0: CLS : RETURN 
8000 LET q=18-RND*13
8010 FOR f=2 TO 29
8020 FOR g=21 TO q STEP -1
8030 PRINT INK 3; PAPER 5;AT g,f;"{92}"+("{92}{92}" AND f=29);AT g,f-2;("{92}{92}" AND f=2)
8040 NEXT g
8050 LET q=q+RND*4-RND*4
8060 IF q<3 THEN LET q=4+RND*2
8065 IF q>20 THEN LET q=20
8070 NEXT f
8100 FOR f=1 TO 21
8110 IF SCREEN$ (f,0)<>" " THEN PRINT INK 4;AT f-1,0; BRIGHT 1;"{90}"
8114 IF SCREEN$ (f,0)<>" " THEN LET f1=(21-f)*8+16: LET q1=f-1: GO TO 8116
8115 NEXT f
8116 FOR f=1 TO 21: IF SCREEN$ (f,31)<>" " THEN PRINT INK 4;AT f-1,31; BRIGHT 1;"{91}"
8117 IF SCREEN$ (f,31)<>" " THEN LET f2=(21-f)*8+16: LET q2=f-1: RETURN 
8120 NEXT f
9000 FOR f=USR "a" TO USR "c"+7: READ g: POKE f,g: NEXT f
9010 DATA 0,1,2,60,56,255,255,127,0,128,64,60,28,255,255,127
9020 DATA 170,85,170,85,170,85,170,85
9100 RETURN 

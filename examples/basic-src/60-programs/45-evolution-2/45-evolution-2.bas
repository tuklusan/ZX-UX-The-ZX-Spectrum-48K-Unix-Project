   1 REM *EVOLUTIN 2*
   5 BORDER 0: INK 7: PAPER 0: CLS 
  10 PRINT '"If you have tried the previous  program this will be the 4th    stage in the evolution sequence."
  20 PRINT INK 6'"If you haven't then the object  is to evolve as far as possible in a role-playing series of     different programs."
  30 PRINT INK 5'"In this stage you play the part of a gorilla who competes       against a smaller monkey who is faster than you."
  40 PRINT INK 4'"You have to eat only 10 out of  40 bananas which are placed in  the forest in random positions, but the monkey likes bananas as well!"
  50 PRINT '"Press ENTER to continue.": PAUSE 0: CLS 
  60 PRINT '"Move with 5-8 but note that you cannot go through the trees."
  70 PRINT INK 6'"You pick up a banana by aligningthe top half of your body with  the banana."
  80 PRINT ' INK 5'"Press ENTER to start.": PAUSE 0: PAPER 4: INK 0: CLS 
  90 RESTORE 110
 100 FOR f=USR "a" TO USR "h"+7: READ g: POKE f,g: NEXT f
 110 DATA 64,99,101,51,63,31,13,7,0,192,160,192,248,252,190,231
 120 DATA 7,7,7,14,12,12,12,28,227,225,224,112,48,48,48,56
 130 DATA 2,2,6,14,28,56,240,0,25,25,255,188,152,60,36,102
 140 DATA 247,195,129,1,0,128,129,195,231,231,231,231,231,231,231,231
 200 FOR f=0 TO 31: PRINT AT 0,f; INK 4; PAPER 2;"{96}";AT 20,f;"{96}";; PAPER 1;AT 1,f;"{97}";AT 21,f;"{97}": NEXT f
 210 FOR f=2 TO 18 STEP 2: PRINT INK 4; PAPER 2;AT f,0;"{96}{96}";AT f,30;"{96}{96}";AT f+1,0; PAPER 1;"{97}{97}";AT f+1,30;"{97}{97}": NEXT f
 220 RANDOMIZE 
 230 FOR f=1 TO 12: LET x=RND*27+2: LET y=RND*16+2: PRINT PAPER 2; INK 4;AT y,x;"{96}";AT y+1,x; PAPER 1;"{97}": NEXT f
 240 LET g=2: LET f=2: LET g1=g: LET f1=f: LET y=18: LET x=28: LET y1=y: LET x1=x
 250 LET b=40: LET s=0
 260 LET by=INT (RND*15+2): LET bx=INT (RND*26+2)
 265 IF SCREEN$ (by,bx)<>" " THEN GO TO 260
 270 PRINT INK 6;AT by,bx;"{94}"
 280 PRINT INK 7;AT 0,3;b;AT 0,28;s
 300 PRINT AT y1,x1;"  ";AT y1+1,x1;"  ";AT y,x;"{90}{91}";AT y+1,x;"{92}{93}";AT f1,g1;" ";AT f,g;"{95}"; INK 6;AT by,bx;"{94}"
 320 IF y=by THEN IF x=bx OR x+1=bx THEN GO SUB 650
 330 IF f=by THEN IF g=bx THEN LET b=b-1: PRINT AT 0,3; INK 7;b;" ": BEEP .1,-10: GO SUB 655
 335 LET y1=y: LET x1=x
 340 LET f1=f: LET g1=g
 350 LET y=y+(INKEY$="6" AND y<18)-(INKEY$="7" AND y>2): LET x=x+(INKEY$="8" AND x<28)-(INKEY$="5" AND x>2)
 360 IF ATTR (y,x)<23 OR ATTR (y+1,x)<23 OR ATTR (y,x+1)<23 OR ATTR (y+1,x+1)<23 THEN LET y=y1: LET x=x1
 380 LET f=f+(f<by)-(f>by): LET g=g+(g<bx)-(g>bx)
 390 IF ATTR (f,g)<23 THEN LET f=INT (f1+RND*1.5-RND*1.5): LET g=INT (g1+RND*1.5-RND*1.5): GO TO 390
 500 GO TO 300
 650 LET s=s+1: LET b=b-1: PRINT INK 7;AT 0,3;b;" ";AT 0,28;s
 652 BEEP .1,10
 655 IF s=10 THEN GO TO 800
 657 IF b=0 THEN GO TO 700
 660 LET by=INT (RND*15+2): LET bx=INT (RND*26+2)
 670 PRINT INK 6;AT by,bx;"{94}"
 680 RETURN 
 700 BORDER 0: PAPER 0: INK 7: CLS 
 710 PRINT '"Bad luck! You are not fast      enough to progress any further  in evolution."
 760 GO TO 1810
 800 BORDER 0: INK 7: PAPER 0: CLS : PRINT '"Well done! You managed to eat   the bananas before you starved  and therefore you can proceed   to the next stage."
 900 GO TO 1810
1000 PRINT '"The object here is to stop othercavemen from attacking yor cave"' INK 5'"Your cave is in the middle of 8 others, and from any of these   can come rivals who are preparedto kill you in order to steal   your property."
1010 PRINT INK 5'"You can spin round with 6 and 7 and throw a spear with 0. You   have successfully defended your cave when 30 attacks have been  made. However, you are given 3  lives to make your task easier."
1020 PRINT INK 4'"Press ENTER to start."
1030 PAUSE 0: CLS 
1040 RESTORE 1050: FOR f=USR "a" TO USR "i"+7: READ g: POKE f,g: NEXT f
1050 DATA 8,28,8,8,8,8,8,8,0,6,6,8,16,32,64,0,0,0,2,255,2,0,0,0,0,64,32,16,8,6,6,0
1060 DATA 8,8,8,8,8,8,28,8,0,2,4,8,16,96,96,0,0,0,64,255,64,0,0,0,0,96,96,16,8,4,2,0
1070 DATA 28,28,8,62,8,28,20,20
1075 FOR f=1 TO 6: READ s,c: PRINT AT s,c; INK RND*5+2;AT 9,0;"  ";TAB 30;"  ";AT 11,0;"  ";TAB 30;"  "
1077 DATA 1,5,1,14,1,23,20,3,20,25,20,14
1079 PRINT INK 4;AT 8,14;"   ";AT 9,13;"     ";AT 11,13;"     ";AT 12,14;"   "
1080 LET q=1
1085 PRINT AT 0,0;"LIVES: {98}{98}"
1090 LET a$="{90}{91}{92}{93}{94}{95}{96}{97}": LET a=1: LET s=0: LET c=0
1091 LET k=0
1092 PRINT AT 0,21;"ATTEMPTS:";c: IF c=30 THEN GO TO 1700
1095 GO SUB (INT (RND*8)*10)+1400
1100 PRINT AT 10,15; INK 4;a$(a)
1110 PRINT AT y,x;" ": LET y=y+dy: LET x=x+dx: PRINT AT y,x; INK 5;"{98}"
1115 IF y=10 THEN IF x=15 THEN GO TO 1600
1120 IF s THEN PRINT AT f,g;" ": LET f=f+dy2: LET g=g+dx2: PRINT AT f,g; INK 3;b$
1130 IF s THEN IF (f=y AND x=g) OR (f+dy2=y AND g+dx2=x) THEN PRINT AT f,g;" ": FOR w=7 TO 0 STEP -1: PRINT INK w;AT y,x;"{98}": BEEP .02,f: NEXT w: LET s=0: LET c=c+1: GO TO 1092
1140 BEEP 1/(c+20),(y+x)/2
1200 LET a=a+(INKEY$="7" AND a<8)-(7 AND INKEY$="7" AND a=8)-(INKEY$="6" AND a>1)+(7 AND INKEY$="6" AND a=1)
1210 IF INKEY$="0" THEN IF s=0 THEN LET b$=a$(a): LET f=10: LET g=15: LET s=1: GO SUB 1510+a*10
1300 GO TO 1100
1400 LET y=q: LET x=6: LET dy=q: LET dx=q: RETURN 
1410 LET y=q: LET x=15: LET dy=q: LET dx=0: RETURN 
1420 LET y=q: LET x=24: LET dy=q: LET dx=-q: RETURN 
1430 LET y=10: LET x=31: LET dy=0: LET dx=-q: RETURN 
1440 LET y=21: LET x=26: LET dy=-q: LET dx=-q: RETURN 
1450 LET y=21: LET x=15: LET dy=-q: LET dx=0: RETURN 
1460 LET y=21: LET x=4: LET dy=-q: LET dx=q: RETURN 
1470 LET y=10: LET x=0: LET dy=0: LET dx=q: RETURN 
1520 LET dy2=-1: LET dx2=0: RETURN 
1530 LET dy2=-1: LET dx2=1: RETURN 
1540 LET dy2=0: LET dx2=1: RETURN 
1550 LET dy2=1: LET dx2=1: RETURN 
1560 LET dy2=1: LET dx2=0: RETURN 
1570 LET dy2=1: LET dx2=-1: RETURN 
1580 LET dy2=0: LET dx2=-1: RETURN 
1590 LET dy2=-1: LET dx2=-1: RETURN 
1600 PRINT AT f,g;" "; FLASH 1;AT y,x;"{98}": FOR f=1 TO 20: BEEP .01,f: BEEP .01,10-f: NEXT f: PRINT AT y,x;a$(a): LET k=k+1: PRINT AT 0,k+6;" "
1605 IF k=3 THEN GO TO 1800
1607 LET s=0
1610 GO TO 1092
1700 CLS : PRINT "Well done! Defending your cave  was not easy, but you did very  well and you can evolve further if  you wish to."
1710 GO TO 1810
1800 CLS : PRINT "Bad luck! You failed in your    attempt to defend your cave."
1810 PRINT INK 4'"Press the key which corresponds to what you want to do next."
1820 PRINT INK 5'"1...Start the gorilla stage."''"2...Start the caveman stage."''"3...Load the 6th stage."''"4...Exit from the program."
1830 IF INKEY$="" THEN GO TO 1830
1840 IF INKEY$="1" THEN CLS : GO TO 30
1850 IF INKEY$="2" THEN CLS : GO TO 1000
1860 IF INKEY$="3" THEN LOAD ""
1870 IF INKEY$="4" THEN STOP 
1880 GO TO 1830

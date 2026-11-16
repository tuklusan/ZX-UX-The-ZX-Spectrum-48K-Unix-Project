   1 REM HELI-BOMBER @ R.Erskine 1983
  10 BORDER 0: PAPER 0: INK 7: CLS 
  20 LET sc=0: LET hs=0
  30 PRINT AT 0,9;"HELI-BOMBER": PRINT 
  40 PRINT : PRINT "Your city is under attack by ","helicopter bombers.  When a bombhas a clear path through to the ground or when your laser tower is destroyed the game ends"
  50 PRINT : PRINT "Move your laser sight using the arrow keys and try to shoot downthe bombs using the 0 key"
  60 PRINT : PRINT AT 20,0;"Press any key to start"
  70 IF INKEY$="" THEN GO TO 70
  80 GO SUB 2500
 100 LET lin=lin+(2 AND INKEY$="6" AND lin<13)
 105 IF ATTR (21,15)=0 THEN GO TO 3000
 120 LET col=col-(2 AND INKEY$="5"): IF col<0 THEN LET col=31
 130 LET lin=lin-(2 AND INKEY$="7" AND lin>0)
 140 LET col=col+(2 AND INKEY$="8"): IF col>31 THEN LET col=0
 150 PRINT INK 4;AT ln,cl;" ";AT lin,col;"+": LET ln=lin: LET cl=col
 160 IF col1=30 THEN LET col1=0: LET lin1=INT (RND*10)+1
 161 LET lin1=lin1+(1 AND RND>.7 AND lin1<13)
 170 LET lin1=lin1+(1 AND RND>.7 AND lin1<13)
 180 LET lin1=lin1-(1 AND RND>.7 AND lin1>0)
 190 LET col1=col1+(1 AND col1<30)
 200 PRINT INK 0; PAPER 0;AT ln1,cl1;"  ";AT ln1+1,cl1;"  "; PAPER 0; INK 5;AT lin1,col1;"__";AT lin1+1,col1;"{93}{94}": LET ln1=lin1: LET cl1=col1
 210 IF g=1 AND RND>.8 THEN LET lin2=lin1+2: LET col2=col1: LET g=-g: LET ln2=lin1+2: LET cl2=col2
 215 IF g=1 THEN GO TO 270
 220 LET lin2=lin2+1
 250 PRINT INK 0; PAPER 0;AT ln2,cl2;" "; INK 7;AT lin2,col2;"{95}": LET ln2=lin2: LET cl2=col2: BEEP .01,-10: IF lin2=21 THEN GO TO 3000
 260 IF ATTR (lin2+1,col2)=3 THEN PRINT PAPER 0; INK 0;AT lin2,col2;" "; PAPER 7;AT lin2+1,col2;"{95}"; PAPER 0;AT lin2+1,col2;" ": LET g=-g
 270 IF INKEY$<>"0" THEN GO TO 100
 280 LET x=122: LET y=42: PLOT INK 6;x,y
 290 LET xx=col*8: LET yy=lin*8-172
 300 LET yy=-yy
 310 DRAW OVER 1; INK 6;xx-x,yy-y
 320 IF ATTR (lin1+1,col1)=6 THEN LET b=-b
 330 IF ATTR (lin2,col2)=6 THEN LET b=-b
 340 PLOT OVER 1; INK 6;x,y: DRAW OVER 1;xx-x,yy-y
 350 IF b=-1 THEN GO SUB 380
 360 IF h=-1 THEN GO SUB 400
 370 GO TO 100
 380 FOR x=1 TO 10: BEEP .05,x+15: PRINT FLASH 1; PAPER 2; INK 6;AT lin2,col2;"*": NEXT x
 390 PRINT INK 0; PAPER 0;AT lin2,col2;" ": LET sc=sc+10: LET g=-g:: LET b=-b: RETURN 
 400 FOR x=lin1 TO 20
 410 PRINT AT ln1,cl1;"  ";AT ln1+1,cl1;"  "
 420 PRINT FLASH 1; PAPER 2; INK 6;AT lin1,col1;"  ";AT lin1+1,col1;"{93}{94}"
 430 LET ln1=lin1: LET cl1=col1: LET lin1=lin1+1
 440 BEEP .01,x
 450 NEXT x
 460 PRINT AT lin1,col1;"  ";AT lin+1,col1;"  ": IF ATTR (21,15)=0 THEN GO TO 3000
 470 LET lin1=0: LET col1=INT (RND*31)
 480 LET h=-h
 490 RETURN 
2499 STOP 
2500 RESTORE : FOR x=USR "a" TO USR "f"+7
2510 READ n: POKE x,n
2520 NEXT x
2530 DATA 255,165,165,255,165,165,165,255,24,126,126,126,60,24,24,255,129,195,165,153,153,165,195,129,0,0,195,255,15,7,0,0,128,128,224,152,252,248,0,0,195,195,36,24,24,36,195,195
2540 PRINT AT 0,4;"HELI-BOMBER"
2600 GO TO 9000
3000 PRINT INK 5;AT 10,10;"END OF GAME";AT 12,7;"Your score was ";sc: IF sc>hs THEN LET hs=sc
3001 PRINT INK 5;AT 14,9;"High score ";hs
3005 FOR x=1 TO 300: NEXT x
3010 PRINT AT 16,4;"Press any key to restart"
3020 IF INKEY$="" THEN GO TO 3020
3030 LET sc=0
3040 GO SUB 9000
3050 GO TO 100
9000 BORDER 0: PAPER 0: RANDOMIZE : INK 7: CLS 
9010 FOR x=0 TO 31
9020 LET r=INT (RND*5)+1+16
9030 FOR y=r TO 21
9040 PRINT INK 3;AT y,x;"{90}"
9050 NEXT y
9060 NEXT x
9070 PRINT INK 6;AT 16,15;"{91}"
9080 FOR x=17 TO 21
9090 PRINT INK 6;AT x,15;"{92}"
9100 NEXT x
9200 LET lin=10: LET col=15: PRINT INK 6;AT lin,col;"+"
9210 LET lin1=0: LET col1=INT (RND*31): LET ln=lin: LET cl=col
9220 PRINT INK 0; PAPER 5;AT lin1,col1;"__"; PAPER 0; INK 5;AT lin1+1,col1;"{93}{94}"
9225 LET ln1=lin1: LET cl1=col1
9230 LET g=1: LET h=1: LET b=1
9300 RETURN 

   1 REM R.Holmes Leeds
   2 BORDER 0: PAPER 0: INK 7: CLS 
   3 FOR j=144 TO 147: FOR k=0 TO 7
   4 READ z: POKE USR (CHR$ j)+k,z
   5 NEXT k: NEXT j
   6 LET hs=0
   7 DATA 16,56,16,56,84,16,40,40,0,0,36,24,24,36,0,0
   8 DATA 42,65,127,73,28,34,34,99,161,18,64,158,5,80,72,221
   9 CLS 
  10 GO SUB 20
  11 GO SUB 3000
  12 GO TO 40
  20 RESTORE 30
  21 FOR i=1 TO 8: READ h,j: BEEP h,j
  22 NEXT i
  23 FOR k=.1 TO 0 STEP -.01: BEEP k,28: NEXT k
  24 RETURN 
  30 DATA .1,11,.1,11,.8,16,.05,11,.05,16,.05,11,.05,16,1,20
  31 REM Mon Cresta Music subroutine {7F}Ron Smith (PCW) 9/9/82
 100 LET n=2
 110 LET s=0: LET ms=3
 120 GO SUB 500
 130 IF n<100 THEN LET n=n+(11-q)
 140 DIM a(n)
 150 DIM b(n)
 160 FOR f=1 TO n
 170 LET a(f)=INT (RND*20)+1
 180 LET b(f)=INT (RND*30)+1
 185 BEEP .005,a(f)
 190 IF (a(f)=10 OR a(f)=11 OR a(f)=12) AND (b(f)=14 OR b(f)=15 OR b(f)=16) THEN GO TO 170
 200 NEXT f
 210 LET x=10: LET y=15
 220 LET d=0
 230 PRINT AT 0,3; INK 6;"Score:"
 231 PRINT AT 21,13; INK 4;"Men:"; INK 6;ms
 235 PRINT AT 0,20; INK 6;"Robots:"
 240 FOR f=1 TO n
 241 IF d=n THEN GO TO 1000
 245 IF a(f)=0 AND b(f)=0 THEN GO TO 360
 250 PRINT AT a(f),b(f);" "
 260 PRINT AT x,y;" "
 265 PRINT AT 0,9; INK 6;s
 266 PRINT AT 0,27; INK 6;n-d;"/"
 270 LET x=x+(INKEY$="v")-(INKEY$="t")
 280 LET y=y+(INKEY$="g")-(INKEY$="f")
 290 LET a(f)=a(f)+(a(f)<x)-(a(f)>x)
 300 LET b(f)=b(f)+(b(f)<y)-(b(f)>y)
 310 IF ATTR (x,y)=4 THEN GO TO 2000
 311 IF ATTR (x,y)=6 THEN GO TO 2000
 312 IF ATTR (x,y)=2 THEN GO TO 2000
 320 IF ATTR (a(f),b(f))=4 THEN LET s=s+(10*n): PRINT AT a(f),b(f); INK 2;"{93}": LET d=d+1: BEEP .5,-7: BEEP .2,28: PRINT AT a(f),b(f); INK 4;"x": BEEP .2,-29: LET a(f)=0: LET b(f)=0: GO TO 360
 330 BEEP .01,-15: BEEP .005,-17
 340 FOR u=1 TO 5: PRINT AT x,y; INK 5;"{90}": PRINT AT a(f),b(f); INK 2;"{92}": NEXT u
 350 IF ATTR (x,y)=2 THEN GO TO 2000
 360 NEXT f
 370 GO TO 240
 499 STOP 
 500 CLS : INK 4
 510 FOR f=0 TO 31: PRINT AT 0,f;"/";AT 21,f;"/": NEXT f
 520 FOR f=0 TO 21: PRINT AT f,0;"/";AT f,31;"/": NEXT f
 530 FOR i=1 TO (q*5): LET f1=INT (RND*20)+1: LET f2=INT (RND*30)+1: PRINT AT f1,f2;"{91}": NEXT f
 535 FOR f=1 TO (11-q)*2: LET f1=INT (RND*20)+1: LET f2=INT (RND*30)+1: PRINT AT f1,f2; INK 6;"{91}": NEXT f
 540 INK 7: RETURN 
1000 CLS : FOR u=7 TO 0 STEP -1: BEEP .01,(u*7): BORDER u: NEXT u: PRINT AT 0,10;"YOU WIN": PRINT AT 10,10;"Score:";s: GO SUB 20: CLS : GO TO 120
1008 LET n=q
2000 PRINT AT x,y; INK 2;"{93}": PAUSE 200: CLS : PRINT AT 10,5;"You Are Dead!!"
2001 FOR v=10 TO -10 STEP -1: BEEP .05,v: BEEP .05,v*2: NEXT v
2002 LET ms=ms-1: IF ms=0 THEN GO TO 2010
2003 INPUT ''''''''''''''''''"Start?"'k$
2004 GO TO 120
2010 CLS : PRINT "All your men are DEAD!!": PRINT "You scored ";s;" points"
2011 IF s>hs THEN PRINT "You got the highscore": LET hs=s
2012 IF hs<>s THEN PRINT "You were not good enough to get the highscore"
2013 PRINT : PRINT INK 5; FLASH 1;AT 5,5;"High"; FLASH 0;" "; FLASH 1;hs
2020 INPUT "AGAIN";a$
2030 IF a$="n" THEN STOP 
2040 GO TO 9
3000 PRINT "   Robot Chase"
3010 PRINT : PRINT " Oh no not another robot ruled  game?Well yes it is.You are the unfortunate being who is pursuedby the killer robots on an alienplanet.Your only means of escapeis to lure the robot hordes intothe lethal anti-mat mines."
3020 PRINT : PRINT " But you must not step on these  mines yourself or you will die."
3030 PRINT : PRINT "GOOD LUCK BRAVE HUMAN"
3040 PRINT : PRINT " {90} - You"
3050 PRINT " {91} - Mine"
3060 PRINT " {92} - Robot"
3070 PRINT : PRINT "Guiding robots into mines also  scores points"
3071 PRINT "Use the 'T,F,G,V' keys to move"
3072 PRINT : PRINT "Watch out for dangerous yellow  mines '{91}', which don't effect   robots."
3080 INPUT "Level 1(hard)-10(easy)";q
3090 IF q>10 OR q<1 THEN PRINT "Are you a dopper or do you just train to be one?": GO TO 3080
3100 CLS : RETURN 

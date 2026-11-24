   1 REM NEMARKET ....... WALWYN
   2 REM HORSERACE GAME
   5 DIM a(7): DIM b(7): DIM x(7): DIM y(7):
  10 LET c=0
  15 BORDER 0
  20 PAPER 7
  25 INK 0
  30 LET slo=3: REM *factor to slow movements increased
  40 GO SUB 1000
  50 GO SUB 3000
  85 INK 0
  90 CLS 
  92 FOR x=0 TO 6: INK x
  93 PRINT AT 2+X*3,0;STR$ (X+1);" {93}{94}"
  94 NEXT X
  95 INK 0: FOR X=0 TO 21: PRINT AT X,30;" ": NEXT X
  96 INK 0: PRINT AT 0,0;"  Controls 7=UP  6DOWN        "
  97 INPUT "Select your horse 1-7   ";h$
  98 IF h$<"1" OR h$>"7" THEN GO TO 97
  99 LET n=VAL (h$): LET acc=(20-ABS (4-n))/34
 100 LET k$=INKEY$: LET m=INT (RND*7+1)
 102 IF m=n THEN GO TO 100
 105 IF k$="7" OR k$="6" THEN LET m=n: GO TO 150
 110 LET k$="7": IF RND>.5 THEN LET k$="6"
 120 IF x(m)>x(n)-2 THEN LET k$="7": IF y(n)>y(m) THEN LET k$="6"
 150 IF k$="7" THEN LET y(m)=y(m)-1: IF y(m)<1 THEN LET y(m)=1
 160 IF k$="6" THEN LET y(m)=y(m)+1: IF y(m)>20 THEN LET y(m)=20
 165 LET x(m)=x(m)-1/slo
 180 FOR i=1 TO 7
 185 LET j=INT (RND*4+1)
 190 IF i<>n THEN GO TO 240
 200 IF c=0 THEN LET j=j*acc: IF x(n)>9 THEN LET c=1
 205 IF c=1 THEN BORDER 2: LET c=2
 210 IF c=2 THEN LET j=j*2
 240 LET x(i)=x(i)+j/slo: IF x(i)>28 THEN LET x(i)=28
 250 NEXT i
 400 LET crash=0
 410 FOR i=1 TO 7
 420 FOR j=1 TO 7
 430 IF i=j THEN GO TO 550
 440 IF y(i)<>y(j) THEN GO TO 550
 450 IF ABS (x(i)-x(j))>3 THEN GO TO 550
 460 LET d=1: IF b(i)>b(j) THEN LET d=-1
 470 LET y(i)=y(i)-d
 475 LET y(j)=y(j)+d
 480 IF y(i)<1 THEN LET y(i)=1
 490 IF y(i)>20 THEN LET y(i)=20
 500 IF y(j)<1 THEN LET y(j)=1
 510 IF y(j)>20 THEN LET y(j)=20
 530 LET x(j)=x(j)-INT (RND*5+1 )/slo: IF x(j)<2 THEN LET x(j)=2
 540 LET crash=1
 550 NEXT j
 560 NEXT i
 570 IF crash=1 THEN GO TO 400
 600 FOR i=1 TO 7
 610 PRINT AT INT b(i),INT a(i);"   "
 615 INK i-1
 618 LET h$="{93}{94}{95}": IF x(i)-INT (x(i))>.5 THEN LET h$="{90}{91}{92}"
 620 PRINT AT INT y(i),INT x(i);h$
 625 IF x(i)>=28 THEN GO TO 5000
 630 LET a(i)=x(i)
 635 LET b(i)=y(i)
 640 NEXT i
 700 GO TO 100
1000 REM **** Instructions ****
1010 CLS : PRINT AT 0,10;"NEWMARET": PRINT 
1020 PRINT "In this horse-race game, you"
1030 PRINT "ride any horse from 1 to 7."
1040 PRINT "You must steer a path avoiding "
1050 PRINT "the other horses since any horse"
1060 PRINT "in a collision with another will"
1070 PRINT "be blocked and forced sideways"
1080 PRINT "and backwards."
1090 PRINT : PRINT "'Easy', you might say..."
1110 PRINT "BUT your horse is a very s-l-o-w"
1120 PRINT "starter and will only run at"
1130 PRINT "speed after the screen border "
1135 PRINT "turns ";: PRINT PAPER 2;"RED";: PRINT ". This occurs when you"
1140 PRINT "have ridden a third of the way"
1150 PRINT "down the track, so you will "
1160 PRINT "always have other horses in "
1170 PRINT "front of you."
1171 PRINT AT 20,0;"   Press any key to continue    "
1172 LET z$="": LET z$=INKEY$: IF z$="" THEN GO TO 1172
1175 CLS : PRINT AT 0,0;"To make it harder still, all"
1177 PRINT "horses within 20 feet of you "
1180 PRINT "will attempt to block your path"
1182 PRINT "or crash into you!": PRINT 
1185 PRINT "Push number 6 to move down the"
1187 PRINT "screen and number 7 to move up"
1190 PRINT "the screen. BEWARE: any course"
1192 PRINT "alteration will also reduce your"
1195 PRINT "speed!"
1197 PRINT 
1200 PRINT "         Good Luck!             ": PRINT : PRINT "     Press any key to start     "
1210 LET z$="": LET z$=INKEY$: IF z$="" THEN GO TO 1210
1220 RETURN 
3000 REM ** set up horse graphic **
3005 FOR i=0 TO 7: READ gr
3010 POKE USR "a"+i,gr
3020 NEXT i
3105 FOR i=0 TO 7: READ gr
3110 POKE USR "b"+i,gr
3120 NEXT i
3205 FOR i=0 TO 7: READ gr
3210 POKE USR "c"+i,gr
3220 NEXT i
3305 FOR i=0 TO 7: READ gr
3310 POKE USR "d"+i,gr
3320 NEXT i
3405 FOR i=0 TO 7: READ gr
3410 POKE USR "e"+i,gr
3420 NEXT i
3505 FOR i=0 TO 7: READ gr
3510 POKE USR "f"+i,gr
3520 NEXT i
3900 DATA 0,0,0,12,3,3,5,10
3910 DATA 8,12,26,113,255,254,1,1
3920 DATA 0,128,224,144,192,128,64,32
3930 DATA 0,0,1,195,63,63,80,80
3940 DATA 128,196,174,153,252,224,20,34
3950 DATA 0,0,0,0,0,0,0,0
4000 REM ** set up screen positions **
4010 FOR q=1 TO 7
4020 LET a(q)=2: LET x(q)=2
4030 LET b(q)=q*3-1: LET y(q)=b(q)
4040 NEXT q
4050 RETURN 
5000 REM *** winner ***
5005 PAPER i-1: INK (7*INT ((7-i)*2/7))
5010 IF i=n THEN GO TO 5030
5015 PRINT AT 0,0;" The Winner....Horse Number ";i;"   "
5020 GO TO 5040
5030 PRINT AT 0,0;"     You won!  Well done       "
5040 FOR q=1 TO 50
5045 PRINT AT y(i),x(i); FLASH 1;"{93}{94}{95}"
5050 NEXT q
5100 PRINT AT 21,0;"   Press any key to play again  "
5130 LET z$="": LET z$=INKEY$: IF z$="" THEN GO TO 5130
5150 RUN 
6000 REM ************************
6010 REM 
6020 REM To alter the fortunes of the game try the following:-
6030 REM vary slo in line 30
6040 REM vary the speed of your horse relative to the others by changing j in lines 200-210
6050 REM alter the point at which the speed up takes place..e.g.x>8 in line 210

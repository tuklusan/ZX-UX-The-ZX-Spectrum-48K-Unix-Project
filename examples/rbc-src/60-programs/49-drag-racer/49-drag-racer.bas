   1 REM Drag Racer @ R.Erskine 1983
   5 GO SUB 4000
  10 GO SUB 9000
  15 GO SUB 9150
  20 LET g=1
 100 LET I=CODE INKEY$
 110 IF I=109 THEN LET a=a+1
 120 IF I>48 AND I<53 THEN LET g=I-48
 125 IF t<3 THEN LET rpm=FN a(x): GO TO 140
 130 LET rpm=FN b(x)
 140 IF RND>(rpm-6000)/1000 THEN GO TO 160
 150 GO TO 3000
 160 LET os=ns
 170 LET op=np
 180 LET tq=FN c(x)
 190 LET tq1=17
 200 LET ns=FN d(x)
 210 LET np=FN e(x)
 240 LET t=t+1
 260 LET a=FN f(x)
 270 LET x=48*SIN a
 280 LET y=48*COS a
 285 IF t>1 THEN PLOT 152,56: DRAW OVER 1;xx,yy
 290 PLOT 152,56: DRAW OVER 1;x,y
 300 LET xx=x: LET yy=y
 310 LET a=FN g(x)
 320 LET n=48*SIN a
 330 LET o=48*COS a
 340 IF t>1 THEN PLOT 49,56: DRAW OVER 1;nn,oo
 350 PLOT 49,56: DRAW OVER 1;n,o
 360 LET nn=n: LET oo=o
 365 PRINT PAPER 5; INK 0;AT lin1,col1;"_"
 400 LET col1=col1+INT ((np-op)/cl)
 410 IF col1>31 AND lin1<8 THEN LET col1=0+(col1-31): LET lin1=lin1+1
 460 IF lin1<8 THEN PRINT PAPER 5; INK 0;AT lin1,col1;"{90}"
 500 IF np<1320 THEN GO TO 100
2000 LET t=FN h(x)
2005 IF bt=0 THEN LET bt=t
2010 IF t<bt THEN LET bt=t
2030 PRINT AT 0,0;"Time ";t;" seconds"
2040 PRINT "Best time: ";bt;" seconds"
2050 PRINT "Maximum speed: ";ns;" mph"
2055 FOR x=1 TO 1000: NEXT x
2060 PRINT "Press any key to restart"
2070 IF INKEY$="" THEN GO TO 2070
2090 LET gr=gr+.1: IF gr>4.1 THEN LET gr=4.11
2095 GO SUB 9000
2096 GO SUB 9310
2100 GO TO 20
3000 PRINT FLASH 1; PAPER 2; INK 6;AT lin1,col1;"{90}";AT 0,3;"Engine blown": GO TO 2055
4000 PAPER 0: INK 5: BORDER 0: CLS 
4010 PRINT AT 0,10;"Drag Racer"
4020 PRINT 
4030 PRINT "In this drag racing simulation ","you must try to cover the ","quarter mile in the shortest ","possible time. The only controlsyou need are the gears which ","must be changed at the optimum ","moment.": PRINT 
4040 PRINT "At the start you are in first ","gear and you must watch the rpm counter and decide when to ","change into second.  At over ","6000 rpm there is a high ","probability of the engine ","blowing.": PRINT 
4050 PRINT "With each succeeding attempt ","the rear end ratio is increased slightly which makes the game ","progressively more difficult.": PRINT 
4060 PRINT "Try not to change gear too late or too early.  The gear keys are1,2,3 and 4.  Good Luck."
4070 PRINT : FOR x=1 TO 1000: NEXT x
4080 PRINT "Press any key to start"
4085 IF INKEY$="" THEN GO TO 4085
4090 RETURN 
8000 FOR x=0 TO 7
8010 PRINT PAPER 5;AT x,0;"                                "
8020 NEXT x
8030 FOR x=112 TO 168 STEP 8
8040 PLOT 0,x: DRAW INK 0;255,0
8050 NEXT x
8060 RETURN 
9000 DIM g(4)
9005 BORDER 5: PAPER 0: INK 7: CLS 
9010 LET g(1)=4
9020 LET g(2)=2.5
9030 LET g(3)=1.5
9040 LET g(4)=1
9050 LET t=0: LET np=0: LET ns=np
9070 LET mph=0
9080 LET rpm=0
9090 CIRCLE 152,56,48
9100 CIRCLE 49,56,48
9110 PRINT AT 14,5;"RPM";AT 14,17;"MPH";AT 10,26;"Drag";AT 19,26;"Racer"
9120 PRINT AT 14,13;"135";AT 14,23;"45";AT 9,19;"0";AT 20,18;"90"
9130 PRINT AT 9,6;"0";AT 14,10;"17";AT 14,0;"52";AT 20,5;"35"
9140 GO SUB 8000
9145 RETURN 
9150 DEF FN a(x)=4200*(g(g)/g(1))
9160 DEF FN b(x)=ns*gr*g(g)*con/circ
9170 DEF FN c(x)=(c1*rpm^3)+(c2*rpm^2)+(c3*rpm)
9180 DEF FN d(x)=os+(tq/tq1)
9190 DEF FN e(x)=op+ns*(5280/60^2)
9200 DEF FN f(x)=(ns*2)/180+PI
9210 DEF FN g(x)=(rpm/19.5)/180*PI
9220 DEF FN h(x)=t+(1320-op)/(np-op)-1
9250 LET con=63360
9260 LET circ=4253.893421
9270 LET c1=-1.8953E-9
9280 LET c2=1.02157E-5
9290 LET c3=.015752
9300 LET bt=0: LET gr=3: LET cl=5.176
9310 LET lin1=0: LET col1=0
9320 RESTORE : FOR x=USR "a" TO USR "a"+7
9330 READ n: POKE x,n
9340 NEXT x
9350 DATA 0,0,0,0,224,255,227,255
9999 RETURN 

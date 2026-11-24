  10 REM *CRITICAL PATH ANALYSIS         @1983 MICHAEL BEWS              for 48k Spectrum
  20 DIM a$(50,5): DIM b$(50,5): DIM g$(30): DIM n$(30): DIM p$(30,20): DIM p(30): DIM t(30)
  21 LET k=0
  25 GO TO 500
  29 REM **READ NETWORK DATA
  30 READ e
  40 FOR x=1 TO e
  50 READ a,b,c
  60 FOR y=1 TO 5
  70 IF b$(a)(y)=" " THEN LET b$(a)(y)=CHR$ (33+b): LET n$(a)=CHR$ (CODE n$(a)+1): GO TO 90
  80 NEXT y
  90 FOR y=1 TO 5
 100 IF a$(a)(y)=" " THEN LET a$(a)(y)=CHR$ (33+c): GO TO 120
 110 NEXT y
 120 NEXT x
 125 READ a: IF a<>-1 THEN PRINT "Check sum error": STOP 
 127 PRINT "  DATA Check OK"
 130 INPUT "ENTER start node ";s: LET n=s: IF s<1 THEN GO TO 130
 135 PRINT : PRINT AT 20,0;"Enter ""-1"" to see ALL possible            paths."
 140 INPUT "finish node ";f: IF f>0 THEN LET n$(f)=" "
 142 IF f>e OR f=0 OR f=s OR f<-1 THEN GO TO 140
 143 PRINT AT 20,0;"                                                           ";AT 20,5;"WAIT PLEASE"
 145 LET p=1: LET h$=n$
 150 LET p$(p)(1)=CHR$ (33+n)
 160 IF n$(n)=" " THEN GO TO 300
 165 LET g$(n)="1"
 170 LET h=CODE h$(n)-32
 175 IF g$(CODE b$(n)(h)-33)<>" " THEN GO TO 430
 180 FOR x=1 TO LEN p$(p): IF p$(p)(x)=" " THEN LET p$(p)(x)=b$(n)(h): GO TO 185
 182 NEXT x
 185 LET t(n)=p(p): LET p(p)=p(p)+CODE (a$(n)(h))-33
 190 LET n=CODE b$(n)(h)-33
 200 GO TO 160
 300 LET v=1: LET g=0
 301 FOR x=LEN p$(p) TO 1 STEP -1
 305 IF p$(p)(x)=" " THEN GO TO 320
 306 LET g$(CODE p$(p)(x)-33)=" "
 307 IF g=0 AND p$(p)(x)<>CHR$ (f+33) AND f>0 THEN LET v=0
 310 LET g=1: IF CODE h$(CODE (p$(p)(x))-33)>33 THEN GO TO 400
 320 NEXT x
 325 IF v=0 THEN LET p$(p)="                                ": LET p=p-1
 330 PRINT AT 8,0;o$;AT 8,0: LET j=0: LET u=0: LET r=0: LET tp=0: FOR x=1 TO p
 335 FOR y=1 TO LEN p$(x): IF p$(x)(y)=" " THEN GO TO 350
 340 PRINT CODE p$(x)(y)-33;",";: NEXT y
 350 PRINT " * ";p(x): IF p(x)>j THEN LET j=p(x): LET k=x
 355 LET tp=tp+1: IF y-1>r THEN LET r=y-1: LET u=x
 360 NEXT x
 362 LET f$=STR$ f: IF f<0 THEN LET f$="end"
 365 PRINT "                                ": PRINT "No. of paths ";s;" to ";f$;" = ";tp
 366 PRINT : PRINT "Path No. ";u;" has most nodes.(";r;")"
 368 PRINT "Path No. ";k;" is longest.(";j;")"
 370 STOP 
 400 LET n=CODE p$(p)(x)-33: LET h$(n)=CHR$ (CODE h$(n)-1): LET q$=p$(p): LET p=p+v: LET p$(p)( TO x)=p$(p-v): LET p$(p)(x+1 TO )="                                ": LET p(p)=t(n)
 405 FOR y=x+1 TO LEN q$: LET z=CODE q$(y)-33: IF z<1 THEN GO TO 160
 410 LET h$(z)=n$(z)
 415 NEXT y
 420 GO TO 160
 430 PRINT "Loop-back error.": PRINT : FOR l=1 TO LEN p$(p)-1: IF CODE p$(p)(l)-33<1 THEN GO TO 450
 440 PRINT CODE p$(p)(l)-33;"-";: NEXT l
 450 PRINT CODE b$(n)(h)-33: PRINT : PRINT "Please correct data error.": PRINT : GO TO 330
 499 STOP 
 500 BORDER 5: PAPER 5: INK 1
 505 LET O$="              ": FOR X=1 TO 5: LET O$=O$+O$: NEXT X
 510 CLS : PRINT ; INVERSE 1;"CRITICAL PATH NETWORK ANALYSIS "; INVERSE 0
 520 INK 0: PRINT : PRINT "CRITICAL PATH NETWORKS CAN BE   APPLIED WHEREVER SEVERAL INTER- DEPENDENT ACTIVITIES NEED TO BE    CARRIED OUT IN A SPECIFIED   SEQUENCE TO ACHIEVE A FINAL GOAL"
 530 PRINT : PRINT "THE GOAL MIGHT BE THE COMPLETION OF A LARGE PROJECT OR, MORE    SIMPLY, ARRIVAL AT A DISTANT    METRO STATION BY THE SHORTEST           POSSIBLE ROUTE"
 540 PRINT : PRINT "THIS PROGRAM IS SUITABLE FOR USEIN EITHER CASE.";
 550 PRINT " A DEMONSTRATION NETWORK IS SHOWN AND THE PROGRAM WILL TRACE OUT ALL POSSIBLE      PATHS THROUGH THE NETWORK,     INDICATING THE LONGEST AND           SHORTEST ROUTES."
 560 PRINT ; INVERSE 1;AT 21,9;"PRESS <ENTER>"; INVERSE 0
 570 INPUT x$
 600 PAPER 7: INK 0: CLS : PLOT 11,131: DRAW 23,32
 610 DRAW 160,0: DRAW 42,-16
 620 PLOT 11,131: DRAW 48,16: DRAW 176,0
 630 PLOT 11,131: DRAW 72,0: DRAW 24,16: DRAW 112,0
 640 PLOT 11,131: DRAW 32,-10: DRAW 80,0: DRAW 32,10
 650 PLOT 60,147: DRAW 24,16
 660 PLOT 132,164: DRAW 16,-16: DRAW 8,-16: DRAW 8,-16
 670 DRAW 72,32: REM DRAW -40,0
 680 PLOT 200,132: DRAW -48,0
 700 PRINT INVERSE 1;AT 1,4;"4";AT 1,10;"5";AT 1,16;"6";AT 1,23;"11";
 710 PRINT INVERSE 1;AT 5,1;"1";AT 3,7;"2";AT 3,13;"3";AT 3,18;"7";AT 3,28;"12";
 720 PRINT INVERSE 1;AT 5,19;"8";AT 5,24;"10";AT 7,20;"9";
 730 PRINT AT 2,2;"4";AT 1,7;"1";AT 1,13;"1";AT 1,19;"7";AT 1,26;"3";
 740 PRINT AT 3,4;"2";AT 3,10;"3";AT 3,15;"5";AT 3,22;"11";AT 5,6;"4";AT 5,21;"3";AT 4,27;"9";AT 6,23;"2"
 745 PRINT AT 2,8;"3";AT 2,16;"2"
 750 PRINT AT 4,18;"0";AT 6,19;"3";AT 6,11;"11"
 800 PRINT AT 8,0;"Nodes "; INVERSE 1;"1"; INVERSE 0;" represent the commence- ment of activities, (represented by the joining lines). The linelengths might represent a number of days or weeks required to   complete an activity."
 810 PRINT : PRINT " Activities can progress in one direction only and the program  will reject a network having a  loop-back condition.";
 820 PRINT " Each activity progresses in the direction  entered in the program{E4}statements."
 830 PRINT AT 21,13; INVERSE 1;"PRESS <ENTER>"; INVERSE 0
 840 INPUT x$
 850 PRINT AT 8,0;O$;AT 21,18;"        ";
 860 PRINT AT 9,0;"The zero (0) length between node "; INVERSE 1;"7"; INVERSE 0;" and "; INVERSE 1;"8"; INVERSE 0;" indicates the existence of a restraint which prevents  activities at node "; INVERSE 1;"8"; INVERSE 0;" from commencing until activities "; INVERSE 1;"3"; INVERSE 0;"to"; INVERSE 1;"7"; INVERSE 0;
 870 PRINT " and  "; INVERSE 1;"6"; INVERSE 0;"to"; INVERSE 1;"7"; INVERSE 0;" are complete."
 880 PRINT : PRINT : PRINT ; INVERSE 1;"PRESS <ENTER>"; INVERSE 0;
 890 INPUT x$
 900 GO TO 30
1000 REM **FLOW CHART DATA****
1005 REM **number of connecting                lines
1010 DATA 18
1015 REM **start node, finish              node, line length
1050 DATA 1,4,4
1060 DATA 1,2,2
1070 DATA 1,3,4
1080 DATA 1,8,11
1090 DATA 2,3,1
1100 DATA 2,5,3
1110 DATA 3,7,5
1120 DATA 4,5,1
1130 DATA 5,6,1
1140 DATA 6,7,2
1150 DATA 6,11,7
1160 DATA 7,8,0
1170 DATA 7,12,11
1180 DATA 8,9,3
1190 DATA 8,10,3
1200 DATA 9,10,2
1210 DATA 10,12,9
1220 DATA 11,12,3
1230 DATA -1

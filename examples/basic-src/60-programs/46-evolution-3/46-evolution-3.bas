   1 BORDER 0: PAPER 0: INK 7: CLS 
   3 POKE 23658,10
   5 REM @ P.Stanley
  10 DATA 0,8,28,8,8,62,0,0,0,32,36,62,36,32,0,0,0,62,8,8,28,8,0,0,0,2,18,62,18,2,0,0
  15 DATA 128,128,128,128,128,128,128,255,128,128,128,156,156,128,128,255
  17 DATA 127,127,127,127,127,127,127,0
  20 FOR y=USR "a" TO USR "g"+7: READ x: POKE y,x: NEXT y
  30 DATA "LONDON",8,13,"MOSCOW",5,24,"BONN",7,17,"WASHINGTON",8,3,"BRASILIA",17,4,"TOKYO",9,28,"RIYADH",12,17,"CANBERRA",18,29,"PEKING",9,25,"PRETORIA",17,14
  60 PRINT "This is the 3rd and final       section in the series of        evolution programs."' INK 5'"This one involves a nuclear war,where you can play the part of  P.M. of any of 10 superpowers   which may exist in 2002 (the    year in which this war takes    place)."
  70 PRINT INK 6'"The object is to program cruise missiles to home in on the      enemies' capitals."
  80 PRINT INVERSE 1'"Press any key to read more.": PAUSE 0: CLS 
  90 PRINT "In 2002 the World is not very   different from the previous 20  years, apart from new superpowerforces exist. South America has been over-run by Brazil and its capital is Brasilia."' INK 5'"Japan has become a powerful     nation, and the Arabs have a    fighting nation based around    Riyadh. Also Australia & South  Africa are superpowers."
  95 INPUT "Enter a skill level (30-100).   30 is the hardest: ";sk
  97 IF sk<30 OR sk>100 THEN GO TO 95
 100 PRINT '"In which capital do you want to be P.M. ? (You only need to typethe first 2 characters.)"
 101 RANDOMIZE 
 105 LET f$="          "
 110 PRINT : FOR f=1 TO 10: READ a$,y,x: PRINT a$,: NEXT f
 120 INPUT a$: IF LEN a$<2 THEN GO TO 120
 130 RESTORE 30: FOR f=1 TO 10: READ b$,y,x: IF b$(1 TO 2)<>a$(1 TO 2) THEN NEXT f
 135 IF b$(1 TO 2)<>a$(1 TO 2) THEN GO TO 120
 136 LET v=y: LET u=x: LET e$="{90}": LET f$(f)="X"
 137 RESTORE 30
 138 LET i=INT (RND*10)+1: IF f$(i)<>"X" THEN FOR f=1 TO i: READ b$,y2,x2: NEXT f: GO TO 140
 139 GO TO 138
 140 LET sc=1: CLS : PRINT "The way you program your missileis by compass directions (ie n,s,w and e). The world map is     divided into squares, and each  step of the program moves the   missile 1 square."
 145 LET f$(i)="X"
 150 PRINT INK 5'"For example ""nnees"" moves the   missile 2 squares up, 2 right   and 1 down."' INK 6'"If the missile goes off the     screen at any side it will      appear on the opposite side."
 151 PRINT INK 4'"The red square is your target"
 155 PRINT '"You must enter your program as  quickly as possible . When it isready press F to launch a nuke."
 160 PAPER 0: INK 5: PRINT AT 21,0;"Press a key to begin": PAUSE 0: CLS : GO SUB 9000
 170 PRINT AT y2,x2; INK 2; FLASH 1;"{8F}"; INK 6; INK 0; PAPER 3;AT y,x;"{95}": LET y1=y2: LET x1=x2: LET d$="{90}"
 175 DIM c$(50): LET c=1
 180 LET c$="": PRINT INK 7;AT 21,0;"Enter program after the tone."
 185 FOR f=1 TO 150: NEXT f: PRINT AT 21,0;"                               ": BEEP .1,10
 190 LET C1=C
 195 FOR f=1 TO sk: IF INKEY$="" THEN NEXT f
 200 IF INKEY$="N" THEN LET c$(c)="N": LET c=c+1
 210 IF INKEY$="S" THEN LET c$(c)="S": LET c=c+1
 220 IF INKEY$="W" THEN LET c$(c)="W": LET c=c+1
 230 IF INKEY$="E" THEN LET c$(c)="E": LET c=c+1
 235 IF INKEY$="F" OR c=51 THEN PRINT AT 21,0;"                                ": BEEP .1,20: GO TO 600
 240 IF c1=c THEN GO SUB 500: GO TO 190
 250 PRINT INK RND*4+3;AT 21,(c-1 AND c<33)+(c-33 AND c>=33);c$(c-1)
 255 IF c=32 THEN PRINT AT 21,0;"                                "
 260 BEEP .1,0
 270 GO TO 190
 500 PRINT AT y1,x1; OVER 1;d$; OVER 0;AT y2,x2; INK 2;"{8F}"
 510 IF y1<y THEN LET y1=y1+1: LET d$="{92}"
 520 IF y1>y THEN LET y1=y1-1: LET d$="{90}"
 530 IF x1<x THEN LET x1=x1+1: LET d$="{91}"
 540 IF x1>x THEN LET x1=x1-1: LET d$="{93}"
 550 PRINT INK 3; FLASH 1; BRIGHT 1;AT y1,x1; OVER 1;d$
 555 IF y1=y THEN IF x1=x THEN GO TO 900
 557 BEEP .06,25: BEEP .06,27
 560 RETURN 
 600 LET c=1
 602 PRINT AT v,u; OVER 1;e$
 605 FOR f=1 TO 3: PRINT AT y,x; INK 6; FLASH 1; PAPER 0;"{95}"; FLASH 0;AT v,u; INK 5; OVER 1;e$
 610 LET v=v+(c$(c)="S")-(c$(c)="N"): LET u=u+(c$(c)="E")-(c$(c)="W")
 615 LET e$="": LET e$=e$+("{92}" AND c$(c)="S")+("{90}" AND c$(c)="N")+("{91}" AND c$(c)="E")+("{93}" AND c$(c)="W")
 620 IF v=-1 THEN LET v=20
 630 IF v=21 THEN LET v=0
 640 IF u=-1 THEN LET u=31
 650 IF u=32 THEN LET u=0
 660 IF v=y2 THEN IF u=x2 THEN GO TO 2000
 670 PRINT OVER 1; INK 7; BRIGHT 1;AT v,u;e$
 671 LET c=c+1: IF c<51 THEN IF c$(c)<>"N" AND c$(c)<>"W" AND c$(c)<>"E" AND c$(c)<>"S" THEN LET c=1: GO TO 800
 672 IF c=51 THEN GO TO 800
 675 FOR i=20 TO 30: BEEP .001,i: NEXT i
 680 NEXT f
 690 GO SUB 500
 700 GO TO 605
 800 PRINT OVER 1;AT v,u;e$
 810 LET c=1: LET v=y: LET u=x
 830 GO TO 180
 900 PRINT INK 7;AT 21,0;"You have been destroyed": FOR f=1 TO 20: PRINT AT y,x; INK RND*6+1;"{8F}": BEEP .05,f*3: NEXT f: INPUT "Want another go (Y/N)";f$
 905 PRINT AT 21,0;"                                "
 906 GO SUB 9000
 907 LET sc=1
 910 IF f$(1)="N" THEN STOP 
 915 INPUT AT 0,0;"Enter a skill level (30-100).   30 is the hardest: ";sk
 917 IF sk<30 OR sk>100 THEN GO TO 915
 920 INPUT AT 0,0;"Want to see the names?";f$: IF f$(1)="N" THEN GO TO 950
 930 RESTORE 30: FOR f=1 TO 10: BEEP .05,-20: READ f$,y,x: PRINT INK RND*3+4;AT 21,0;f$;"         ": FOR y=1 TO 70: NEXT y: NEXT f
 950 LET f$="          "
 960 INPUT AT 0,0;"Which capital?";a$: IF LEN a$<2 THEN GO TO 960
 970 RESTORE 30: FOR f=1 TO 10: READ b$,y,x: IF b$(1 TO 2)<>a$(1 TO 2) THEN NEXT f: GO TO 960
 975 LET f$(f)="X"
 980 LET c=1: LET c$="": LET v=y: LET u=x
 990 LET i=INT (RND*10)+1: IF f$(i)<>"X" THEN RESTORE 30: FOR f=1 TO i: READ b$,y2,x2: NEXT f: LET f$(i)="X": GO TO 170
1000 GO TO 990
2000 IF sc=9 THEN LET i=5: GO TO 2015
2010 LET i=INT (RND*10)+1: IF f$(i)="X" THEN GO TO 2010
2015 LET sc=sc+1: LET f$(i)="X": PRINT INK 7;AT 21,0;b$;" has been destroyed": FOR f=1 TO 4: FOR s=7 TO 0 STEP -1: PRINT AT y2,x2; INK s;"{8F}": BEEP .03,s*7: NEXT s: NEXT f
2016 IF sc=10 THEN GO TO 4000
2017 PRINT AT y1,x1; OVER 1;d$
2020 PRINT INVERSE 1;AT y2,x2;"{94}": LET c=1: LET c$="": LET v=y: LET u=x: RESTORE 30: FOR f=1 TO i: READ b$,y2,x2: NEXT f: PRINT FLASH 1;AT y2,x2; INK 2;"{8F}": LET y1=y2: LET x1=x2
2025 PRINT AT 21,31;" "
2030 GO TO 180
4000 PRINT INVERSE 1;AT y2,x2;"{94}": PRINT AT 21,0;"                                "
4005 INK 2: FLASH 1: BRIGHT 1: GO SUB 9000: INK 5: FLASH 0: BRIGHT 0: PRINT AT 9,0;"CONGRATULATIONS - YOU NOW RULE  THE WHOLE WORLD (WELL WHAT'S    LEFT AFTER YOUR NUKES' WORK!)   "
4010 FOR f=1 TO 3: FOR g=12 TO 20 STEP 2: BEEP .07,g: NEXT g: FOR g=18 TO 10 STEP -2: BEEP .07,g: NEXT g: NEXT f
4020 PRINT "                                PRESS Y TO TRY AGAIN, ELSE N...."
4025 IF INKEY$="" THEN GO TO 4025
4030 IF INKEY$="Y" THEN GO SUB 9000: PRINT AT 21,0;"                                ": GO TO 915
4040 STOP 
9000 PRINT AT 0,0;"{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{94}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{94}{96}{96}{94}{94}{94}{94}{96}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{94}{96}{96}{94}{94}{94}{94}{94}{94}{94}{96}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{94}{94}{94}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{94}{94}{94}"
9010 PRINT "{96}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{94}{94}{94}{96}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94} {8F}{94}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{94}{94}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{94}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{94}{96}{94}{94}{94}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{96}{94}{96}{94}{94}{94}{96}{94}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{94}{96}{96}{96}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}   {94}{96}{96}{94}{94}{96}{96}{94}{94}{96}{94}{94}{94}{96}{94}{94}{94}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{94}{96}{94}{94}{94}{96}{94}{94}{94}{94}{96}{94}{94}{96}{94}{94}"
9020 PRINT "{94}{96}{96}{96}{96}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{94}{96}{94}{94}{94}{94}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{94}{94}{94}{94}{96}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{94}{96}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{96}{96}{94}{94}{94}{94}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{96}{96}{96}{96}{96}{96}{94}{94}{94}{94}{94}{96}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{96}{94}{94}{94}{96}{96}{94}{94}{94}{94}{94}{96}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}"
9030 PLOT 255,8: DRAW 0,167: DRAW -255,0
9040 RESTORE 30: FOR f=1 TO 10: READ a$,b,a: PRINT AT b,a;"{95}": NEXT f: RETURN 

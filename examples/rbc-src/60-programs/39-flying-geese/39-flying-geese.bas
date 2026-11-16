  10 REM ** FLYING GEESE                  @1983 MICHAEL BEWS
  20 GO TO 580
  25 REM **FLYING/SHOOT ROUTINE
  30 FOR x=o TO fr: LET d(x)=ei-x+SGN (o-tw*INT (RND*tw)): PRINT AT h(x),g(x)-o;"  ";: FOR z=o TO fr: LET f=-f: PRINT AT d(x),g(x);" ";a$(th-f);: NEXT z
  40 IF PEEK 23556=65 THEN FOR y=o TO tw: PLOT OVER o;en,tf: DRAW OVER o;fr,th: PRINT OVER o;AT si,th;"{94}";: NEXT y: LET SH=SH+o: PRINT INVERSE o;AT 0,sx;SH;: IF g(x)=ev OR g(x)=tv THEN LET B=B+o: PRINT AT d(x),g(x);"   "; INVERSE o;AT 0,hy;B;: LET g(x)=o-tw: LET h(x)=o: FOR y=d(x) TO ni STEP tw: PRINT AT y-tw,fo;" ";AT y-o,fo;" ";AT y,fo;"{95}";AT y+o,fo;"{96}";: NEXT y: PRINT AT ni-o,fo;" ";AT ni,fo;" ";AT ni+o,fo;" ";
  50 LET h(x)=d(x): LET g(x)=g(x)+tw: IF g(x)>tn THEN PRINT AT h(x),g(x)-o;"  ";: LET g(x)=o
  60 NEXT X: IF SH>99 THEN GO TO 300
  70 GO TO 30
 100 FOR x=1 TO 4: LET h(x)=1: LET g(x)=x*5-4: NEXT x
 110 CLS : PRINT INVERSE 0;AT 0,0;"SHOTS:  ";AT 0,10; PAPER 7; INK 2;"<A> TO FIRE "; INK 7; PAPER 1;AT 0,24;"SCORE  "; INK 4;AT 13,21;"{94}{94}{94}";AT 14,20;"{94}{94}{94}{94}{94}";AT 15,19;"{94}{94}{94}{94}{94}{94}{94}";AT 16,19;"{94}{94}{94}{94}{94}{94}{94}";AT 17,19;"{94}{94}{8F}"; PAPER 2; INK 0;"{93}"; PAPER 1; INK 4;"{8F}{94}{94}"; PAPER 2; INK 0;AT 18,22;"{93}";AT 19,22;"{93}";
 120 PRINT AT 20,0; PAPER 4;"            "; PAPER 1;"        "; PAPER 4;"                        "; INK 5; PAPER 1;"{93}{93}{93}{93}{93}{93}{93}{93}"; PAPER 4;"            ";
 130 PRINT AT 18,1;"{9C}";AT 19,1;"{9D}";
 140 GO TO 30
 299 REM ***END OF GAME ROUTINE***
 300 IF B>TOT THEN LET TOT=B
 310 PRINT FLASH 1;AT 9,10;" GAME OVER "; FLASH 0; INVERSE 1;AT 11,4;" SCORE:";B;" IN 100 SHOTS ";
 320 PRINT AT 13,4; INVERSE 1;"HIGHEST SCORE:";TOT;
 330 INPUT FLASH 1;"PRESS <ENTER> FOR NEXT GAME";X$: LET SH=0: LET B=0: GO TO 100
 570 REM **INITIALISATION**
 580 PAPER 1: INK 7: BORDER 6: CLS 
 590 DIM a$(4,2): DIM d(4): DIM g(4): DIM h(4)
 600 LET sx=6: LET hy=30: LET TOT=0: LET SH=0: LET fi=15: LET tv=12: LET ev=11: LET ni=19: LET ty=20: LET en=18: LET tf=34: LET si=16: LET fo=14: LET ei=8: LET f=-1: LET o=1: LET tw=2: LET th=3: LET fr=4: LET tn=29
 610 FOR x=0 TO 7: READ a,b,c: POKE USR "{90}"+x,a: POKE USR "{91}"+x,b: POKE USR "{92}"+x,c: NEXT x
 620 LET a$(4)="{90}{91}": LET a$(2)="{92}{91}"
 630 FOR x=0 TO 7: READ a,b: POKE USR "{9C}"+x,a: POKE USR "{9D}"+x,b: NEXT x
 640 FOR x=0 TO 7: READ a: POKE USR "{93}"+x,a: NEXT x
 650 FOR x=0 TO 7: READ a: POKE USR "{94}"+x,a: NEXT x
 660 FOR x=0 TO 7: READ a,b: POKE USR "{95}"+x,a: POKE USR "{96}"+x,b: NEXT x
 690 GO TO 100
 999 REM **U.D. GRAPHICS{E4}
1000 DATA 2,0,0,6,0,0,7,48,0,7,104,0,127,254,127,31,192,31,8,0,15,0,0,3
1010 DATA 1,224,98,224,244,144,232,144,88,144,232,144,248,144,224,216
1020 DATA 85,170,85,170,85,170,85,170
1030 DATA 66,16,132,33,4,81,4,160
1040 DATA 0,48,16,56,18,28,54,20,118,24,62,16,60,16,60,0

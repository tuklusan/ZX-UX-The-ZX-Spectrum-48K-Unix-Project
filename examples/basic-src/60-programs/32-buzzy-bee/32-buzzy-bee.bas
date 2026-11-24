   1 BORDER 0: PAPER 0: INK 7: CLS 
   6 CLS 
   7 GO SUB 9700
   8 GO SUB 9000
  10 LET hs=0
  20 GO SUB 8000
  50 POKE 23674,255: POKE 23673,255: POKE 23672,255
 100 PRINT PAPER 5;AT y1,x1;"   ";AT y1+1,x1;"   "; INK 0;AT y,x;b$;AT y+1,x;c$: LET y1=y: LET x1=x
 120 IF y(t)=4 THEN GO SUB 1000
 480 LET g=g+(2 AND IN 65278=251 AND g<31)-(2 AND IN 65278=253 AND g>0)
 500 PRINT AT f1,g1; INK 4; OVER 1;"{9F}";AT f,g;"{9F}": LET f1=f: LET g1=g
 510 IF IN 32766=251 THEN GO SUB 2000
 700 LET t=INT (RND*5)+1: LET y(t)=y(t)-1: IF y(t)<h2 AND y(t)>h1 THEN LET h2=y(t): LET fl2=t
 710 IF y(t)<h1 THEN LET h1=y(t): LET fl1=t
 750 PRINT INK t+2;AT y(t),t*6-5;"{9C}   {9D}";AT y(t)+1,t*6-5;"     ";AT y(t)+2,t*6-5;"{A0} {8F} {A1}"; INK 4;AT y(t)+3,t*6-5;"  {8F}  ";AT y(t)+1,t*6-3;"{9E}"
 800 IF x<fl1*6-4 THEN LET b$=a$(3): LET c$=a$(4): LET x=x+1
 820 IF x>fl1*6-4 THEN LET b$=a$(1): LET c$=a$(2): LET x=x-1
 999 GO TO 100
1000 IF x=t*6-4 THEN GO TO 1500
1002 IF g=t*6-3 THEN PRINT INK 4; OVER 1;AT f,g;"{9F}"
1005 FOR f=4 TO 17
1010 PRINT INK t+2;AT f,t*6-5;"     ";AT f+1,t*6-5;"{9C}   {9D}";AT f+2,t*6-5;"     ";AT f+3,t*6-5;"{A0} {8F} {A1}"; INK 4;AT f+4,t*6-4;" {8F} ";AT f+2,t*6-3;"{9E}"
1020 BEEP .04,f
1030 NEXT f
1035 LET f=21
1040 LET y(t)=18
1050 IF t=fl1 THEN LET fl1=fl2: LET h1=h2
1100 IF g=t*6-3 THEN PRINT INK 4; OVER 1;AT f,g;"{9F}"
1300 RETURN 
1500 IF b$=a$(1) THEN LET d=x+1
1502 IF b$=a$(3) THEN LET d=x
1503 LET time=INT ((65536*PEEK 23674+256*PEEK 23673+PEEK 23672)/49)
1505 FOR i=0 TO 3: FOR g=1 TO 10
1510 BEEP .005,2: BEEP .005,5: PRINT AT i,d; PAPER 5; INK 0;a$(1,2 TO ): BEEP .005,7: PRINT AT i,d; PAPER 5; INK 0;a$(3, TO 2)
1520 NEXT g
1530 PRINT AT i,x; PAPER 5;"   ";AT i+1,x; INK 0;b$;AT i+2,x;c$
1540 NEXT i
1550 FOR f=1 TO 200: NEXT f
1560 CLS : PRINT AT 4,0; INK 6;"You survived for ";time;" seconds."
1570 IF time>hs THEN LET hs=time: PRINT INK 5''"Well done! That's the longest   recorded time!": GO TO 1600
1580 PRINT ' INK 5'"The longest recorded time standsat ";hs;" seconds."
1600 PRINT INK 7''"Press any key to play again."
1610 IF INKEY$="" THEN GO TO 1610
1630 CLS : GO TO 20
2000 BEEP .01,20: IF g<>3 AND g<>9 AND g<>15 AND g<>21 AND g<>27 THEN RETURN 
2005 IF g=u*6-3 OR y((g+3)/6)>15 THEN RETURN 
2010 LET u=(g+3)/6
2020 LET y(u)=y(u)+2
2050 PRINT INK u+2;AT y(u)-2,u*6-5;"      ";AT y(u)-1,u*6-5;"     ";AT y(u),u*6-5;"{9C}   {9D}";AT y(u)+1,u*6-5;"     ";AT y(u)+2,u*6-5;"{A0} {8F} {A1}"; INK 4;AT y(u)+3,u*6-4;" {8F} ";AT y(u)+1,u*6-3;"{9E}"
2070 IF u=fl1 THEN IF y(u)>h2 THEN LET h1=h2: LET fl1=fl2: LET fl2=u: LET h2=y(u)
2090 RETURN 
8000 DIM y(5): FOR f=1 TO 5: LET y(f)=18
8010 PRINT INK f+2;AT y(f),f*6-5;"{9C}   {9D}";AT y(f)+1,f*6-5;"     ";AT y(f)+2,f*6-5;"{A0} {8F} {A1}"; INK 4;AT y(f)+3,f*6-3;"{8F}";AT y(f)+1,f*6-3;"{9E}"
8020 NEXT f
8100 FOR f=0 TO 3: PRINT AT f,0; PAPER 5;"                                ": NEXT f
8500 LET y=0: LET x=15
8510 LET f=21: LET g=15
8520 DIM a$(4,3): LET a$(1)="{90}{91}{92}": LET a$(2)="{93}{94}{95}": LET a$(3)="{96}{97}{98}": LET a$(4)="{99}{9A}{9B}": LET b$=a$(1): LET c$=a$(2)
8530 LET y1=y: LET x1=x: LET f1=f: LET g1=g
8540 PRINT AT f,g; OVER 1;"{9F}"
8550 LET h1=20: LET h2=20: LET fl1=2: LET fl2=4
8560 LET t=1
8570 LET u=10
8900 BEEP .5,0
8999 RETURN 
9000 PRINT "{8F}{8F}{8F} {8F} {8F} {8F}{8F}{8F} {8F}{8F}{8F} {8F} {8F}  {8F}{8F}{8F} {8F}{8F}{8F} {8F}{8F}{8F}{8F} {8F} {8F} {8F}   {8F}   {8F} {8F} {8F}  {8F} {8F} {8F}   {8F}  {8F}{8F}{8F} {8F} {8F}  {8F}   {8F}  {8F}{8F}{8F}  {8F}{8F}{8F} {8F}{8F}{8F} {8F}{8F}{8F}{8F} {8F} {8F} {8F} {8F}   {8F}    {8F}   {8F} {8F} {8F}   {8F}  {8F}{8F}{8F} {8F}{8F}{8F} {8F}{8F}{8F} {8F}{8F}{8F}  {8F}   {8F}{8F}{8F} {8F}{8F}{8F} {8F}{8F}{8F}"
9010 RANDOMIZE 100
9020 LET y=8: LET y1=8: FOR f=1 TO 29
9025 BEEP .01,-10
9030 PRINT AT y1,f-1;"   ";AT y1+1,f-1;"   ";AT y,f;"{96}{97}{98}";AT y+1,f;"{99} {9B}"; INK 6;AT y+1,f+1;"{9A}"
9035 LET y1=y
9040 BEEP .01,-10
9050 IF RND>.5 THEN LET y=y+1-(2 AND RND>.5)
9060 NEXT f
9070 PRINT AT y1,f-1;"   ";AT y1+1,f-1;"   "
9080 PRINT INK 6;AT 6,6;"  @  PAUL STANLEY"
9100 PRINT AT 8,0; INK 5;"A giant bee likes nectar from   giant flowers, but you have to  stop it because you eat nectar  as well!!"
9200 PRINT INK 6'"Chop chunks out of the stalks   with M (but note that once a    piece has been cut out of one   stalk, you must cut the next    piece out of a different stalk)."
9300 PRINT '"Move left with Z & right with X."
9400 PRINT INVERSE 1'"PRESS ANY KEY TO START."
9500 IF INKEY$="" THEN GO TO 9500
9600 CLS : RANDOMIZE : BORDER 5
9700 RESTORE : FOR x=USR "a" TO USR "r"+7
9710 READ n: POKE x,n
9720 NEXT x
9730 DATA 0,2,34,17,9,5,5,5,7,24,32,33,66,66,68,69,128,124,226,34,34,66,130,12,7,13,25,63,63,31,15,7,170,170,170,170
9740 DATA 170,170,170,170,240,248,252,254,252,248,240,224,1,62,71,68,68,66,65,48,224,24,4,132,66,66,34,162,0,64,68,136,144,160,160,160,15,31,63,127
9750 DATA 63,31,15,7,85,85,85,85,85,85,85,85,224,176,152,252,252,248,240,224,96,224,224,112,120,60,30,15,6,6,7,15,30
9760 DATA 60,120,240,108,104,75,139,145,73,81,255,220,220,72,126,72,28,20,20,15,7,3,1,0,0,0,0,240,224,192,128,0,0,0,0
9770 RETURN 

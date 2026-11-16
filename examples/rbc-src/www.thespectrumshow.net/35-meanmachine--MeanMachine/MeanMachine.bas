   1 GO TO 7500
   2 GO SUB 9000
   3 LET d=0
   4 LET ghf=INT (RND*7)
   9 LET gat=0
  10 LET x=2: LET y=14: LET lives=3: LET laps=0
  11 LET z$="{97}": LET b$="5"
  98 POKE 23692,255
 100 PRINT AT 21,0;: FOR n=1 TO 22: INK ghf: PRINT a$(n): NEXT n
 101 INK 9: PRINT AT 9,22;"{90}{92}";AT 10,22;"{99}{98}";AT 16,4;"{90}{92}";AT 17,4;"{99}{98}"
 108 PRINT AT 20,7; INVERSE 1;" LIVES=   LAPS=  ": INVERSE 0
 109 INK ghf
 110 IF INKEY$<>"" THEN LET b$=INKEY$
 111 INVERSE 1: INK 9: PRINT AT 20,14;lives: PRINT AT 20,22;laps: INVERSE 0: INK 0
 112 IF lives=0 THEN GO TO 7000
 113 BEEP .01,-25
 114 BEEP .01,-15
 131 IF b$="6" THEN LET z$="{95}": LET x=x+1: PRINT AT x-1,y;" "
 132 IF b$="7" THEN LET z$="{94}": LET x=x-1: PRINT AT x+1,y;" "
 133 IF b$="8" THEN LET z$="{97}": LET y=y+1: PRINT AT x,y-1;" "
 134 IF b$="5" THEN LET z$="{96}": LET y=y-1: PRINT AT x,y+1;" "
 135 IF y=17 AND x>16 AND d=0 THEN LET d=1
 137 IF y=18 AND x<3 AND d=1 THEN LET laps=laps+1: LET d=0
 140 PRINT AT x,y; INK 1;z$
 148 IF laps=20 AND gat=0 THEN LET gat=1
 149 IF gat=1 THEN GO TO 400
 150 IF a$(x+1,y+1)="{8F}" THEN GO TO 8000
 161 IF (x=9 OR x=10) AND (y=22 OR y=23) THEN GO TO 1000
 162 IF (x=16 OR x=17) AND (y=4 OR y=5) THEN GO TO 1000
 170 GO TO 110
 400 LET lives=lives+1: FOR f=1 TO 20: FOR g=1 TO 30 STEP f: BEEP .01,g: NEXT g: NEXT f: LET gat=2
 401 GO TO 150
1000 FOR m=1 TO 3
1001 PRINT AT x,y;" "
1002 LET x=x+INT (RND*2)
1003 LET y=y+INT (RND*2)
1004 PRINT AT x,y; INK 1;z$
1005 IF a$(x+1,y+1)="{8F}" THEN GO TO 8000
1006 FOR g=1 TO 10: NEXT g: NEXT m
1007 PRINT AT 9,22;"{90}{92}";AT 10,22;"{99}{98}";AT 16,4;"{90}{92}";AT 17,4;"{99}{98}"
1010 GO TO 110
7000 PRINT AT 11,10; INK 9;"ANOTHER GO?"
7009 IF INKEY$="n" THEN STOP 
7010 IF INKEY$="y" THEN GO TO 3
7020 GO TO 7000
7500 INK 1: CLS : PLOT 100,160: DRAW 16,0: DRAW 0,-12: DRAW -4,-4: DRAW 4,0: DRAW 0,-8: DRAW -8,8: DRAW 0,-8: DRAW -8,0: DRAW 0,24
7501 PLOT 107,152: DRAW 4,0: DRAW 0,-4: DRAW -4,0: DRAW 0,4
7502 PLOT 122,152: DRAW 16,0: DRAW 0,-16: DRAW -6,0: DRAW 0,4: DRAW -4,0: DRAW 0,-4: DRAW -6,0: DRAW 0,16: PLOT 128,146: DRAW 4,0: DRAW 0,-4: DRAW -4,0: DRAW 0,4
7503 PLOT 144,152: DRAW 16,0: DRAW 0,-4: DRAW -12,0: DRAW 0,-8: DRAW 12,0: DRAW 0,-4: DRAW -16,0: DRAW 0,16
7504 PLOT 166,152: DRAW 16,0: DRAW 0,-4: DRAW -12,0: DRAW 0,-2: DRAW 8,0: DRAW 0,-4: DRAW -8,0: DRAW 0,-2: DRAW 12,0: DRAW 0,-4: DRAW -16,0: DRAW 0,16
7505 PLOT 186,140: DRAW 4,0: DRAW 0,-4: DRAW -4,0: DRAW 0,4
7506 PLOT 100,134: DRAW 90,0: PLOT 100,132: DRAW 90,0
7510 PRINT AT 6,0;"           By G.N.Woodhead."
7520 PRINT : PRINT "The object of this game is to   drive you blue car round the    race track."
7530 PRINT : PRINT "Beware of the oil slicks!!"
7540 PRINT : PRINT "You start off with 3 cars,but   each time you crash into a wall you lose 1 car..."
7550 PRINT : PRINT "If you manage to survive 20 lapsyou will receive 1 extra car...         GOOD LUCK!!"
7560 PRINT "  5 right 6 down 7 up 8 left    "
7561 PRINT #1;"         PRESS ANY KEY.."
7570 PAUSE 0
7575 CLS 
7580 RUN 2
8000 FOR z=1 TO 6: BEEP .1,-10: PRINT AT x,y; INVERSE 1; INK 2;"*": FOR a=1 TO 21: NEXT a: PRINT AT x,y;z$: NEXT z: BEEP 1,-20: INK ghf: PRINT AT x,y;"{8F}": LET lives=lives-1: LET x=2: LET y=15: LET z$="{96}": INK 9: LET d=0: LET b$="0"
8005 PRINT AT 9,22;"{90}{92}";AT 10,22;"{99}{98}";AT 16,4;"{90}{92}";AT 17,4;"{99}{98}"
8010 GO TO 110
9000 FOR f=USR "a" TO USR "j"+7: READ a: POKE f,a: NEXT f
9001 DATA 15,31,31,63,127,241,245,245
9002 DATA 0,0,0,255,0,0,0,0
9003 DATA 240,248,248,252,254,94,95,95
9004 DATA 8,4,2,255,2,4,8,0
9005 DATA 60,219,255,219,24,219,255,219
9006 DATA 219,255,219,24,219,255,219,0
9007 DATA 119,119,162,255,255,162,119,119
9008 DATA 238,238,69,255,255,69,238,238
9009 DATA 95,67,254,254,252,248,248,240
9010 DATA 245,241,127,127,63,31,31,15
9019 DIM a$(22,32)
9020 LET a$(1)="{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}"
9030 LET a$(2)="{8F}                             {8F}"
9040 LET a$(3)="{8F}                             {8F}"
9050 LET a$(4)="{8F}  {8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}  {8F}{8F}"
9060 LET a$(5)="{8F}  {8F}{8F}       {8F}{8F}{8F}{8F}{8F}{8F}      {8F}{8F}{8F}  {8F}{8F}"
9070 LET a$(6)="{8F}  {8F}{8F}       {8F}{8F}{8F}{8F}{8F}    {8F}{8F} {8F}{8F}{8F}  {8F}{8F}"
9080 LET a$(7)="{8F}  {8F}{8F}  {8F}{8F}{8F}  {8F}{8F}{8F}{8F}    {8F}{8F}{8F} {8F}{8F}{8F}  {8F}{8F}"
9090 LET a$(8)="{8F}      {8F}{8F}{8F}  {8F}{8F}{8F}{8F}  {8F}{8F}{8F}{8F}{8F} {8F}{8F}{8F}  {8F}{8F}"
9100 LET a$(9)="{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}  {8F}{8F}{8F}{8F}   {8F}{8F}{8F}   {8F}{8F}  {8F}{8F}"
9110 LET a$(10)="{8F}{8F}{8F}{8F}          {8F}{8F}   {8F}{8F}     {8F}  {8F}{8F}"
9120 LET a$(11)="{8F}{8F}{8F}{8F}          {8F}{8F}   {8F}{8F}     {8F}{8F} {8F}{8F}"
9130 LET a$(12)="{8F}{8F}{8F}{8F}  {8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}  {8F}{8F}{8F}     {8F}  {8F}{8F}"
9140 LET a$(13)="{8F}{8F}{8F}{8F}  {8F}        {8F}  {8F}{8F}{8F}     {8F}  {8F}{8F}"
9150 LET a$(14)="{8F}{8F}{8F}{8F}  {8F}        {8F}   {8F}{8F}{8F}   {8F}{8F} {8F}{8F}{8F}"
9160 LET a$(15)="{8F}{8F}{8F}{8F}  {8F}   {8F}{8F}   {8F}{8F}   {8F}{8F}  {8F}{8F}{8F}  {8F}{8F}"
9170 LET a$(16)="{8F}{8F}    {8F}   {8F}{8F}{8F}  {8F}{8F}   {8F}{8F} {8F}{8F}{8F}{8F}{8F}  {8F}"
9180 LET a$(17)="{8F}{8F}    {8F}{8F}  {8F}{8F}   {8F}{8F}   {8F}{8F} {8F}{8F}{8F}{8F}{8F}  {8F}"
9190 LET a$(18)="{8F}{8F}        {8F}{8F}        {8F}{8F}  {8F}{8F}{8F}  {8F}{8F}"
9200 LET a$(19)="{8F}{8F}        {8F}{8F}        {8F}{8F}       {8F}{8F}"
9210 LET a$(20)="{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}"
9220 LET a$(21)="{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}"
9230 RETURN 

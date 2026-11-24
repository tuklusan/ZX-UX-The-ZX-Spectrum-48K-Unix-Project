   5 LET hs=0
  10 PAPER 0: CLS : BORDER 0
  20 FLASH 0: OVER 0: INVERSE 0
  30 BRIGHT 0
  35 PRINT AT 10,0; FLASH 1; INK 4;"STOP THE TAPE - PRESS ANY KEY   ": PAUSE 0: CLS 
  40 PRINT INK 2;"RED"; INK 7;"CARPET"''"For the 16K ZX Spectrum"''"By Gavin Devine"''"Move Chris the carpet layer     about the maze laying the QueensRed Carpet, as she is about to  take her first steps into the   stars.One problem:The carpet andstars have burglar alarms and   if Chris touches them he will   be destoryed.Use:"''"Z-Left"'"X-Right"'"C-Down"'"F-Up"''"Press 's' to start"
  45 PAUSE 600
  46 IF INKEY$<>"s" THEN GO TO 45
  50 RESTORE 
  70 FOR f=USR "a" TO USR "b"+7
  80 READ a: POKE f,a
  90 NEXT f
  95 CLS 
 100 LET s=0
 120 PRINT : PRINT INK 6;"*********************************              *               ** ** ********* * ********** ***** **         * * *          ***** ********** * * * **************                              ** **************************** **                              ******* ****************** *******    *                    *    ** **   *******   ********   ** ** **         *   *          ** **    * ***** * * * ****** *    *******         *          **** **      ******************      ** **** *                * **** **                              *"
 130 PRINT INK 6;"**********            ***********                              *********************************"
 140 LET a=18: LET b=15
 145 LET e=-1: LET f=0
 150 PRINT AT a,b; INK 7;"{90}"
 151 REM BEEP .02,1
 160 BEEP .01,0: BEEP .01,1: BEEP .01,2: BEEP .01,3: BEEP .01,4: BEEP .01,5: BEEP .01,6: BEEP .01,7
 170 IF INKEY$="z" THEN LET e=-1: LET f=0
 180 IF INKEY$="x" THEN LET e=1: LET f=0
 190 IF INKEY$="c" THEN LET f=1: LET e=0
 200 IF INKEY$="f" THEN LET f=-1: LET e=0
 210 PRINT AT a,b; INK 2;"{8F}"
 220 IF SCREEN$ (a+f,b+e)="*" THEN GO TO 250
 225 IF ATTR (a+f,b+e)=BIN 00000010 THEN GO TO 250
 230 LET s=s+1: LET a=a+f: LET b=b+e
 235 PRINT AT 0,0; INK 7; INVERSE 1;"SCORE=";s;" HI=";hs
 240 GO TO 150
 250 PRINT AT a+f,b+e, FLASH 1; INK 6; PAPER 2;"{91}": FOR k=1 TO 20: BEEP .01,5: NEXT k: BEEP .1,10: BEEP .01,10
 260 IF s>hs THEN GO TO 300
 270 PRINT AT 21,8;"Instructions<y/n> ?": INPUT a$: IF a$="y" THEN CLS : GO TO 40
 280 CLS 
 290 GO TO 100
 300 CLS : PAPER 6: CLS 
 310 INK 0
 320 PRINT AT 1,3;"{8F}{8F}{8F}     {8F}{8F}{8F}    {8F}{8F}{8F}{8F}{8F}{8F}{8F}           {8F}       {8F}        {8F}              {8F}       {8F}        {8F}              {8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}        {8F}              {8F}       {8F}        {8F}              {8F}       {8F}        {8F}             {8F}{8F}{8F}     {8F}{8F}{8F}    {8F}{8F}{8F}{8F}{8F}{8F}{8F}"
 330 PRINT AT 10,1;"{8F}{8F}{8F}{8F}{8F}  {8F}{8F}{8F}   {8F}{8F}{8F}  {8F}{8F}{8F}{8F}  {8F}{8F}{8F}{8F}{8F}   {8F}     {8F}   {8F} {8F}   {8F} {8F}   {8F} {8F}       {8F}{8F}{8F}{8F}{8F} {8F}     {8F}   {8F} {8F}{8F}{8F}{8F}  {8F}{8F}{8F}{8F}        {8F} {8F}   {8F} {8F}   {8F} {8F} {8F}   {8F}       {8F}{8F}{8F}{8F}{8F}  {8F}{8F}{8F}   {8F}{8F}{8F}  {8F}  {8F}  {8F}{8F}{8F}{8F}{8F}"
 340 PRINT AT 17,1;"{8F}{8F}{8F} {8F}  {8F}{8F}                       {8F} {8F} {8F}  {8F} {8F} {83}{83} ";hs
 350 PRINT AT 19,1;"{8F}{8F}{8F} {8F}{8F} {8F}{8F}  {83}{83}"
 360 FOR f=1 TO 250: NEXT f
 370 PRINT AT 17,1;"{8F} {8F} {8F}{8F} {8F} {8F} {8F}                    {8F}{86}{8F} {8F}{8C} {8F} {8F} {8F}                    {8F} {8F} {8F}{8C}  {8F} {8F}     "
 380 FOR f=1 TO 25: PRINT AT 21,f;s: BEEP .05,f: PRINT AT 21,f-1;" ": NEXT f
 390 FOR f=21 TO 18 STEP -1: PRINT AT f,25;s: BEEP .05,f: PRINT AT f,25;"    ": NEXT f
 400 FOR f=25 TO 14 STEP -1: PRINT AT 18,f+3;" ";AT 18,f;s: BEEP .05,f: NEXT f
 410 PRINT AT 18,14;s;"    "
 412 FLASH 0: PAPER 0: INK 7
 420 LET hs=s: GO TO 270
1000 DATA 24,24,126,24,24,36,36,36
1010 DATA 153,90,60,255,255,60,90,153

   1 REM **GRANDPRIX**
   2 BORDER 0: PAPER 0: INK 7: CLS 
   5 DIM b$(3,15): DIM i(3): FOR f=1 TO 3: LET b$(f)="": LET i(f)=0: NEXT f
   6 GO SUB 8000
   7 CLS 
   8 INPUT "Enter skill (1-good to 4-bad) ";sk: IF sk<1 OR sk>4 THEN GO TO 8
   9 INPUT "How many laps? ";laps: IF laps<1 THEN GO TO 9
  10 INPUT "1-Hard Or 2-Easy Circuit? ";ci: IF ci<>1 AND ci<>2 THEN GO TO 10
  15 GO SUB 9000
  20 PRINT AT 2,17;"READY": BEEP .5,0: PRINT AT 2,17;"STEADY": BEEP .5,5: PRINT AT 2,17;"  GO  ": BEEP .2,10: PRINT AT 2,19;"  "
  70 IF INKEY$="1" THEN LET g=1: BEEP .05,50
  80 IF INKEY$="2" THEN LET g=2: BEEP .05,50
 100 LET po=po+(INKEY$="7" AND po<151)-(7 AND INKEY$="7" AND po=151)-(INKEY$="6" AND po>144)+(7 AND INKEY$="6" AND po=144): IF x<5 THEN LET c=1
 105 FOR f=1 TO g
 110 LET y=y-(po>144 AND po<148)+(po>148): LET x=x-(po<146 OR po=151)+(po>146 AND po<150)
 115 IF SCREEN$ (y,x)="" THEN LET y=y1: LET x=x1: BEEP .02,-10: LET po=INT (RND*8)+144
 120 PRINT OVER 1; INK 0;AT y1,x1;CHR$ po1; OVER 1; INK 7;AT y,x;CHR$ po
 125 LET y1=y: LET x1=x: LET po1=po
 130 IF y=11 THEN IF x>27 THEN IF c=1 THEN BEEP .1,10: LET l1=l1+1: PRINT AT 0,10;l1: LET c=0: IF l1=laps+1 THEN GO TO 5000
 140 NEXT f
 150 LET cy=cy-(cpo>144 AND cpo<148)+(cpo>148): LET cx=cx-(cpo<146 OR cpo=151)+(cpo>146 AND cpo<150)
 152 IF SCREEN$ (cy,cx)="" THEN BEEP .02,-20: LET cy=cy1: LET cx=cx1: LET cpo=cpo1
 160 IF SCREEN$ (cy,cx)="-" THEN READ q: LET cpo=cpo+q
 165 IF cy=13 THEN IF cx=30 THEN RESTORE 9400
 170 PRINT OVER 1; INK 0;AT cy1,cx1;CHR$ cpo1; INK 3; OVER 1;AT cy,cx;CHR$ cpo
 175 LET cy1=cy: LET cx1=cx: LET cpo1=cpo
 200 IF cy=11 THEN IF cx=30 THEN LET l2=l2+1: BEEP .1,15: PRINT AT 0,30;l2: IF l2=laps+1 THEN GO TO 5000
 500 GO TO 70
5000 FOR f=1 TO 40: BEEP .01,f: NEXT f
5001 CLS 
5002 LET sc=40/ci+60/sk
5005 IF cy=11 AND cx=30 THEN LET sc=-sc
5007 LET sc=sc+(l1-l2)*2
5010 IF sc<0 THEN PRINT AT 2,0;"Bad Luck! You Were Beaten."
5011 IF sc>0 THEN PRINT AT 2,0;"Well Done! You Were The Winner."
5013 PRINT '"Your Score Is ";sc
5014 IF sc<i(3) THEN GO TO 5050
5015 PRINT INK 5;AT 6,0;"Your Score Is Good Enough To Be Included In The Top Scores.     Please Enter Your Name.": INPUT n$: IF LEN n$>15 THEN GO TO 5015
5020 IF sc>i(1) THEN LET i(3)=i(2): LET i(2)=i(1): LET i(1)=sc: LET b$(3)=b$(2): LET b$(2)=b$(1): LET b$(1)=n$: GO TO 5050
5030 IF sc>i(2) THEN LET i(3)=i(2): LET i(2)=sc: LET b$(3)=b$(2): LET b$(2)=n$: GO TO 5050
5040 LET i(3)=sc: LET b$(3)=n$
5050 PRINT '"These Are The Best Scores:": FOR f=1 TO 3: PRINT 'f;"...";b$(f);TAB 23;i(f): NEXT f
5060 PRINT ' INK 6'"Press Any Key To Play Again.": PAUSE 0: GO TO 6
8000 LET a$="GRAND PRIX - BY PAUL STANLEY - "
8010 PRINT AT 2,0;"Steer Your Car Around The Race- track And Try To Beat A Car     Driven By The Computer."
8020 PRINT INK 5'"Turn Left With ""6"" And Right    With ""7"". You Can Select Gears  With 1(Slow) And 2 (Fast).The   Computer Will Stay In First At  All Times."
8030 PRINT INK 6'"If You Crash You Will Restart   In A Random Direction, So You   Must Sort Yourself Out As Fast  As Possible."
8035 PRINT '"Your Car Is The White One."
8040 PRINT INK 4'"PRESS ANY KEY TO CONTINUE."
8050 PRINT PAPER 2; INK 6;AT 0,0;A$;AT 21,0;a$: LET A$=a$(2 TO 31)+a$(1): PAUSE 3: IF INKEY$="" THEN GO TO 8050
8060 RETURN 
9000 RESTORE 9005: FOR y=USR "a" TO USR "i"+7: READ x: POKE y,x: NEXT y
9005 DATA 0,110,132,252,252,132,110,0,40,108,240,58,223,76,24,8
9010 DATA 60,90,90,24,90,126,90,0,20,54,15,92,251,50,24,16
9020 DATA 0,118,33,63,63,33,118,0,16,24,50,251,92,15,54,20
9030 DATA 0,90,126,90,24,90,90,60,8,24,76,223,58,240,108,40
9040 DATA 60,66,189,165,165,189,66,60
9100 PRINT AT 1,0; INK 4;"  {98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}   {98}{98}                          {98}{98} {98}{98}                            {98}{98}{98}               {98}{98}{98}{98}{98}{98}{98}{98}{98}      {98}{98}              {98}{98}    {98}  {98}{98}     {98}{98}             {98}{98}     {98}   {98}{98}    {98}{98}    {98}{98}{98}{98}{98}{98}{98}{98}{98}{98}      {98}    {98}{98}   {98}"
9110 PRINT INK 4;"{98}          {98}         {98}     {98}   {98}{98}          {98}         {98}     {98}   {98}{98}          {98}    {98}    {98}     {98}   {98}{98}{98}         {98}   {98}{98}{98}   {98}     {98}   {98} {98}{98}{98}{98}{98}{98}    {98}   {98} {98}   {98}     {98}   {98}      {98}{98}   {98}   {98} {98}   {98}     {98}   {98} {98}{98}{98}{98}{98}{98}    {98}   {98} {98}   {98}     {98}   {98}"
9120 PRINT INK 4;"{98}{98}         {98}   {98} {98}   {98}{98}   {98}{98}   {98}{98}          {98}   {98} {98}    {98}{98}{98}{98}{98}    {98}{98}     {98}{98}{98}{98}{98}{98}   {98} {98}             {98}{98}              {98} {98}             {98}{98}              {98} {98}             {98}{98}{98}            {98}{98} {98}{98}          {98}{98} {98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}   {98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}{98}"
9130 PRINT AT 11,27;"     "
9150 IF ci=1 THEN PRINT INK 4;AT 3,6;"{98}{98}";AT 4,5;"{98}{98}";AT 8,2;"{98}";AT 9,2;"{98}{98}";AT 17,3;"{98}";AT 18,3;"{98}";AT 8,18;"{98}";AT 13,28;"{98}"
9190 DATA 3,9,3,24,6,5,6,6,7,4,8,4,9,5,9,6,9,15,9,16,9,30,11,8,11,18,12,12,13,8,14,30,15,5,15,6,15,18,16,4,17,4,17,12,17,20,17,27,18,5,18,11
9200 DATA 3,8,3,25,6,4,6,5,7,3,8,3,8,30,9,4,9,5,9,16,9,17,10,18,12,8,12,13,13,8,13,18,13,30,15,5,15,6,16,4,16,13,17,4,17,22,17,26,18,5,18,11
9210 DATA 2,12,2,26,5,3,5,9,6,30,7,1,7,17,7,18,8,19,9,1,10,2,10,7,10,14,12,9,15,9,15,30,16,3,16,8,16,14,16,19,17,2,18,2,19,3,19,11,20,23,20,25
9220 DATA 2,6,2,27,4,2,4,4,5,1,5,30,7,16,7,18,9,20,9,1,9,14,10,2,10,7,13,10,14,10,16,30,16,3,16,8,17,14,17,20,18,1,19,1,19,22,19,27,20,2,20,11
9290 RESTORE 9180+sk*10
9300 FOR l=1 TO 26: READ y,x: PRINT INK 0;AT y,x;"-": NEXT l
9350 RESTORE 9400
9370 LET l=-1
9400 DATA l,l,7,-7,7,l,l,l,-l,-l,-l,-7,7,l,l,l,l,l,-l,-l,-l,-l,l,l,l,l
9500 LET po=146: LET cpo=146
9510 LET y=10: LET x=28: LET cy=y: LET cx=30
9520 LET y1=y: LET x1=x: LET po1=po
9522 LET cy1=cy: LET cx1=cx: LET cpo1=cpo
9528 LET l1=1: LET l2=l1
9529 LET g=1: LET c=0
9530 PRINT AT y,x; OVER 1;CHR$ po;" "; INK 3;CHR$ cpo
9540 PRINT AT 0,0;"YOUR LAPS:";L1;"   COMPUTER's LAPS:";L2
9600 RETURN 

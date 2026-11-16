   1 PAPER 1: INK 7: BORDER 1: CLS 
   2 REM ********************
   3 REM ** @ PAUL STANLEY **
   4 REM ********************
   5 GO SUB 8000
   7 LET hs=0
  10 GO SUB 9000
  15 LET sk=.98: LET s=0
  20 LET a$="{90}": LET b$="{91}": LET c$="{92}": LET x=27
  21 DIM d$(28)
  25 LET g=1: LET h=INT (RND*28)+2
  26 PRINT AT 0,18;"HIGH-SCORE:";hs
  27 LET p=0
  28 PRINT AT 0,0;"PRESENTS:";s
  30 IF INKEY$="x" THEN LET x=x+(2 AND x<27): LET a$="{93}": LET b$="{94}": LET c$="{95}"
  35 IF INKEY$="z" THEN LET x=x-(2 AND x>1): LET a$="{90}": LET b$="{91}": LET c$="{92}"
  40 PRINT AT 10,x-2;"       ";AT 10,x; INK 2;a$; INK 0;b$; INK 2;c$;
  50 IF NOT p THEN LET g=g+1: PRINT AT g-1,h;" ";AT g,h; INK 6;"{96}": IF g=10 THEN IF h=x+2 OR h=x+1 OR h=x THEN LET p=1
  60 IF g=12 THEN IF SCREEN$ (g+1,h)=":" THEN GO TO 1000
  65 IF g=12 THEN PRINT AT 12,h;" ": LET g=1: LET h=INT (RND*28)+2
  70 IF p THEN IF INKEY$="m" THEN LET g=10: LET h=x-1+(a$="{93}")+(3 AND c$="{92}"): LET p=0
  80 IF RND>sk THEN LET q=INT (RND*7)+1: LET e=INT (RND*4): PRINT PAPER 3;AT 16,q*4-e+1;" ": LET d$(q*4-e)="p": IF d$(q*4-3 TO q*4)="pppp" THEN GO TO 2000
  90 GO TO 30
1000 PRINT AT 12,h;" "
1010 IF SCREEN$ (18,h)="_" THEN GO TO 25
1015 LET s=s+1: PRINT AT 0,0;"PRESENTS:";s
1020 PRINT AT 18,h; INK 0; PAPER 6;"__";AT 19,h;"__"
1022 FOR f=1 TO 3: BEEP .001,30: NEXT f
1025 FOR f=4 TO 28 STEP 4: IF SCREEN$ (18,f)="_" THEN NEXT f: LET sk=sk-.02: CLS : GO SUB 9030: GO TO 20
1030 GO TO 25
2000 IF SCREEN$ (18,q*4)<>"_" THEN GO TO 6000
2010 GO TO 30
5000 RESTORE 5100: LET z=.3: LET c=.6: FOR f=1 TO 26: READ a,b: BEEP a,b: NEXT f
5100 DATA z,6,z,6,c,6,z,6,z,6,c,6,z,6,z,9,z,2,z,4,1,6,z,6,z,7,z,7,z,7,z,7,z,7,z,6,z,6,z,6,z,9,z,9,z,7,z,4,c,2,c,2
5200 RETURN 
6000 FOR f=10 TO 1 STEP -.5: PRINT AT f,x; INK 2;a$; INK 0;b$; INK 2;c$;AT f+1,x;"   ": BEEP .005,2*f: NEXT f
6002 IF s>hs THEN LET hs=s
6005 PRINT AT 1,x;"   "
6006 PRINT AT g,h;" "
6010 PRINT FLASH 1;AT 18,q*4-1; INK 0; PAPER 6;"__";AT 19,q*4-1;"{9A}_"
6030 PRINT AT 8,8; FLASH 1;"G A M E  O V E R"
6045 GO SUB 5000
6050 PRINT AT 11,2; FLASH 1;"PRESS ANY KEY TO PLAY AGAIN"
6060 IF INKEY$<>"" THEN CLS : GO TO 10
6070 GO TO 6060
8000 PRINT INVERSE 1;AT 5,0;"   C H R I S T M A S  E V E    "' INVERSE 0''"       @   PAUL STANLEY": PAUSE 250: CLS 
8010 PRINT '"It is approaching midnight on   Christmas eve and Santa is late.You play the part of Santa and  you must deliver presents which are thrown down to you by your  elves. Having caught a present  (by flying directly below it)   you must move over a chimney    and drop a present down it."
8020 PRINT '"When a present has been dropped down a chimney the famiy in     that house immediately start    work on opening up the present  and they will turn the light on.Dropping another present down   a chimney of a lit house will   not count."
8030 PRINT ' INVERSE 1;"PRESS ANY KEY TO SEE MORE.": PAUSE 0
8040 CLS : PRINT "Beneath each roof you will see  a patch of snow which melts as  time elapses. This melts at a   rate which is proportional to   the activity in the house."
8050 PRINT '"As the presents must be placed  down the chimneys before anyone sees you, if all the snow has   melted under a particular roof  without a present being dropped before this occurs it will      indicate that the inhabitants   are awake and you will have to  return immediately."
8060 PRINT '"    Z------------------LEFT         X-----------------RIGHT         M----------DROP PRESENT"
8070 PRINT ' INVERSE 1;"     PRESS ANY KEY TO START     ": PAUSE 0: CLS : RETURN 
9000 RESTORE 9010: FOR y=USR "a" TO USR "k"+7: READ x: POKE y,x: NEXT y
9010 DATA 0,0,1,0,0,0,0,0
9020 DATA 192,64,160,224,127,126,99,82
9030 DATA 8,28,8,124,156,72,63,128
9040 DATA 16,56,16,62,56,18,252,1
9050 DATA 3,2,5,7,254,126,198,74
9060 DATA 0,0,128,0,0,0,0,0
9070 DATA 0,0,0,54,54,0,54,54
9080 DATA 0,1,3,7,15,31,63,127
9090 DATA 0,128,192,224,240,248,252,254
9100 DATA 255,220,73,65,64,0,0,0
9110 DATA 24,60,{C4}01010110,60,24,126,255,255
9300 FOR x=2 TO 26 STEP 4
9310 PRINT INK 3;AT 13,x+1;":"; PAPER 3; INK 5;AT 14,x+1;"{97}"; PAPER 1;"{98}";AT 15,x;"{97}{8F}{8F}{98}"; INK 7; PAPER 3;AT 16,x;"{99}{99}{99}{99}";AT 17,x; PAPER 1; INK 3;"{8F}{8F}{8F}{8F}";AT 18,x;"{8F}  {8F}";AT 19,x;"{8F}  {8F}";AT 20,x;"{8F}{8F}{8F}{8F}";AT 21,x;"{8F}{8F}{8F}{8F}"
9320 NEXT x
9400 FOR x=48 TO 208 STEP 32: OVER 1: INK 3: PLOT x,0: DRAW 0,39: NEXT x: INK 7: OVER 0
9450 FOR x=24 TO 216 STEP 32: PLOT x,23: DRAW 15,0: NEXT x
9500 RETURN 

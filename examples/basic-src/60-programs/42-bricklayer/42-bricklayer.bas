   1 PAPER 5: BORDER 5: CLS 
   2 GO SUB 4000
   3 PAUSE 100
   5 LET hs=0
  10 GO SUB 180
  15 PRINT AT 0,13;"HI:";hs
  20 LET x=x+f
  30 IF x=0 OR x=29 THEN BEEP .04,10: LET f=-f
  32 PRINT AT 0,0;"SCORE:";s;AT 0,24;"LIVES:";lives;" "
  40 PRINT AT 1,x;" {91} "
  50 IF INKEY$="z" THEN IF t<>1 THEN LET t=1: LET k=x+1: LET l=2
  55 IF INKEY$="m" AND x>3 AND x<27 THEN IF z<>1 THEN LET z=1: LET q=x+1: LET i=2
  60 IF t=1 THEN PRINT AT l,k;" ": LET l=l+1: PRINT AT l,k;"{92}": BEEP .002,0: IF SCREEN$ (l+1,k)<>" " THEN GO SUB 140
  65 IF z=1 THEN PRINT AT i,q;" ": LET i=i+1: PRINT AT i,q;"{93}": BEEP .002,-5: IF SCREEN$ (i+1,q)<>" " THEN GO SUB 160
  70 IF l=21 THEN PRINT AT l,k;" ": LET t=0
  75 IF i=21 THEN LET s=s+b*2: BEEP .1,20: PRINT AT i,q;" ": LET i=0: LET z=0
 110 LET a=a+c
 115 PRINT AT b,a; INK RND*3; PAPER 7;"{90}"
 120 IF a<3 OR a>27 THEN LET c=-c: LET b=b-1
 125 IF b=3 THEN GO TO 1000
 130 GO TO 20
 140 PRINT AT l,k;" ": PRINT AT l+1,k-2;"     ": LET t=0: IF l<20 THEN PRINT AT l+2,k-1;"   "
 150 RETURN 
 160 PRINT AT i,q; FLASH 1;"*": LET lives=lives-1: BEEP .1,-30: BEEP .1,-25: LET z=0: PRINT AT i,q;" ";AT i+1,q-1;"   ": IF lives=0 THEN GO TO 1000
 166 RETURN 
 180 DATA 0,126,126,126,126,126,126,126
 181 DATA 0,24,118,219,255,110,24,0
 182 DATA 231,126,60,60,60,60,60,24
 183 DATA 28,28,8,62,8,8,20,34
 190 FOR a=USR "a" TO USR "d"+7: READ b: POKE a,b: NEXT a
 191 LET a=27: LET b=20
 192 LET c=-.6: LET t=0: LET l=1: LET z=0: LET i=1
 193 LET x=0: LET f=1
 194 LET s=0
 197 LET lives=10
 200 RETURN 
1000 IF lives=0 THEN PRINT AT 0,30;"0"
1010 FOR o=-30 TO 30 STEP 2
1020 BEEP .01,o
1025 NEXT o
1030 PRINT FLASH 1;AT 15,7;"ANOTHER GAME?"
1035 IF s>hs THEN LET hs=s
1040 INPUT a$
1050 IF a$(1)="y" THEN GO SUB 191: CLS : PAUSE 100: GO TO 15
1060 STOP 
4000 PRINT AT 1,10;"BRICK LAYER"
4010 PRINT AT 1,10; OVER 1;"___________"
4013 PRINT '"The object is to drop humanoids from the spacecraft at the top  of the screen                     As the game progresses a wall will be built up, starting from the bottom.Holes can be made in this by releasing a bomb.         You have 10 lives and each    time a humanoid hits the wall a life will be lost."
4015 PRINT ''"   Z...........DROPS BOMBS         M....RELEASES HUMOIDS"
4017 PRINT INVERSE 1;'"Press any key to start."
4020 PAUSE 0
4025 CLS 
4030 RETURN 

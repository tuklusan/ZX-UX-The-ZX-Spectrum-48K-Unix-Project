   1 BORDER 0: INK 6: BRIGHT 1: PAPER 0: CLS 
  10 GO SUB 9000
  20 GO SUB 8000
  50 LET hs=0
  70 PRINT FLASH 1;" ----- ASTEROIDS DETECTED ----- ": FOR F=1 TO 4: FOR d=-20 TO 0: BEEP .02,d: NEXT d: NEXT f
  90 LET x1=x
 100 LET x=x+(INKEY$="x" AND x<26)-(INKEY$="z" AND x>5)
 105 IF (ATTR (7,x)=71 OR ATTR (7,x)=66) THEN IF SCREEN$ (7,x)="" THEN LET hit=1
 107 IF ATTR (7,x)=68 THEN FOR d=0 TO 60 STEP 20: BEEP .01,d: NEXT d: LET sc=sc+1
 110 POKE 23692,255: PRINT AT 6,x1;" ";AT 21,31;"  "; INK 4;AT 6,x;"{90}"
 112 IF q=6 THEN IF w=x THEN BEEP .01,20: BEEP .01,10: BEEP .01,20: GO SUB 4100
 115 IF hit=1 THEN LET hit=0: BEEP .1,-10: GO SUB 4100
 117 IF INKEY$="m" THEN GO SUB 5000
 120 LET l=INT (RND*30): LET g=(INT (RND*3)*2)+1: PRINT INK 7;AT 20,l;a$(g TO g+1);AT 21,l;b$(g TO g+1)
 125 IF c>400 THEN LET l=INT (RND*30): LET g=(INT (RND*3)*2)+1: PRINT INK 7;AT 20,l;a$(g TO g+1);AT 21,l;b$(g TO g+1)
 130 IF c=200 THEN LET a$="{92}{93}{91} {9A} ": LET b$="{94}{95}    "
 135 IF c=300 THEN LET a$="{92}{93}{92}{93}{92}{93}": LET b$="{94}{95}{94}{95}{94}{95}"
 140 IF RND>.6 THEN PRINT INK 4;AT 21,RND*30;"{96}"
 150 IF RND<.4 THEN PRINT INK 2;AT 21,RND*30;"{97}"
 160 IF ATTR (8,x)=66 OR ATTR (9,x)=66 OR ATTR (10,x)=66 OR ATTR (11,x)=66 THEN GO SUB 400
 185 LET c=c+1
 187 IF c>400 THEN GO TO 90
 190 LET q=q-2: PRINT INK 5;AT q,w;"{98}";AT q+1,w;" ": IF q=0 THEN LET q=20: LET w=x
 200 GO TO 90
4000 LET d=88*(ATTR (11,x)=66)+96*(ATTR (10,x)=66)+104*(ATTR (9,x)=66)+112*(ATTR (8,x)=66): IF d>112 THEN LET d=112
4005 PLOT x*8+3,d: DRAW INK 6;0,120-d: FOR f=35 TO 40: BEEP .002,f: NEXT f: PLOT OVER 1;x*8+3,d: DRAW OVER 1;0,120-d
4100 FOR g=1 TO 2: FOR f=5 TO 0 STEP -1: PRINT AT f,x-5+f;".";AT f,x+5-f;".";AT 10-f,x-5+f;".";AT 10-f,x+5-f;".";AT f,x;".";AT 10-f,x;".";AT 5,x+5-f;".";AT 5,x-5+f;"."
4110 NEXT f: OVER 1: NEXT g: OVER 0: PRINT AT 5,x;" "
4130 LET li=li-1: PRINT FLASH 1;AT 0,0;"LIVES LEFT:";li;TAB 23;"SCORE:";sc: FOR f=-30 TO 0: BEEP .02,f: NEXT f
4135 IF li<>0 THEN RETURN 
4137 FOR f=1 TO 4: BEEP .3,0: BEEP .6,10: FOR g=1 TO 20: NEXT g: NEXT f
4140 CLS : PRINT AT 5,0;"You scored ";sc;" points."
4145 PRINT ''"The high-score is ";hs;"."
4150 IF sc>hs THEN LET hs=sc: PRINT INK 5''"Congratulations!"'"That is a new  high score."
4160 PRINT INVERSE 1''"PRESS ANY KEY TO PLAY AGAIN."
4170 PAUSE 0: CLS : GO SUB 9500: GO TO 70
5000 LET sc=sc-1: FOR f=7 TO 17
5010 PRINT AT f,x;".": BEEP .001,30
5020 PRINT AT f,x;" ": IF SCREEN$ (f+1,x)="" THEN GO TO 5030
5025 NEXT f
5030 IF ATTR (f+1,x)<>71 THEN RETURN 
5040 PRINT AT f+1,x;" ": FOR d=1 TO 3: BEEP .03,-20: NEXT d
5050 IF RND>.4 THEN RETURN 
5055 LET t=INT (RND*4)+1
5060 FOR d=0 TO t: PRINT AT f+1-d,x-d; INK 7;"{91}";AT f+1-d,x+d;"{91}";AT f+1+d,x-d;"{91}";AT f+1+d,x+d;"{91}"
5065 BEEP .03,-40
5070 IF d<t THEN PRINT AT f+1-d,x-d;" ";AT f+1-d,x+d;" ";AT f+1+d,x-d;" ";AT f+1+d,x+d;" "
5080 NEXT d: RETURN 
8000 PRINT INVERSE 1;"    S P A C E  T R A F F I C    "''"        BY PAUL STANLEY         "
8010 PRINT INK 7'"You are flying through space    when suddenly you encounter an  asteroid belt."
8020 PRINT INK 4'"Enemy craft will fire at you    given the chance, and other     missiles are aimed right at     you."
8030 PRINT '"To score you have to recover    lost satellites in your craft."
8040 PRINT INK 5'"If you are desperate, you can   fire at asteroids, but you lose a satellite in the process."
8050 PRINT '"Move left with Z, right with X, and fire with M"
8060 INPUT PAPER 6; INK 3;"      PRESS ENTER TO START     "; LINE q$
8070 CLS : RETURN 
9000 FOR x=USR "a" TO USR "k"+7: READ y: POKE x,y: NEXT x
9010 DATA 254,124,40,124,40,56,16,16,0,48,72,84,72,48,0,0,1,2,60,64,160,132,136,129
9020 DATA 224,152,8,136,70,9,17,145,130,144,121,5,4,5,6,3,133,3,20,72,16,32,32,192
9030 DATA 129,66,60,36,36,60,66,129,16,16,56,84,84,56,16,124,0,16,8,16,32,16,16,56
9040 DATA 24,54,41,66,169,130,84,56,38,91,162,152,130,106,60,4
9500 LET a$="{91} {99} {9A} ": LET b$="      ": LET x=15: LET c=0: LET hit=0: LET sc=0
9510 LET q=20: LET w=x: LET li=5
9700 RETURN 

   1 RANDOMIZE : BORDER 0: PAPER 0: INK 7: CLS 
   5 LET hs=0
  10 GO SUB 9000
  50 GO SUB 5000
  70 LET sc=0
  80 LET li=5
 100 FOR f=0 TO 30: PRINT INK 4; PAPER 7;AT 0,f;"{96}";AT 20,f;"{96}": NEXT f: FOR f=1 TO 19: PRINT INK 4; PAPER 7;AT f,0;"{96}";AT f,30;"{96}": NEXT f
 103 GO SUB 2000
 107 FOR i=1 TO 30: PRINT AT INT (RND*10)*2,INT (RND*15)*2; PAPER 7; INK 4;"{96}": NEXT i
 110 LET sc=sc-1: LET y=1: LET x=y: LET f=19: LET g=29: LET a$="{92}"
 115 PRINT AT 21,5;"HI-SC:";hs;AT 21,16;"LI:";li;AT 21,23;"SCORE:0"
 120 LET b$="{90}{91}": LET c=1
 130 GO SUB 1500
 200 FOR i=1 TO 2
 201 LET c=c-1: PRINT AT 21,0;c;" ": IF c=0 THEN GO TO 3500
 205 IF RND>.97 THEN GO SUB 1600
 210 PRINT AT y,x;" "
 220 IF INKEY$="8" THEN IF ATTR (y,x+1)<>60 THEN LET x=x+1
 230 IF INKEY$="5" THEN IF ATTR (y,x-1)<>60 THEN LET x=x-1
 240 IF INKEY$="7" THEN IF ATTR (y-1,x)<>60 THEN LET y=y-1
 250 IF INKEY$="6" THEN IF ATTR (y+1,x)<>60 THEN LET y=y+1
 255 IF ATTR (y,x)>128 THEN GO SUB 1500
 257 IF (x=b(1) AND y=a(1)) OR (x=b(2) AND y=a(2)) OR (x=b(3) AND y=a(3)) OR (x=b(4) AND y=a(4)) THEN GO TO 3000
 260 PRINT INK 6;AT y,x;b$(i): GO SUB 1000
 270 NEXT i
 280 GO TO 200
1000 LET f1=f: LET g1=g
1010 IF f<y THEN LET a$="{95}": LET f=f+.5
1020 IF f>y THEN LET a$="{94}": LET f=f-.5
1030 IF g<x THEN LET a$="{93}": LET g=g+.5
1040 IF g>x THEN LET a$="{92}": LET g=g-.5
1050 PRINT INK 3;AT f1,g1;" ";AT f,g;a$
1060 IF ATTR (y,x)=3 THEN GO TO 3100
1070 PRINT AT INT (RND*10)*2,INT (RND*15)*2; PAPER 7; INK 4;"{96}"
1100 RETURN 
1500 LET sc=sc+1: PRINT AT 21,29;sc
1501 FOR l=1 TO 5: BEEP .01,l*5: NEXT l
1502 LET c=50
1505 LET q=INT (RND*10)*2+1: LET w=INT (RND*15)*2+1: PRINT PAPER 6; FLASH 1; INK 2;AT q,w;"{97}"
1510 RETURN 
1600 PRINT AT q,w;" ": LET l=q: LET m=w: LET l1=f: LET m1=g: LET f=1: LET g=m: LET q=l1: LET w=m1
1605 PRINT AT q,w; PAPER 6; INK 2; FLASH 1;"{97}"
1606 LET t=1
1610 RETURN 
2000 DIM a(4): DIM b(4)
2010 FOR i=1 TO 4: LET a(i)=INT (RND*10)*2+1: LET b(i)=INT (RND*15)*2+1: NEXT i
2020 FOR i=7 TO 0 STEP -1: FOR l=1 TO 4: PRINT INK i;AT a(l),b(l);"{8F}": BEEP .01,l*i: BEEP .01,-l*i: NEXT l: NEXT i
2030 RETURN 
3000 FOR l=1 TO 3: FOR i=7 TO 0 STEP -1: PRINT AT y,x; INK i;"{90}": BEEP .05,i*8: NEXT i: NEXT l
3010 GO TO 3600
3100 FOR l=1 TO 3: FOR i=7 TO 0 STEP -1: PRINT AT y,x; INK i;"{95}": BEEP .1,-i*4: NEXT i: NEXT l
3120 GO TO 3600
3500 FOR l=1 TO 15: FOR i=1 TO 3: BEEP .02,l*i: PRINT AT q,w; INK RND*7;"{97}": NEXT i: NEXT l
3600 PRINT AT y,x;" ";AT f,g;" ";AT q,w;" "
4000 LET li=li-1: IF li>0 THEN BEEP .3,0: GO TO 110
4002 CLS : FOR f=0 TO 20: BEEP .02,f: NEXT f: PRINT ''"You scored ";sc;" point";("s" AND sc<>1);"."
4010 IF sc>hs THEN LET hs=sc: PRINT INK 4''"WELL DONE!  A NEW HIGH-SCORE!": GO SUB 9100
4015 PRINT INK 5''"The high-score is ";hs
4018 PRINT ' INK 6' FLASH 1;"PRESS ANY KEY TO PLAY AGAIN"
4019 IF INKEY$="" THEN GO TO 4019
4020 CLS : GO TO 70
5000 PRINT FLASH 1;"   {92} M {93} U {94} T {95} A {92} N {93} T {94}    "
5010 PRINT FLASH 1;'"        {92} R {93} A {94} T {95} S {92}       "
5030 FOR y=0 TO 2 STEP 2: FOR i=0 TO 31
5035 BEEP .04,RND*40
5040 IF SCREEN$ (y,i)<>"{8F}" AND SCREEN$ (y,i)<>"" THEN PRINT AT y,i; BRIGHT 1; INK 2; PAPER 7;SCREEN$ (y,i)
5050 NEXT i: NEXT y
5055 PRINT '"    @ P a u l  S t a n l e y"
5060 PRINT ''"The giant rat is out to get you!You must try and reach the girl before she mutates (a timer at  the bottom of the screen counts this down)."
5070 PRINT INK 5''"However she might be mutant     herself and change places with  the rat unpredictably. Also she might disappear totally (if she meets the rat, she will)."
5075 PRINT ''"Press any key...": PAUSE 0: CLS 
5080 PRINT INK 6''"And that's not all! When you    start, up to 4 mines will be    shown in random positions.      These positions must be noted,  for if you land on one, you     will be destroyed!"
5085 PRINT INK 4''"Move with 5-8"
5090 PRINT INK 4; INVERSE 1''"    PRESS ANY KEY TO START.    ": PAUSE 0: CLS : RETURN 
9000 RESTORE 9010: FOR y=USR "a" TO USR "h"+7: READ x: POKE y,x: NEXT y
9010 DATA 28,93,73,62,8,28,34,65,28,28,8,127,8,28,20,20
9020 DATA 7,1,33,57,93,255,36,108,240,128,132,156,186,255,36,54
9030 DATA 8,28,62,28,28,63,61,7,15,57,255,124,254,84,56,16
9040 DATA 255,129,189,165,165,189,129,255,28,28,73,62,28,62,20,54
9050 RETURN 
9100 LET g=.3: RESTORE 9200: FOR f=1 TO 23: READ y,x: BEEP y,x: NEXT f: RETURN 
9200 DATA g,7,g,9,.6,7,g,7,g,9,.6,7,g,12,g,11,g,9,g,7,1.2,9,g,11,g,9,g,7,g,5,g,4,g,5,.6,7,g,2,g,5,g,4,g,2,1.2,0

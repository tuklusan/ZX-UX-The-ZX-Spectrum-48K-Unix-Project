   1 BORDER 7: PAPER 7: INK 0: CLS 
   2 REM @ Postman-Paul Stanley
   5 LET hs=0
   7 GO SUB 9000
  10 GO SUB 5500
  20 GO SUB 7000
  60 GO SUB 5000
  70 BEEP .1,0
  80 FOR i=1 TO 2
 100 IF INKEY$="5" THEN IF x>1 AND ATTR (y,x-1)<>58 AND ATTR (y+1,x-1)<>58 THEN LET a$="{94}{95}": LET b$(1)=" {96}": LET b$(2)=" {97}": LET x=x-1
 110 IF INKEY$="8" THEN IF x<29 AND ATTR (y,x+2)<>58 AND ATTR (y+1,x+2)<>58 THEN LET a$="{90}{91}": LET b$(1)="{92}": LET b$(2)="{93}": LET x=x+1
 120 IF INKEY$="7" THEN IF y>1 AND ATTR (y-1,x)<>58 AND ATTR (y-1,x+1)<>58 THEN LET a$="{98} ": LET b$(1)="{99}": LET b$(2)="{9C}": LET y=y-1
 130 IF INKEY$="6" THEN IF y<17 AND ATTR (y+2,x)<>58 AND ATTR (y+2,x+1)<>58 THEN LET a$="{9A} ": LET b$(1)="{9B}": LET b$(2)=b$(1): LET y=y+1
 140 PRINT AT y1,x1;"  ";AT y1+1,x1;"  "; INK 1;AT y,x;a$;AT y+1,x;b$(i): LET y1=y: LET x1=x
 200 IF let THEN IF x=hx OR x=hx-1 THEN IF y=hy THEN FOR f=1 TO 10: BEEP .01,f: NEXT f: LET sc=sc+o: PRINT AT 21,7;sc: GO SUB 5000
 250 IF NOT let THEN IF x=px OR x+1=px THEN IF y=py THEN LET let=1: BEEP .06,20: LET sc=sc+10: PRINT AT 21,7;sc: LET o=FN a()
 300 NEXT i
 500 LET dy=dy+(dy<y+1)-(dy>y+1)
 510 IF dx<x THEN LET dx=dx+1: LET d$="{9D}"
 530 IF dx>x THEN LET dx=dx-1: LET d$="{9E}"
 580 IF ATTR (dy,dx)=58 OR ATTR (dy,dx)=158 OR ATTR (dy,dx)=59 THEN LET u=dx: LET dx=dx+(dx<x)-(dx>x): IF dx=u THEN LET dx=dx+1
 800 PRINT INK 3;AT hy,hx;"{A2}"; INK 0;AT dy1,dx1;" ";AT dy,dx;d$
 810 LET dy1=dy: LET dx1=dx: LET t=t-1: PRINT AT 21,27;t;" ": IF t=0 THEN GO TO 8000
 850 IF dx=x OR dx=x+1 THEN IF dy=y OR dy=y+1 THEN GO SUB 6000
 999 GO TO 80
5000 PRINT INK 2;AT py,px;"{9F}";AT py+1,px;"{A0}"
5003 LET f=INT (RND*lb)+1
5005 LET let=0
5010 PRINT INK 6; PAPER 3; FLASH 1;AT y(f),x(f);"{9F}";AT y(f)+1,x(f);"{A0}"
5020 LET py=y(f): LET px=x(f)
5030 LET hx=INT (RND*14)*2+1: LET hy=INT (RND*9)*2+1
5040 IF ATTR (hy,hx)=58 OR ATTR (hy,hx)=158 THEN GO TO 5030
5050 PRINT INK 3;AT hy,hx;"{A2}"
5100 RETURN 
5500 INPUT "How many post boxes would you   like there to be? (Any number   between 1 and 36)  ";lb
5790 IF lb<1 OR lb>36 THEN GO TO 5780
5800 RETURN 
6000 FOR f=1 TO 12: BEEP .07,f: PRINT AT y,x; INK 1;"{90}{91}";AT y+1,x;"{92}"
6010 BEEP .05,f: PRINT INK 1;AT y,x;"{98} ";AT y+1,x;"{99}"
6020 BEEP .07,f: PRINT INK 1;AT y,x;"{94}{95}";AT y+1,x;" {96}"
6030 BEEP .05,f: PRINT INK 1;AT y,x;"{9A} ";AT y+1,x;"{9B} "
6040 NEXT f
6050 PRINT AT y,x;"  ";AT y+1,x;"  ";AT hy,hx;" "
6060 LET t=t-50: IF t<=0 THEN GO TO 8000
6070 PRINT AT 21,27;t;"  "
6080 LET y=17: LET x=28: LET y1=y: LET x1=x
6090 LET dy=1: LET dx=1: LET dy1=dy: LET dx1=dx
6100 GO TO 60
7000 FOR f=0 TO 19: PRINT INK 4;AT f,0;"{A1}";AT f,31;"{A1}": NEXT f
7010 FOR f=1 TO 30: PRINT INK 4;AT 0,f;"{A1}";AT 19,f;"{A1}": NEXT f
7060 DIM y(lb): DIM x(lb)
7100 FOR f=1 TO lb
7110 LET y=INT (RND*4)*4+3: LET x=INT (RND*9)*3+3
7120 IF ATTR (y,x)=58 OR ATTR (y+1,x)=58 THEN GO TO 7110
7125 LET y(f)=y: LET x(f)=x
7130 PRINT INK 2;AT y,x;"{9F}";AT y+1,x;"{A0}": NEXT f
7800 LET y=17: LET x=28: LET y1=y: LET x1=x
7810 DIM b$(2,2): LET a$="{94}{95}": LET b$(1)=" {96}": LET b$(2)=" {97}"
7840 LET sc=0: LET t=300: PRINT AT 21,1;"SCORE:";sc;AT 21,22;"TIME:";t
7850 LET let=0: LET py=y(lb): LET px=x(lb)
7900 LET dy=1: LET dx=1: LET d$="{9D}"
7910 LET dy1=dy: LET dx1=dx
7950 DEF FN a()=INT (SQR (ABS (hy-py)^2+ABS (hx-px)^2))
7999 RETURN 
8000 FOR f=1 TO 40: BEEP .01,f: NEXT f
8005 CLS : PRINT INK 4''"You have run out of time."
8010 PRINT INK 3''"You scored ";sc;" points."
8020 IF sc>hs THEN LET hs=sc: PRINT INK 2''"Well done that's a new high     score!!  Please ENTER your      name.": INPUT h$: GO TO 8035
8030 PRINT INK 2''"The high-score is ";hs;" points"'"by Postman ";h$
8035 FOR f=1 TO 50: NEXT f
8040 PRINT INK 5''"Press any key to play again..."
8050 IF INKEY$="" THEN GO TO 8050
8060 CLS : GO TO 10
9000 RESTORE 9010: FOR f=USR "a" TO USR "s"+7: READ g: POKE f,g: NEXT f
9010 DATA 120,126,236,231,255,255,124,56,0,0,0,254,255,254,0,0
9020 DATA 56,127,184,184,40,72,136,76,56,254,185,56,40,37,34,48
9030 DATA 0,0,0,127,255,127,0,0,30,126,55,231,255,255,62,28
9040 DATA 28,127,157,28,20,164,68,12,28,254,29,29,20,18,17,50
9050 DATA 16,56,56,56,56,56,56,56,124,254,124,56,126,184,40,32
9060 DATA 28,62,91,73,62,62,93,157,28,28,28,28,8,0,0,0
9070 DATA 124,254,124,56,252,58,40,8,8,14,139,142,252,124,68,68
9080 DATA 32,112,209,113,63,62,34,34,60,126,255,126,66,126,126,126,102,102,102,126,126,126,126,255
9090 DATA 126,195,189,165,165,189,195,126,32,126,255,126,86,86,126,126
9200 PRINT INK 2;"   {90}{91}    P O S T M A N    {94}{95}"'"   {92}                       {97}"
9250 PRINT '"        @ Paul Stanley"
9300 PRINT INK 1''"First collect a letter from the flashing post-box. Then deliver it to the little purple house."
9400 PRINT ''"You have limited time, and if   you are attacked by the dog,    you will lose time."
9500 PRINT INK 3''"Move with 5-8."
9600 PRINT ''"Press any key to start....."
9700 IF INKEY$="" THEN BEEP .01,20: PAUSE 10: GO TO 9700
9999 CLS : RETURN 

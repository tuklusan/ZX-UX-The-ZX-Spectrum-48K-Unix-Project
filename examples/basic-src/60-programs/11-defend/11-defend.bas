   1 REM Defend
   2 REM @ PAUL STANLEY  1982
   3 RANDOMIZE : BORDER 0: INK 7: PAPER 0: CLS 
   4 LET hl=10
   5 LET li=2
   6 LET hs=0
   7 GO SUB 3000
  10 RESTORE : GO SUB 2000: GO SUB 1000
  15 GO SUB 1170: BEEP .1,0
  19 PRINT AT 21,8;"FUEL:";c$( TO 10-hl);AT 0,14;"HI:";hs: PRINT OVER 1;AT y,15;b$: PLOT 104,0: DRAW 80,0: DRAW 0,7: DRAW -80,0: DRAW 0,-7: IF li=2 THEN PRINT AT 21,1; INK 3;"{92}{93}"
  20 PRINT OVER 1; INK 5;AT b,a;"{91}";AT b+1,a;a$
  21 PRINT AT 0,0;"Captures:";cap;AT 0,22;"Score:";sc;" "
  22 IF RND<.08 AND b<=lt THEN GO SUB 500
  27 PRINT OVER 1;AT b,a;"{91}";AT b+1,a;a$
  30 IF ATTR (b+2,a)=4 AND a$=" " THEN LET a$="{90}": LET c=c+1: LET m=1: PRINT AT b+2,a;" "
  37 IF m=1 THEN LET b=b-INT (RND*3): GO TO 45
  40 IF SCREEN$ (b+2,a)=" " THEN LET b=b+(INT (RND*2))
  42 IF SCREEN$ (b-1,a)<>" " THEN LET m=1: LET c=c+1
  45 IF b<1 THEN LET b=1
  47 IF c=8 OR b>17 THEN CLS : GO SUB 1000: GO TO 19
  50 LET a=a-1
  55 IF a=-1 THEN LET a=31: LET m=0: IF a$="{90}" THEN LET cap=cap+1: BEEP .1,0: BEEP .1,12: BEEP .1,0: BEEP .1,12: LET a$=" "
  56 PRINT OVER 1;AT y,15;b$
  57 LET y=y+(IN 63486=254 AND y<=lt)-(IN 63486=253 AND y>1)
  58 IF IN 61438=253 THEN IF b$="{92}{93}" THEN LET b$="{94}{95}": GO TO 60
  59 IF IN 61438=253 THEN LET b$="{92}{93}"
  60 PRINT OVER 1;AT y,15; INK 6;b$
  61 IF cap=3 OR hl=10 THEN PRINT AT 0,9;cap: GO TO 800
  66 IF IN 61438=254 THEN GO SUB 100
  70 GO TO 20
 100 LET i=119*(b$="{94}{95}")+136*(b$="{92}{93}"): LET j=(21-y)*8+3
 106 PLOT i,j
 110 IF b$="{92}{93}" THEN BEEP .05,20: DRAW 90,0: BEEP .04,0: BEEP .03,-5: PLOT OVER 1;i,j: DRAW OVER 1;90,0
 120 IF b$="{94}{95}" THEN BEEP .05,20: DRAW -90,0: BEEP .04,0: BEEP .03,-5: PLOT OVER 1;i,j: DRAW OVER 1;-90,0
 121 IF y=b AND ((b$="{92}{93}" AND a>16 AND a<29) OR (b$="{94}{95}" AND a<15 AND a>2)) THEN GO TO 200+(100 AND a$="{90}")
 130 RETURN 
 200 LET m=0: INK 6: PRINT AT b,a;"{96}": BEEP .03,-10: PRINT AT b,a; INVERSE 1;"{96}": BEEP .03,-16: PRINT AT b,a;"{96}": BEEP .03,-10: PRINT AT b,a; INVERSE 1;"{96}": BEEP .05,-20: PRINT AT b,a; INVERSE 1;"{96}": BEEP .05,-20: PRINT AT b,a;"{96}": BEEP .03,-3: PRINT AT b,a;" ": INK 7: LET b=1+INT (RND*14): LET a=31
 206 LET sc=sc+10
 215 LET a$=" "
 220 RETURN 
 300 BEEP .02,-5: PRINT AT b,a;"{96}": BEEP .04,-9: PRINT INVERSE 1;AT b,a;"{96}": BEEP .04,-3: PRINT AT b,a;"{96}": BEEP .04,-10: PRINT AT b,a;" "
 305 LET f=0: FOR d=b+1 TO 19
 310 PRINT AT d,a;"{90}": BEEP .02,d*2
 320 LET f=f+1
 325 PRINT AT d,a;" "
 330 IF SCREEN$ (d+1,a)<>" " THEN GO TO 360
 350 NEXT d
 355 GO TO 300
 360 LET o=RND: IF o>.35 AND f>9 THEN LET sc=sc-(50 AND sc>=50)-(sc AND sc<50): FOR f=-30 TO 0: PRINT AT d+1,a; INK RND*4+3;"{96}": BEEP .03,f: NEXT f: PRINT AT d+1,a;" ": GO TO 372
 370 PRINT AT d+1,a; INK 4;"{90}"
 372 IF o<=.35 THEN GO TO 400
 375 LET m=0
 380 LET a$=" ": LET a=31: LET b=INT (RND*14)+1: RETURN 
 400 FOR f=1 TO 4
 410 PRINT INK 4;AT d+1,a;"{90}": BEEP .1,2: PRINT INK 4;AT d+1,a;" ";AT d,a;"{90}": BEEP .1,4: PRINT AT d,a;" ": NEXT f
 420 PRINT AT d+1,a; INK 4;"{90}"
 430 PRINT OVER 1;AT d-1,a-2;"I'M OK!";AT d,a;"|": FOR f=0 TO 100: NEXT f: PRINT AT d-1,a-2; OVER 1;"I'M OK!";AT d,a;"|": GO TO 375
 500 IF a>15 THEN LET dir=-80: LET stx=a*8-1
 510 IF a<=15 THEN LET dir=80: LET stx=a*8+8
 520 PLOT OVER 1;stx,(21-b)*8+3: BEEP .01,20: DRAW OVER 1;dir,0
 525 PLOT OVER 1;stx,(21-b)*8+3: BEEP .01,20: DRAW OVER 1;dir,0
 530 IF b=y THEN IF (a<27 AND dir=-80) OR (a>4 AND dir=80) THEN GO TO 560
 540 RETURN 
 560 PRINT AT y,15; OVER 1;b$: LET a=15
 565 PLOT OVER 1;120,(21-y)*8+3: DRAW OVER 1;7,0
 570 FOR v=1 TO 6
 580 PRINT INK 6;AT y+v/2,a+v;"{92}";AT y-v/2,a+v;"{93}";AT y+v/2,a-v;"{94}";AT y-v/2,a-v;"{95}"
 590 BEEP .01,30-v
 600 PRINT AT y+v/2,a+v;" ";AT y-v/2,a-v;" ";AT y+v/2,a-v;" ";AT y-v/2,a+v;" "
 610 NEXT v
 620 LET li=li-1
 630 IF li<>0 THEN CLS : GO SUB 1000: GO TO 19
 800 FOR f=1 TO 2: RESTORE 8000: FOR a=1 TO 8: READ b,y: BEEP b,y: NEXT a: NEXT f
 810 PRINT AT 10,7; FLASH 1;"G A M E  O V E R": PRINT : PRINT : PRINT : PRINT "   Press any key to try again"
 815 IF sc>hs THEN LET hs=sc
 820 IF INKEY$<>"" THEN CLS : GO TO 10
 825 GO TO 820
1000 LET hl=hl+1: LET y=50: LET x=0
1010 PLOT x,y
1020 LET a=RND*20: LET b=RND*20-RND*20
1030 LET x=x+a: LET y=y+b
1040 IF x>251 THEN GO TO 1080
1050 IF y<10 OR y>60 THEN LET x=x-1: LET y=y-b: GO TO 1020
1060 DRAW a,b
1070 GO TO 1020
1080 FOR x=0 TO 24 STEP 3
1090 LET a=INT (RND*6)+x
1095 LET f=20
1100 FOR b=4 TO 21
1110 IF SCREEN$ (b,a)<>" " THEN PRINT AT b,a; INK 4;"{90}": LET b=b+2
1120 NEXT b: NEXT x
1121 FOR f=11 TO 17: FOR y=0 TO 31: IF SCREEN$ (f,y)<>" " THEN LET lt=f-1: GO TO 1130
1122 NEXT y: NEXT f
1130 LET y=5: LET c=0
1135 LET b$="{92}{93}"
1140 LET a=31: LET b=1
1150 LET a$=" ": LET c$="{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}"
1160 LET m=0
1164 PRINT AT 21,1;"  "
1165 IF li=2 THEN PRINT AT 21,1; INK 3;"{92}{93}"
1168 RETURN 
1170 LET sc=0: LET cap=0: LET c=0
1182 LET hl=0: LET li=2
1200 RETURN 
2000 FOR a=USR "a" TO USR "g"+7: READ b: POKE a,b: NEXT a
2010 RETURN 
2020 DATA 28,28,8,62,8,8,20,34
2030 DATA 0,24,60,66,255,126,66,{C4}01100110
2040 DATA 0,0,199,{C4}11001100,255,255,3,0
2050 DATA 0,0,240,24,255,252,224,0
2060 DATA 0,0,15,24,255,63,7,0
2070 DATA 0,0,{C4}11100011,{C4}00110011,255,255,192,0
2080 DATA 196,9,{C4}1011000,6,208,74,145,{C4}01100100
3000 FOR a=1 TO 30: PRINT AT RND*21,RND*26; INK RND*3+4;"DEFEND": BEEP .01,RND*10: NEXT a
3010 PAUSE 100: CLS 
3020 PRINT "A fleet of aliens have managed  to get past defensive lines on  Earth. One by one they fly in   with the sole intent of picking up Humanoids which have climbed to the top of the hills to see  what is happening."
3030 PRINT : PRINT "Your job is to prevent the fleetfrom capturing the Humanoids.   You have a powerful laser with  which to shoot down the aliens."
3040 PRINT : PRINT "CONTROLS ARE:                   1........................Down   2..........................Up   9............Change direction   0........................Fire"
3041 PRINT : PRINT : PRINT INVERSE 1;"Press any key to continue": PAUSE 0
3045 CLS 
3050 PRINT : PRINT "You have been defeated when 3   Humanoids have been captured.": PRINT : PRINT "It is alright to shoot at alienswhich are clutching a Humanoid  as long as he does not fall too far (if he does you forfeit 50  points)."
3060 PRINT "Note that only green Humanoids  are attractive to the aliens.": PRINT : PRINT "Don't underestimate your enemy  invader, he may have a trick up his sleeve.....": PRINT : PRINT "Every so often the computer willtake you to a new location at   the expense of some of your fuelwhich if zero will end the game.": PRINT : PRINT INVERSE 1;"Press any key to continue.": PAUSE 0
3065 CLS 
3070 RETURN 
8000 DATA .1,11,.1,11,.8,16,.05,11,.05,16,.05,11,.05,16,1,20

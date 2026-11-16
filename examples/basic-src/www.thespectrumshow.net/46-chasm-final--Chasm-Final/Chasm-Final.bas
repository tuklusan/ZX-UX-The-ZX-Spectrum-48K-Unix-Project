   1 REM **********************
   2 REM *       CHASM        *
   3 REM *                    *
   4 REM * {7F} R. Grimwood 1983 *
   5 LET l=3: LET sc=0: LET w=21
   6 GO SUB 8000
   7 BORDER 0: PAPER 0: INK 7
   8 CLS : PRINT FLASH 1;"            THE CHASM           "
   9 PRINT AT 2,7;"{7F} R. Grimwood 1983"
  10 PRINT '"      Welcome to the chasm"
  11 PRINT '"You have just completed the     elimination of all the aliens   from your kingdom, however you  have just learnt of the exist-  ance of a couple more, seeking  refuge in the chasm only a few  miles from the city."
  15 PRINT '"Your task is to eliminate these few remaining aliens & you must pilot your ship down the chasm  whilst destroying them."
  20 PRINT '"The chasm narrows as your       mission continues & the aliens  become more profuse."
  22 PRINT #1;"Pres 'M' for more "
  23 IF INKEY$<>"m" THEN GO TO 23
  25 CLS : PRINT '"You must avoid the sides of the chasm, if you hit them however  you will loose one of your 3    lives. After a crash you must   start steerig away from the     sides immediatey or you will    hit them again. You will also   loose a life if you hit an alien"
  27 PRINT '"You will be informed of your    score when you die & when you   change stages."
  28 PRINT '"S-X Up-Down             -A-     O-P Left-Right        to Fire"
  30 PRINT '''"          GOOD LUCK"
  33 PRINT #1;"Pres 'p' to start"
  35 IF INKEY$<>"p" THEN GO TO 35
  37 CLS 
  40 REM GO SUB 8000
  45 BORDER 0: PAPER 2: INK 0: CLS 
  50 LET z=7: LET a=8: LET s=1: LET d=11
  60 PAPER 0
  65 FOR g=0 TO 20: PRINT INK 0;"                                ": NEXT g
  70 LET a$="       "
  75 LET b$="      "
  80 LET c$="     "
  85 LET d$="    "
  90 LET e$="   "
  95 FOR f=1 TO 20: PLOT INK 7;INT (RND*255),INT (RND*150): NEXT f
 100 FOR r=1 TO 9999999999: POKE 23692,255
 105 LET x=INT (RND*3)-1
 110 PAPER 0
 111 PRINT OVER 0; INK 6; PAPER 0;AT s,d;"{9D}"
 112 PRINT OVER 0; INK 5; PAPER 0;AT s,d;" "
 115 IF r<=200 THEN PRINT AT w,a; INK 2;a$
 120 IF r>200 AND r<=400 THEN PRINT AT w,a; INK 2;b$
 125 IF r=200 THEN GO SUB 1600: BEEP 1,0: LET z=z-1: FOR f=1 TO 10: BEEP .1,5: NEXT f
 130 IF r>400 AND r<=600 THEN PRINT AT w,a; INK 2;c$
 135 IF r=400 THEN GO SUB 1600: BEEP 1,0: LET z=z-1: FOR f=1 TO 10: BEEP .1,5: NEXT f
 140 IF r>600 AND r<=800 THEN PRINT AT w,a; INK 2;d$
 150 IF r=600 THEN GO SUB 1600: BEEP 1,0: LET z=z-1: FOR f=1 TO 10: BEEP .1,5: NEXT f
 160 IF r>800 AND r<=1500 THEN PRINT AT w,a; INK 2;e$
 170 IF r=88 THEN GO SUB 1600: BEEP 1,0: LET z=z-1: FOR f=1 TO 10: BEEP .1,5: NEXT f
 200 IF r>1500 THEN FOR f=-35 TO 45: BEEP .05,f: NEXT f: FOR f=45 TO -35 STEP -1: BEEP .05,f: NEXT f: GO TO 1700
 260 PAPER 2
 265 PRINT 
 270 LET a=a+x
 280 IF a<1 THEN LET a=1
 285 IF a>25 THEN LET a=25
 290 LET d=d+(INKEY$="p")-(INKEY$="o")
 295 LET s=s+(INKEY$="x")-(INKEY$="s")
 300 IF s>21 THEN LET s=21
 310 IF s<0 THEN LET s=0
 320 PRINT OVER 0; INK 6; PAPER 0;AT s,d;"{9D}"
 330 PRINT OVER 0; INK 5; PAPER 0;AT s,d;" "
 340 IF ATTR (s+1,d)=16 THEN GO TO 7200
 350 IF ATTR (s+1,d)=4 THEN GO SUB 1300
 360 LET q=INT (RND*4): IF q=2 THEN GO SUB 1200
 990 IF INKEY$="a" THEN GO SUB 1500
1000 NEXT r: GO TO 100
1200 PRINT AT w-1,INT (RND*z)+a; INK 4; PAPER 0;"@": BEEP .003,40
1220 RETURN 
1300 PRINT AT s+1,d; FLASH 1; PAPER 0; INK 2; BRIGHT 1;"{A3}"
1305 LET l=l-1
1310 PRINT AT 0,5; PAPER 7; INK 0;"SCORE=";sc;AT 0,20;"LIVES=";l
1320 FOR f=1 TO 10: FOR j=1 TO 2: BEEP .002,15: BEEP .03,10: NEXT j: FOR j=1 TO 2: BEEP .03,5: BEEP .004,0: NEXT j: NEXT f
1330 IF l<0 THEN GO TO 7500
1340 PRINT AT s+1,d; FLASH 0; PAPER 0; BRIGHT 0;" ": RETURN 
1500 LET m=s: LET n=d
1501 FOR f=55 TO 0 STEP -7: BEEP .001,f: NEXT f
1502 PRINT AT m+1,n; INK 6; PAPER 0;"|"
1503 LET m=m+1
1505 PRINT AT m,n; PAPER 0;" "
1506 REM PRINT AT 15,29;ATTR (m+1,n)
1510 IF m>20 THEN LET m=20: RETURN 
1515 IF ATTR (m+1,n)=16 THEN RETURN 
1520 IF ATTR (m+1,n)=4 THEN LET sc=sc+100: PRINT AT m+1,n; INK 3; PAPER 0;"{A3}": BEEP .1,0: PRINT AT m+1,n; PAPER 0;" ": RETURN 
1525 GO TO 1502
1530 RETURN 
1600 PRINT AT 0,5; PAPER 7; INK 0;"SCORE=";sc;AT 0,20;"LIVES=";l
1601 RETURN 
1700 CLS : FOR g=0 TO 5: POKE 23692,255: FOR f=0 TO 7: PRINT INK f;"{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}": NEXT f: NEXT g
1710 CLS : PRINT '''' PAPER 7;"          CONGRATULATIONS       "
1726 PRINT ''"You have successfuly completed"''"            THE CHASM"
1730 PAUSE 100: GO TO 7500
7200 LET l=l-1
7220 PRINT AT 0,5; PAPER 7; INK 0;"SCORE=";sc;AT 0,20;"LIVES=";l
7230 FOR f=45 TO 35 STEP -1: BEEP .01,f: NEXT f: FOR f=25 TO 35: BEEP .01,f: NEXT f: FOR f=35 TO 15 STEP -1: BEEP .01,f: NEXT f: FOR f=f TO 15: BEEP .01,f: NEXT f
7240 FOR f=5 TO -1 STEP -1: BEEP .01,f: NEXT f: FOR f=-15 TO -5: BEEP .01,f: NEXT f
7250 FOR f=1 TO 5: FOR g=-40 TO -45 STEP -1: BEEP .01,f: NEXT g: NEXT f
7260 IF l<1 THEN GO TO 7500
7300 GO TO 235
7500 PAUSE 40: CLS : PAPER 0: BORDER 0: INK 7: FOR g=50 TO -10 STEP -1: BEEP .0075,g: NEXT g: FOR h=1 TO 20: BEEP .004,10: NEXT h
7510 PRINT INVERSE 1;AT 10,8;"SCORE=";sc
7550 PRINT #1;"Another try? (y/n)"
7560 IF INKEY$="y" THEN CLS : GO TO 40
7570 IF INKEY$="n" THEN STOP 
7575 GO TO 7560
7580 CLS 
8000 POKE USR "n"+0,BIN 10000001
8001 POKE USR "n"+1,BIN 01000010
8002 POKE USR "n"+2,BIN 01100110
8003 POKE USR "n"+3,BIN 01111110
8004 POKE USR "n"+4,BIN 01111110
8005 POKE USR "n"+5,BIN 00100100
8006 POKE USR "n"+6,BIN 00111100
8007 POKE USR "n"+7,BIN 00011000
8010 POKE USR "t"+0,BIN 10010010
8011 POKE USR "t"+1,BIN 01010100
8012 POKE USR "t"+2,BIN 00000000
8013 POKE USR "t"+3,BIN 11010110
8014 POKE USR "t"+4,BIN 00000000
8015 POKE USR "t"+5,BIN 01010100
8016 POKE USR "t"+6,BIN 10010010
8017 POKE USR "t"+7,BIN 00000000
8018 RETURN 

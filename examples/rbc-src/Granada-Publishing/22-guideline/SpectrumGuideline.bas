  10 REM Spectrum guideline
  20 GO SUB 1000
  30 GO SUB 2000
  40 PAUSE 100
  50 PRINT AT 1,0; BRIGHT 1;"GO"
  60 BEEP .1,5
  70 LET y=100: LET x=10
  80 LET b=y: LET r=12-df
  90 LET r2=r/2: LET v=2
 100 GO SUB 5000
 105 OVER 0
 110 PRINT AT 1,0;"You were on target ";AT 2,10;INT (hit/(hit+miss)*10000)/100;"% of the time"
 120 INPUT "Another game ";a$
 130 IF a$="y" THEN RUN 
 140 IF a$<>"n" THEN GO TO 120
 150 BORDER 7
 160 CLS 
 170 STOP 
1000 LET x=10
1010 LET y=100
1020 LET d=30
1030 LET p=0
1040 INK 0
1050 PAPER 7
1060 BORDER 4
1070 CLS 
1080 PRINT AT 2,7;"G U I D E L I N E"
1090 PRINT AT 5,0;"You must guide a ring along the"
1100 PRINT "wavy 'wire' using the up and"
1110 PRINT "down arrow keys"
1120 PRINT 
1130 PRINT "You will be marked on how"
1140 PRINT "accurate you are"
1150 INPUT "Select the difficulty level"'" - 1 (easy) to 5 (difficult) ?";df
1160 IF df<1 OR df>5 THEN GO TO 1150
1170 CLS 
1180 OVER 1
1190 RETURN 
2000 PLOT x,y
2010 FOR i=1 TO 10
2020 LET r=d-INT (RND*2*d)
2030 LET y=y+r
2040 IF y>160 THEN LET y=y-r: LET r=-r
2050 IF y<10 THEN LET y=y+r: LET r=-r
2060 DRAW 20,r
2070 NEXT i
2080 LET hit=0
2090 LET miss=0
2100 RETURN 
5000 PLOT x-r2,y-r2
5010 DRAW 0,r
5020 DRAW r,0
5030 DRAW 0,-r
5040 DRAW -r,0
5100 LET a$=INKEY$
5110 IF a$="6" AND y-r2>2*v THEN LET b=b-2*v
5120 IF a$="7" AND y+r<175-2*v THEN LET b=b+2*v
5510 PLOT x-r2,y-r2
5520 DRAW 0,r
5530 DRAW r,0
5540 DRAW 0,-r
5550 DRAW -r,0
5560 LET x=x+v
5565 IF x>210 THEN RETURN 
5570 LET y=b
5580 FOR i=-r2+1 TO r2-1
5590 IF POINT (x,y+i) THEN LET hit=hit+1: PAUSE 2: GO TO 5000
5600 NEXT i
5610 LET miss=miss+1
5700 BEEP .01,3
5710 GO TO 5000

  10 LET aa=1
  20 FOR i=1 TO 100
  30 LET bb=aa+1: LET cc=bb-aa
  40 IF cc<>1 THEN GO TO 70
  50 LET aa=aa*2
  60 NEXT i
  70 LET bb=1
  80 FOR i=1 TO 100
  90 LET cc=aa+bb: LET dd=cc-aa
 100 IF dd<>0 THEN GO TO 130
 110 LET bb=bb*2
 120 NEXT i
 130 LET ibeta=INT (dd+.25)
 140 IF ibeta<2 THEN LET ibeta=2
 150 LET eps=1: LET ndig=0
 160 FOR i=1 TO 100
 170 LET xx=eps/ibeta: LET yy=1+xx
 180 IF yy=1 THEN GO TO 210
 190 LET eps=xx: LET ndig=ndig+1
 200 NEXT i
 210 LET eneg=1
 220 FOR i=1 TO 100
 230 LET xx=eneg/ibeta: LET yy=1-xx
 240 IF yy=1 THEN GO TO 270
 250 LET eneg=xx
 260 NEXT i
 270 PRINT "MACHAR ";ibeta;" ";ndig+1;" ";eps;" ";eneg
 290 PRINT "DONE MACHAR"
 300 STOP 

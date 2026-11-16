  10 DIM a(2): LET a(1)=1.5: LET a(2)=3.5
  20 FOR v=1 TO 2
  30 LET xx=a(v)
  40 FOR i=1 TO 20
  50 LET yy=xx*xx*xx-2*xx-5
  60 LET dd=3*xx*xx-2
  70 IF ABS dd<.001 THEN GO TO 110
  80 LET xx=xx-yy/dd
  90 IF ABS yy<.00001 THEN GO TO 110
 100 NEXT i
 110 PRINT "NEWTON ";v;" ";i;" ";xx;" ";xx*xx*xx-2*xx-5
 130 NEXT v
 140 PRINT "DONE NEWTON"
 150 STOP 

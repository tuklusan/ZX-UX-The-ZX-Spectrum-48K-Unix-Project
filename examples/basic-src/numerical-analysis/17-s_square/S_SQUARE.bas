  10 FOR v=1 TO 2
  20 LET n=100*v: LET start=1-.00002*v: LET ss=0
  30 FOR i=1 TO n
  40 LET xx=start
  50 FOR j=1 TO 16
  60 LET xx=xx*xx
  70 NEXT j
  80 LET ss=ss+xx
  90 NEXT i
 100 PRINT "SQUARE ";v;" ";n;" ";ss;" ";xx
 120 NEXT v
 130 PRINT "DONE S_SQUARE"
 140 STOP 

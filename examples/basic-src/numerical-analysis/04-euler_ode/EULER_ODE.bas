  10 FOR v=1 TO 2
  20 LET n=10*v: LET h=1/n: LET xx=0: LET yy=1
  30 FOR i=1 TO n
  40 LET yy=yy-h*yy: LET xx=xx+h
  50 IF i=n THEN PRINT "EULER STEP ";v;" ";i;" ";xx;" ";yy
  60 NEXT i
  70 LET err=ABS (yy-.36787944)
  80 PRINT "EULER ";v;" ";n;" ";yy;" ";err
 100 NEXT v
 110 PRINT "DONE EULER_ODE"
 120 STOP 

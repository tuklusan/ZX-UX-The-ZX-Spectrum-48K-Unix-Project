  10 FOR v=1 TO 2
  20 LET n=10*v: LET h=1/n: LET xx=0: LET yy=1
  30 IF v=2 THEN LET yy=.25
  40 FOR i=1 TO n
  50 LET zz=yy: GO SUB 190: LET k1=fx
  60 LET zz=yy+h*k1/2: GO SUB 190: LET k2=fx
  70 LET zz=yy+h*k2/2: GO SUB 190: LET k3=fx
  80 LET zz=yy+h*k3: GO SUB 190: LET k4=fx
  90 LET yy=yy+h*(k1+2*k2+2*k3+k4)/6
 100 LET xx=xx+h
 110 NEXT i
 120 LET exact=EXP (-2)
 130 IF v=2 THEN LET exact=1/(1+3*EXP (-1))
 140 PRINT "RK4 ";v;" ";n;" ";yy;" ";ABS (yy-exact)
 160 NEXT v
 170 PRINT "DONE RK4_FIXED"
 180 STOP 
 190 LET fx=-2*zz
 200 IF v=2 THEN LET fx=zz*(1-zz)
 210 RETURN 

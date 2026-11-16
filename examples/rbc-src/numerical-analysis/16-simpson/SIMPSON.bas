  10 FOR v=1 TO 2
  20 LET n=80*v: LET h=1/n: LET ss=0
  30 FOR i=1 TO n-1
  40 LET xx=i*h: LET yy=xx*xx
  50 IF v=2 THEN LET yy=4/(1+xx*xx)
  60 IF i-2*INT (i/2)=0 THEN LET ss=ss+2*yy
  70 IF i-2*INT (i/2)<>0 THEN LET ss=ss+4*yy
  80 NEXT i
  90 LET res=(ss+1)*h/3: LET exact=1/3
 100 IF v=2 THEN LET res=(ss+6)*h/3: LET exact=3.14159265
 110 PRINT "SIMPSON ";v;" ";n;" ";res;" ";ABS (res-exact)
 130 NEXT v
 140 PRINT "DONE SIMPSON"
 150 STOP 

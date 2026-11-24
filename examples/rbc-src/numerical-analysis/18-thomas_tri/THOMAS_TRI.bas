  10 DIM a(20): DIM b(20): DIM c(20): DIM d(20): DIM e(20)
  20 FOR v=1 TO 2
  30 LET n=10*v
  40 FOR i=1 TO n
  50 LET a(i)=-1: LET b(i)=4: LET c(i)=-1
  60 LET e(i)=1+.025*i: LET d(i)=4*e(i)
  70 IF i>1 THEN LET d(i)=d(i)-(1+.025*(i-1))
  80 IF i<n THEN LET d(i)=d(i)-(1+.025*(i+1))
  90 NEXT i
 100 FOR i=2 TO n
 110 LET tt=a(i)/b(i-1)
 120 LET b(i)=b(i)-tt*c(i-1)
 130 LET d(i)=d(i)-tt*d(i-1)
 140 NEXT i
 150 LET d(n)=d(n)/b(n)
 160 FOR i=n-1 TO 1 STEP -1
 170 LET d(i)=(d(i)-c(i)*d(i+1))/b(i)
 180 NEXT i
 190 LET err=0
 200 FOR i=1 TO n
 210 IF ABS (d(i)-e(i))>err THEN LET err=ABS (d(i)-e(i))
 220 NEXT i
 230 PRINT "THOMAS ";v;" ";n;" ";err;" ";d(1);" ";d(n)
 250 NEXT v
 260 PRINT "DONE THOMAS_TRI"
 270 STOP 

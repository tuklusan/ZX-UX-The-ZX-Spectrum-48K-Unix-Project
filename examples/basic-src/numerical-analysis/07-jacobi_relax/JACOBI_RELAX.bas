  10 DIM a(16,16): DIM b(16,16)
  20 FOR v=1 TO 2
  30 LET n=8*v: LET iter=20*v
  40 FOR j=1 TO n
  50 FOR i=1 TO n
  60 LET a(i,j)=0: LET b(i,j)=0
  70 IF j=n THEN LET a(i,j)=1: LET b(i,j)=1
  80 NEXT i
  90 NEXT j
 100 FOR k=1 TO iter
 110 LET err=0
 120 FOR j=2 TO n-1
 130 FOR i=2 TO n-1
 140 LET vv=(a(i-1,j)+a(i+1,j)+a(i,j-1)+a(i,j+1))/4
 150 LET dd=ABS (vv-a(i,j))
 160 IF dd>err THEN LET err=dd
 170 LET b(i,j)=vv
 180 NEXT i
 190 NEXT j
 200 FOR j=2 TO n-1
 210 FOR i=2 TO n-1
 220 LET a(i,j)=b(i,j)
 230 NEXT i
 240 NEXT j
 250 NEXT k
 260 PRINT "JACOBI ";v;" ";n;" ";iter;" ";a(n/2,n/2);" ";err
 280 NEXT v
 290 PRINT "DONE JACOBI_REL"
 300 STOP 

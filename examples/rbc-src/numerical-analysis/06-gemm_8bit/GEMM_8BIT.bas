  10 DIM a(15,15): DIM b(15,15): DIM c(15,15)
  20 FOR v=1 TO 2
  30 LET n=7+4*v
  40 FOR j=1 TO n
  50 FOR i=1 TO n
  60 LET a(i,j)=.02*(i-j)+.1
  70 LET b(i,j)=.01*(i+j)
  80 IF i=j THEN LET b(i,j)=1+.01*i
  90 LET c(i,j)=0
 100 NEXT i
 110 NEXT j
 120 FOR j=1 TO n
 130 FOR k=1 TO n
 140 LET dd=b(k,j)
 150 FOR i=1 TO n
 160 LET c(i,j)=c(i,j)+a(i,k)*dd
 170 NEXT i
 180 NEXT k
 190 NEXT j
 200 LET chk=0
 210 FOR i=1 TO n
 220 LET chk=chk+c(i,i)
 230 NEXT i
 240 PRINT "GEMM ";v;" ";n;" ";chk;" ";c(1,1);" ";c(n,n)
 260 NEXT v
 270 PRINT "DONE GEMM_8BIT"
 280 STOP 

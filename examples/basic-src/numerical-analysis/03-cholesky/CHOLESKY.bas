  10 DIM a(8,8): DIM b(8,8): DIM c(8,8)
  20 FOR v=1 TO 2
  30 LET n=3+2*v
  40 FOR j=1 TO n
  50 FOR i=1 TO n
  60 LET a(i,j)=0: LET c(i,j)=0
  70 IF i>=j THEN LET a(i,j)=.025*(i-j)
  80 IF i=j THEN LET a(i,j)=2+.1*i
  90 NEXT i
 100 NEXT j
 110 FOR j=1 TO n
 120 FOR i=1 TO n
 130 LET ss=0
 140 FOR k=1 TO n
 150 LET ss=ss+a(i,k)*a(j,k)
 160 NEXT k
 170 LET b(i,j)=ss
 180 NEXT i
 190 NEXT j
 200 FOR j=1 TO n
 210 FOR i=j TO n
 220 LET ss=b(i,j)
 230 IF j=1 THEN GO TO 270
 240 FOR k=1 TO j-1
 250 LET ss=ss-c(i,k)*c(j,k)
 260 NEXT k
 270 IF i=j THEN LET c(i,j)=SQR ss
 280 IF i<>j THEN LET c(i,j)=ss/c(j,j)
 290 NEXT i
 300 NEXT j
 310 LET err=0
 320 FOR j=1 TO n
 330 FOR i=j TO n
 340 IF ABS (c(i,j)-a(i,j))>err THEN LET err=ABS (c(i,j)-a(i,j))
 350 NEXT i
 360 NEXT j
 370 PRINT "CHOL ";v;" ";n;" ";err
 390 NEXT v
 400 PRINT "DONE CHOLESKY"
 410 STOP 

  10 DIM a(8,8): DIM b(8): DIM c(8)
  20 FOR v=1 TO 2
  30 LET n=4+2*v
  40 FOR j=1 TO n
  50 LET c(j)=.2*j
  60 FOR i=1 TO n
  70 LET a(i,j)=.05*(i+j)
  80 IF i=j THEN LET a(i,j)=4
  90 NEXT i
 100 NEXT j
 110 LET a(1,1)=0: LET a(2,1)=2
 120 FOR i=1 TO n
 130 LET b(i)=0
 140 FOR j=1 TO n
 150 LET b(i)=b(i)+a(i,j)*c(j)
 160 NEXT j
 170 NEXT i
 180 FOR k=1 TO n-1
 190 LET pp=k: LET big=ABS a(k,k)
 200 FOR i=k+1 TO n
 210 IF ABS a(i,k)>big THEN LET big=ABS a(i,k): LET pp=i
 220 NEXT i
 230 IF pp=k THEN GO TO 280
 240 FOR j=1 TO n
 250 LET tt=a(pp,j): LET a(pp,j)=a(k,j): LET a(k,j)=tt
 260 NEXT j
 270 LET tt=b(pp): LET b(pp)=b(k): LET b(k)=tt
 280 FOR i=k+1 TO n
 290 LET mult=a(i,k)/a(k,k)
 300 FOR j=k+1 TO n
 310 LET a(i,j)=a(i,j)-mult*a(k,j)
 320 NEXT j
 330 LET b(i)=b(i)-mult*b(k): LET a(i,k)=0
 340 NEXT i
 350 NEXT k
 360 FOR i=n TO 1 STEP -1
 370 LET tt=b(i)
 380 IF i=n THEN GO TO 420
 390 FOR j=i+1 TO n
 400 LET tt=tt-a(i,j)*b(j)
 410 NEXT j
 420 LET b(i)=tt/a(i,i)
 430 NEXT i
 440 LET err=0
 450 FOR i=1 TO n
 460 IF ABS (b(i)-c(i))>err THEN LET err=ABS (b(i)-c(i))
 470 NEXT i
 480 PRINT "PIVOT ";v;" ";n;" ";err
 500 NEXT v
 510 PRINT "DONE LU_PIVOT"
 520 STOP 

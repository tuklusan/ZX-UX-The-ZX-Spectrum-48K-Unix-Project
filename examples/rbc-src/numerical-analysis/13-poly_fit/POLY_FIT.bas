  10 DIM a(5,5): DIM b(5): DIM c(5): DIM d(9)
  20 FOR v=1 TO 2
  30 LET nc=2+v: LET n=7+2*v
  40 FOR i=1 TO nc
  50 LET b(i)=0: LET c(i)=0
  60 FOR j=1 TO nc
  70 LET a(i,j)=0
  80 NEXT j
  90 NEXT i
 100 LET c(1)=1: LET c(2)=.5: LET c(3)=-.25
 110 IF v=2 THEN LET c(1)=.25: LET c(2)=-.4: LET c(3)=.3: LET c(4)=-.1
 120 FOR k=1 TO n
 130 LET xx=(2*k-n-1)/(n-1)
 140 LET d(1)=1
 150 FOR i=2 TO 9
 160 LET d(i)=d(i-1)*xx
 170 NEXT i
 180 LET yy=0
 190 FOR i=1 TO nc
 200 LET yy=yy+c(i)*d(i)
 210 NEXT i
 220 FOR i=1 TO nc
 230 LET b(i)=b(i)+yy*d(i)
 240 FOR j=1 TO nc
 250 LET a(i,j)=a(i,j)+d(i+j-1)
 260 NEXT j
 270 NEXT i
 280 NEXT k
 290 FOR k=1 TO nc-1
 300 LET pp=k: LET tt=ABS a(k,k)
 310 FOR i=k+1 TO nc
 320 IF ABS a(i,k)>tt THEN LET tt=ABS a(i,k): LET pp=i
 330 NEXT i
 340 IF pp=k THEN GO TO 390
 350 FOR j=1 TO nc
 360 LET tt=a(k,j): LET a(k,j)=a(pp,j): LET a(pp,j)=tt
 370 NEXT j
 380 LET tt=b(k): LET b(k)=b(pp): LET b(pp)=tt
 390 FOR i=k+1 TO nc
 400 LET mult=a(i,k)/a(k,k)
 410 FOR j=k+1 TO nc
 420 LET a(i,j)=a(i,j)-mult*a(k,j)
 430 NEXT j
 440 LET b(i)=b(i)-mult*b(k)
 450 NEXT i
 460 NEXT k
 470 FOR i=nc TO 1 STEP -1
 480 LET tt=b(i)
 490 IF i=nc THEN GO TO 530
 500 FOR j=i+1 TO nc
 510 LET tt=tt-a(i,j)*b(j)
 520 NEXT j
 530 LET b(i)=tt/a(i,i)
 540 NEXT i
 550 LET err=0
 560 FOR i=1 TO nc
 570 IF ABS (b(i)-c(i))>err THEN LET err=ABS (b(i)-c(i))
 580 NEXT i
 590 PRINT "POLY ";v;" ";n;" ";nc;" ";err;" ";b(1);" ";b(nc)
 610 NEXT v
 620 PRINT "DONE POLY_FIT"
 630 STOP 

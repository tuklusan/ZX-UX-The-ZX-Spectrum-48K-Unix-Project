  10 DIM a(10,10): DIM b(10): DIM c(10): DIM d(10)
  20 FOR v=1 TO 2
  30 LET n=4+3*v
  40 FOR j=1 TO n
  50 LET c(j)=.125*j
  60 FOR i=1 TO n
  70 LET a(i,j)=.05*(i+j)
  80 IF i=j THEN LET a(i,j)=5+.2*i
  90 NEXT i
 100 NEXT j
 110 LET a(1,1)=.01: LET a(2,1)=2
 120 FOR i=1 TO n
 130 LET b(i)=0
 140 FOR j=1 TO n
 150 LET b(i)=b(i)+a(i,j)*c(j)
 160 NEXT j
 170 NEXT i
 180 LET info=0
 190 FOR k=1 TO n
 200 LET pp=k: LET big=0
 210 FOR i=k TO n
 220 IF ABS a(i,k)>big THEN LET big=ABS a(i,k): LET pp=i
 230 NEXT i
 240 IF big=0 THEN LET info=k: GO TO 380
 250 IF pp=k THEN GO TO 290
 260 FOR j=1 TO n
 270 LET tt=a(k,j): LET a(k,j)=a(pp,j): LET a(pp,j)=tt
 280 NEXT j
 290 LET d(k)=pp
 300 IF k=n THEN GO TO 370
 310 FOR i=k+1 TO n
 320 LET mult=a(i,k)/a(k,k): LET a(i,k)=mult
 330 FOR j=k+1 TO n
 340 LET a(i,j)=a(i,j)-mult*a(k,j)
 350 NEXT j
 360 NEXT i
 370 NEXT k
 380 IF info<>0 THEN GO TO 550
 390 FOR k=1 TO n
 400 LET pp=d(k): LET tt=b(k): LET b(k)=b(pp): LET b(pp)=tt
 410 NEXT k
 420 FOR k=1 TO n-1
 430 FOR i=k+1 TO n
 440 LET b(i)=b(i)-a(i,k)*b(k)
 450 NEXT i
 460 NEXT k
 470 FOR k=n TO 1 STEP -1
 480 LET tt=b(k)
 490 IF k=n THEN GO TO 530
 500 FOR j=k+1 TO n
 510 LET tt=tt-a(k,j)*b(j)
 520 NEXT j
 530 LET b(k)=tt/a(k,k)
 540 NEXT k
 550 LET err=0
 560 IF info<>0 THEN LET err=999: GO TO 600
 570 FOR i=1 TO n
 580 IF ABS (b(i)-c(i))>err THEN LET err=ABS (b(i)-c(i))
 590 NEXT i
 600 PRINT "LINPACK ";v;" ";n;" ";info;" ";err
 620 NEXT v
 630 PRINT "DONE MINI_LINPA"
 640 STOP 

  10 DIM a(64): DIM b(64)
  20 LET n=64: LET pp=3.14159265
  30 FOR v=1 TO 2
  40 FOR i=1 TO n
  50 LET a(i)=0: LET b(i)=0
  60 NEXT i
  70 LET a(1)=1
  80 IF v=2 THEN LET a(33)=1
  90 LET j=1
 100 FOR i=1 TO n
 110 IF i>=j THEN GO TO 140
 120 LET tr=a(i): LET a(i)=a(j): LET a(j)=tr
 130 LET ti=b(i): LET b(i)=b(j): LET b(j)=ti
 140 LET m=n/2
 150 IF m<2 OR j<=m THEN GO TO 170
 160 LET j=j-m: LET m=m/2: GO TO 150
 170 LET j=j+m
 180 NEXT i
 190 LET le=2
 200 FOR p=1 TO 6
 210 LET le2=le/2: LET th=-2*pp/le
 220 LET ws=COS th: LET wt=SIN th
 230 LET wr=1: LET wi=0
 240 FOR j=1 TO le2
 250 FOR i=j TO n STEP le
 260 LET k=i+le2
 270 LET tr=wr*a(k)-wi*b(k)
 280 LET ti=wr*b(k)+wi*a(k)
 290 LET ar=a(i): LET ai=b(i)
 300 LET a(k)=ar-tr: LET b(k)=ai-ti
 310 LET a(i)=ar+tr: LET b(i)=ai+ti
 320 NEXT i
 330 LET tr=wr*ws-wi*wt
 340 LET wi=wr*wt+wi*ws: LET wr=tr
 350 NEXT j
 360 LET le=le*2
 370 NEXT p
 380 LET err=0
 390 FOR i=1 TO n
 400 LET expected=1
 410 IF v=2 THEN LET expected=0
 420 IF v=2 AND i-2*INT (i/2)<>0 THEN LET expected=2
 430 LET dd=ABS (a(i)-expected)+ABS b(i)
 440 IF dd>err THEN LET err=dd
 450 NEXT i
 460 PRINT "FFT ";v;" ";n;" ";err;" ";a(1);" ";a(2)
 480 NEXT v
 490 PRINT "DONE TINY_FFT"
 500 STOP 

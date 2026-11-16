  10 FOR v=1 TO 2
  20 LET aa=0: LET bb=2
  30 IF v=1 THEN LET aa=1
  40 LET xx=aa: GO SUB 360: LET fa=fx
  50 LET xx=bb: GO SUB 360: LET fb=fx
  60 LET cc=aa: LET fc=fa: LET dd=bb-aa: LET ee=dd
  70 FOR t=1 TO 50
  80 IF fb*fc>0 THEN LET cc=aa: LET fc=fa: LET dd=bb-aa: LET ee=dd
  90 IF ABS fc<ABS fb THEN LET aa=bb: LET bb=cc: LET cc=aa: LET fa=fb: LET fb=fc: LET fc=fa
 100 LET tol=.000002*ABS bb+.000001: LET xm=(cc-bb)/2
 110 IF ABS xm<=tol OR fb=0 THEN GO TO 300
 120 IF ABS ee<tol OR ABS fa<=ABS fb THEN GO TO 230
 130 LET ss=fb/fa
 140 IF aa=cc THEN LET pp=2*xm*ss: LET qq=1-ss: GO TO 180
 150 LET qq=fa/fc: LET rr=fb/fc
 160 LET pp=ss*(2*xm*qq*(qq-rr)-(bb-aa)*(rr-1))
 170 LET qq=(qq-1)*(rr-1)*(ss-1)
 180 IF pp>0 THEN LET qq=-qq
 190 LET pp=ABS pp: LET tt=3*xm*qq-ABS (tol*qq)
 200 IF tt>ABS (ee*qq) THEN LET tt=ABS (ee*qq)
 210 IF 2*pp>=tt THEN GO TO 230
 220 LET ee=dd: LET dd=pp/qq: GO TO 240
 230 LET dd=xm: LET ee=dd
 240 LET aa=bb: LET fa=fb
 250 IF ABS dd>tol THEN LET bb=bb+dd: GO TO 280
 260 IF xm>0 THEN LET bb=bb+tol
 270 IF xm<0 THEN LET bb=bb-tol
 280 LET xx=bb: GO SUB 360: LET fb=fx
 290 NEXT t
 300 LET xx=bb: GO SUB 360
 310 PRINT "BRENT ";v;" ";t;" ";bb;" ";fx
 330 NEXT v
 340 PRINT "DONE BRENT_ROOT"
 350 STOP 
 360 LET fx=xx*xx*xx-xx-2
 370 IF v=2 THEN LET fx=COS xx-xx
 380 RETURN 

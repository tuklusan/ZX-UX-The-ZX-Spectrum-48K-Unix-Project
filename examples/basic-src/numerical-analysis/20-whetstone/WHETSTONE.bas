  10 FOR v=1 TO 2
  20 LET ii=3*v: LET tt=.499975
  30 LET x1=1: LET x2=-1: LET x3=-1: LET x4=-1
  40 FOR i=1 TO ii
  50 FOR j=1 TO 12
  60 LET x1=(x1+x2+x3-x4)*tt
  70 LET x2=(x1+x2-x3+x4)*tt
  80 LET x3=(x1-x2+x3+x4)*tt
  90 LET x4=(-x1+x2+x3+x4)*tt
 100 NEXT j
 110 NEXT i
 120 LET yy=.5: LET zz=.25
 130 FOR i=1 TO ii
 140 FOR j=1 TO 8
 150 LET yy=yy+.01*zz
 160 LET zz=(zz+yy)/2
 170 LET yy=yy/(1+.0001*zz)
 180 NEXT j
 190 NEXT i
 200 LET ss=0
 210 FOR k=1 TO ii
 220 LET ss=ss+SQR (1+.01*k)
 230 LET ss=ss+SIN (.01*k)*COS (.02*k)
 240 NEXT k
 250 PRINT "WHET ";v;" ";x1;" ";x2;" ";x3;" ";x4
 270 PRINT yy;" ";zz;" ";ss
 290 NEXT v
 300 PRINT "DONE WHETSTONE"
 310 STOP 

  10 DIM a(8,8)
  20 FOR v=1 TO 2
  30 LET a(1,1)=(1+EXP (1))/2: LET exact=EXP (1)-1
  40 IF v=2 THEN LET a(1,1)=3: LET exact=3.14159265
  50 LET n=1: LET h=1
  60 FOR k=2 TO 7
  70 LET h=h/2: LET ss=0
  80 FOR i=1 TO n
  90 LET xx=(2*i-1)*h: LET yy=EXP xx
 100 IF v=2 THEN LET yy=4/(1+xx*xx)
 110 LET ss=ss+yy
 120 NEXT i
 130 LET a(k,1)=a(k-1,1)/2+h*ss
 140 LET fact=1
 150 FOR j=2 TO k
 160 LET fact=fact*4
 170 LET a(k,j)=a(k,j-1)+(a(k,j-1)-a(k-1,j-1))/(fact-1)
 180 NEXT j
 190 LET n=n*2
 200 NEXT k
 210 PRINT "ROMBERG ";v;" ";n;" ";a(7,7);" ";ABS (a(7,7)-exact)
 230 NEXT v
 240 PRINT "DONE ROMBERG"
 250 STOP 

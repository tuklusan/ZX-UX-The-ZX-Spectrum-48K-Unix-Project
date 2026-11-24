  10 DIM a(3)
  20 LET a(1)=1: LET a(2)=12345: LET a(3)=32748
  30 PRINT "LCG MOD ";-13+INT (13/5)*5
  50 FOR v=1 TO 3
  60 LET seed=a(v): LET chk=0
  70 FOR i=1 TO 64
  80 LET q=INT (seed/436): LET r=seed-q*436
  90 LET tt=75*r-49*q
 100 IF tt<=0 THEN LET tt=tt+32749
 110 LET seed=tt
 120 LET chk=chk+seed-INT (seed/97)*97
 130 LET chk=chk-INT (chk/997)*997
 140 NEXT i
 150 PRINT "LCG ";v;" ";seed;" ";chk
 170 NEXT v
 180 PRINT "DONE LCG_RAND"
 190 STOP 

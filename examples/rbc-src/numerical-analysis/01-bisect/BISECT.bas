  10 FOR v=1 TO 2
  20 LET aa=1: LET bb=2
  30 FOR i=1 TO 28
  40 LET mm=(aa+bb)/2
  50 LET fa=aa*aa-2: LET fm=mm*mm-2
  60 IF v=2 THEN LET fa=aa*aa*aa-aa-2: LET fm=mm*mm*mm-mm-2
  70 IF fa*fm<0 THEN LET bb=mm
  80 IF fa*fm>=0 THEN LET aa=mm
  90 IF ABS (bb-aa)<.00001 THEN GO TO 110
 100 NEXT i
 110 LET mm=(aa+bb)/2: LET res=mm*mm-2
 120 IF v=2 THEN LET res=mm*mm*mm-mm-2
 130 PRINT "BISECT ";v;" ";i;" ";mm;" ";res
 150 NEXT v
 160 PRINT "DONE BISECT"
 170 STOP 

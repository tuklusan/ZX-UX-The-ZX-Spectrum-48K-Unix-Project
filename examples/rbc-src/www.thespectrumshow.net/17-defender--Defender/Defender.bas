   1 FOR f=0 TO 7: POKE USR "b"+f,RND*255: POKE USR "c"+f,RND*255: NEXT f
   2 LET i=0: LET bl=20
   3 LET s=0: LET d=0
   6 FOR f=0 TO 7: READ a: POKE USR "a"+f,a: NEXT f: DATA 220,8,4,255,255,4,8,220
   7 FOR f=0 TO 7: READ x,y: POKE USR "d"+f,x: POKE USR "e"+f,y: NEXT f: DATA 24,7,32,174,64,192,63,128,63,128,64,192,32,174,24,7
   8 LET b$="--------------------------------": LET c$="                                "
   9 LET f=0: LET x=10
  10 LET a$="{8E}{88}{8D}{8F}{8E}{8D}{8E}{84}{8D}{84}{8F}{8C}{84}{8A}{8D}{8E}{8C}{88}{8E}{8D}{8E}{88}{8F}{84}{88}{8E}{8A}  {8C}{8E} "
  20 PRINT INK 2;AT 21,0;"{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}"
  25 GO TO 45
  30 PRINT INK 2;AT 20,0;a$
  40 LET a$=a$+a$(1): LET a$=a$(2 TO )
  43 RETURN 
  45 GO SUB 30
  46 GO SUB 49: IF i<>0 THEN GO SUB 410
  47 IF i=0 THEN GO SUB 400
  48 GO TO 45
  49 PRINT AT x,0;" "
  50 LET x=x+(INKEY$="z" AND x<19)-(INKEY$="a" AND x>1)
  55 PRINT AT x,0;"{90}"
  57 IF f<>0 THEN RETURN 
  60 IF INKEY$=" " THEN GO TO 700
  70 RETURN 
 300 FOR v=1 TO 20
 310 PRINT AT q,f; FLASH 1;"{92}{91}{92}"
 320 GO SUB 49: GO SUB 30: NEXT v
 330 PRINT AT d,i-1;"     ": LET i=0: LET s=s+1: PRINT AT 0,0;s: IF INT (s/10)*10=s THEN LET bl=bl+20
 340 PRINT AT 0,10;bl;" ": LET f=0: RETURN 
 400 LET d=RND*18+1: LET i=30: LET d=INT d
 410 PRINT AT d,i;"  ": LET i=i-1: IF i=0 THEN GO TO 500
 415 LET d=d-1: IF RND>.5 THEN LET d=d+2
 417 IF d<1 THEN LET d=1
 418 IF d>19 THEN LET d=19
 420 PRINT AT d,i;"{93}{94}": RETURN 
 500 PRINT AT x,0;"***"; FLASH 1;AT 10,10;"INVADED  SCORE=";s;AT d,i; FLASH 1;"***"
 510 GO SUB 30: GO TO 510
 700 LET bl=bl-1: IF bl=-1 THEN GO TO 800
 701 PRINT AT 0,10;bl;"  ": IF d=x THEN GO TO 750
 710 PRINT AT x,1;"-------------------------------": PRINT AT x,1;"                               ": RETURN 
 750 PRINT AT x,1;b$( TO i)
 751 FOR v=1 TO 3: NEXT v
 752 PRINT AT x,1;c$( TO i)
 760 LET q=x: LET f=i: GO TO 300
 800 PRINT FLASH 1;AT 10,10;"No bullets left": GO TO 510

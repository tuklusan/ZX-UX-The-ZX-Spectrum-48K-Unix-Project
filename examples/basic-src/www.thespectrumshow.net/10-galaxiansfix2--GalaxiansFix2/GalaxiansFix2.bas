   1 REM {8B}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{87}
   2 REM {8B}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{83}{87}
   3 REM {8A}SPECTRUM  GALAXIANS {85}
   4 REM {8A}{7F} C.D. Fisher 6/1982{85}
   5 REM {8E}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8D}
   6 REM {8E}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8C}{8D}
   7 REM 
   8 REM 
  10 BORDER 0: PAPER 0: INK 7: CLS 
  11 PRINT AT 10,10; FLASH 1;"Please wait."
  12 GO SUB 1000
  13 GO SUB 5000
  14 RANDOMIZE 
  15 LET a=0
  19 LET s=0
  20 LET w=1: LET w$="{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}{95}"
  25 LET D=1
  26 LET y=2
  27 LET g$=" {9E}{9F} {9E}{9F} {9E}{9F} {9E}{9F} {9E}{9F} {9E}{9F}   {9E}{9F} {9E}{9F} {9E}{9F} {9E}{9F} {9E}{9F} {9E}{9F} {9E}{9F} {9E}{9F} {9E}{9F} {9E}{9F} "
  30 LET P=8
  39 LET y=2
  42 FOR i=50 TO 2 STEP -3: IF g$(i)=" " THEN NEXT i
  44 LET h=i-19*(i>19)-19*(i>38)+y
  45 LET g$(i-1 TO i+1)="  "
  46 IF i<4 THEN GO TO 89
  47 LET id=(h<16)-(h>=16)
  49 FOR x=50 TO 2 STEP -3: IF g$(x)=" " THEN NEXT x
  54 LET l=x-19*(x>19)-19*(x>38)+y
  55 LET g$(x-1 TO x+1)="  "
  56 LET idl=(l<16)-(l>=16)
  80 LET oh=h: LET ol=l
  88 LET b$="{96}{97}"
  89 LET a$="{96}{97}"
  90 CLS 
  91 PRINT INVERSE 1;AT 1,1;"1up:";s;TAB 15;"HIGH SCORE:";a
  92:
  93: REM    Main loop
  94:
  95 FOR v=3 TO 19
 100 PRINT AT v-1,oh;"  ";AT v-1,ol;"  "
 105 PRINT INVERSE 1;AT 1,5;s; INVERSE 0; INK 4;AT 3,y;g$( TO 21);TAB y;g$(22 TO 38);TAB y;g$(39 TO )
 110 PRINT INK 3;AT v,h;a$;AT v,l;b$; INK 7;AT 20,p-2;"  {91}  "
 115 LET y=y+d: IF y<2 OR y>10 THEN LET d=-d
 119 IF INKEY$="0" THEN INK 2: PLOT p*8+3,16: DRAW 0,130: BEEP .03,50: DRAW OVER 1;0,-130: INK 7
 120 IF INKEY$="0" AND (((p=h OR p=h+1) AND a$<>"") OR ((p=l OR p=l+1) AND b$<>"")) THEN GO SUB 248
 125 BEEP .01,-14
 130 IF RND>.5 THEN GO SUB 800
 140 LET p=p+2*((INKEY$="3") AND p<29)-2*((INKEY$="1") AND p>2)
 141 LET oh=h: LET ol=l
 150 LET di=(INT (RND*2)+1)*id
 155 LET h=h+di
 156 IF h>30 OR h<0 THEN LET id=-id: LET h=30*(l>16): GO TO 150
 159 LET di=(INT (RND*2)+1)*idl
 160 LET l=l+di
 161 IF l>30 OR l<0 THEN LET idl=-idl: LET l=30*(l>16): GO TO 159
 165 LET l=l+(l<2)-(l>30)
 166 IF a$="" AND b$="" THEN GO TO 176
 167 PLOT INVERSE 1;0,15: DRAW INVERSE 1;254,0
 169 PRINT AT 21,0;w$( TO w)
 170 NEXT v
 171 IF a$="{96}{97}" OR b$="{96}{97}" THEN GO SUB 600
 176 IF x<6 AND i<6 AND a$="" AND b$="" THEN LET w=w+1: LET s=s+50: PRINT AT 1,9; FLASH 1;"BONUS": PAUSE 250: PAUSE 0: GO TO 25
 180 IF ABS (p+1-l)>1 AND ABS (p+1-h)>1 THEN GO TO 40
 190 IF (ABS (p+1-l)<=1 AND b$="") OR (ABS (p+1-h)<=1 AND a$="") THEN GO TO 40
 195 PRINT AT 20,p; FLASH 1;"{91}"
 200 PRINT AT 10,10; FLASH 1;"SCORE:";s: BEEP 1,20
 201 IF a<s THEN LET a=s
 202 LET s=0
 203 LET li=3
 215 PAUSE 0: PAUSE 0
 220 GO TO 20
 230:
 231: REM Subroutine to Explode
 232: REM   Appropriate alien.
 233:
 248 LET s=s+10
 249 BEEP .5,35
 250 IF p=h+1 OR p=h THEN PRINT AT v,h;"{A0}{A0}": LET a$=""
 260 IF p=l+1 OR p=l THEN PRINT AT v,l;"{A0}{A0}": LET b$=""
 270 RETURN 
 595:
 596 REM sub to replace
 597 REM aliens in pool if
 598 REM they escape
 599:
 600 IF a$="{96}{97}" THEN LET g$(x TO x+1)="{9E}{9F}"
 610 IF b$="{96}{97}" THEN LET g$(i TO i+1)="{9E}{9F}"
 620 RETURN 
 795:
 796: REM Subroutine to fire
 797: REM aliens missiles.
 798:
 800 LET c$="hl"(INT (RND*2)+1)
 805 IF c$="h" AND a$="" OR c$="l" AND b$="" THEN RETURN 
 806 INK 6
 810 PLOT VAL c$*8+8,(21-v)*8-2
 815 DRAW VAL c$*8+8-PEEK 23677,16-PEEK 23678
 816 INK 7
 830 IF VAL c$=p OR VAL c$+1=p THEN GO TO 195
 840 REM DRAW OVER 1;0,(19-v)*8-2
 844 PLOT OVER 1;VAL c$*8+8,(21-v)*8-2
 845 DRAW OVER 1;VAL c$*8+8-PEEK 23677,16-PEEK 23678
 846 INK 7
 850 RETURN 
 995:
 996: REM Subroutine to set up
 997 REM user-defined chars.
 998:
1000 FOR x=1 TO 7: READ p$: FOR n=0 TO 7
1010 READ r: POKE USR p$+n,r
1020 NEXT n: NEXT x
1030 DATA "o",2,2,71,125,7,31,59,49
1040 DATA "p",64,64,226,190,224,246,220,140
1041 DATA "g",49,56,31,7,125,71,2,2
1042 DATA "h",140,220,248,224,190,226,64,64
1050 DATA "b",24,60,153,169,255,255,219,129
1075 DATA "q",145,82,0,3,192,0,74,145
1076 DATA "f",128,192,224,192,128,128,128,128
1080 RETURN 
4994:
4995: REM Subroutine to print
4996: REM  instructions & scores
4998:
5000 CLS 
5005 PRINT TAB 10;"SPECTRUM GALAXIANS"'',"by C.Fisher."
5009 PRINT '"  The object of this game is to"
5010 PRINT "shoot as many of the diving,    firing aliens as you can --"
5020 PRINT "so getting a high score."
5025 PRINT ''TAB 5; FLASH 1;"THE CONTROLS:-"
5030 PRINT '"key '1'   moves you left"
5040 PRINT " '  '3'    '    '   right"
5050 PRINT " '  '0'   fires your laser."
5060 PRINT '' PAPER 2; FLASH 1;"GOOD LUCK  !!"
5070 INPUT "(press 'enter' to begin)"' LINE a$
5080 RETURN 

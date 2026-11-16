  10 POKE 23658,255: REM force upper case input
  20 REM Morse Tutor @ Robert Erskine 1983
  40 GO SUB 8500
 100 PAPER 1: INK 5: BORDER 1: CLS 
 110 PRINT AT 1,11;"OPTIONS"
 120 PRINT 
 140 PRINT "1 Print a message": PRINT 
 150 PRINT "2 Message with sound only": PRINT 
 160 PRINT "3 Create your own message": PRINT 
 170 PRINT "4 Test section": PRINT 
 180 PRINT "5 Change speed": PRINT 
 190 PRINT "6 The Morse Code": PRINT 
 210 IF INKEY$="1" THEN GO TO 2005
 220 IF INKEY$="2" THEN GO TO 2000
 230 IF INKEY$="3" THEN GO TO 2030
 240 IF INKEY$="4" THEN GO TO 5000
 250 IF INKEY$="5" THEN GO TO 6000
 260 IF INKEY$="6" THEN GO TO 7000
 290 GO TO 210
1000 LET x$=v$: LET v$=q$+v$+h$
1010 FOR x=1 TO LEN v$-32
1020 IF O=0 THEN PRINT AT 21,0;v$(x TO x+31)
1025 LET T=CODE v$(x+31)
1030 FOR y=1 TO 5
1040 IF T>64 THEN BEEP c(CODE (v$(x+31))-64,y),25
1042 IF T<58 AND T>47 THEN BEEP c(CODE (v$(x+31))-21,y),25
1045 NEXT y
1046 PAUSE 3
1050 NEXT x
1999 GO TO 2110
2000 LET O=1
2005 LET v$=f$
2010 GO TO 1000
2020 GO TO 100
2030 CLS : PRINT AT 2,7;"CREATE A MESSAGE"
2040 PRINT "Enter your own message at the ","bottom of the screen and then ","press the ENTER key."
2050 INPUT v$
2060 CLS : PRINT "Do you want the message displayed in both sound and vision? (Y or N)"
2065 PAUSE 100
2070 IF INKEY$="" THEN GO TO 2070
2080 IF INKEY$="Y" THEN GO TO 2100
2090 LET O=1
2100 GO TO 1000
2110 LET O=0
2140 LET f$=x$
2150 GO TO 100
5000 CLS : PRINT AT 1,10;"TEST SECTION"
5010 PRINT 
5020 INPUT "Do you want to be tested on characters (1) code (2) or sound (3)?";A$
5030 IF A$="1" THEN LET W=1
5040 IF A$="2" THEN LET W=2
5050 IF A$="3" THEN LET W=3
5055 IF CODE A$<49 OR CODE A$>51 THEN GO TO 5020
5060 INPUT "Do you want testing on letters (1) or numbers (2)?";A$
5090 IF A$="1" THEN LET B=1
5100 IF A$="2" THEN LET B=2
5105 IF CODE A$<49 OR CODE A$>50 THEN GO TO 5060
5110 IF W>1 THEN GO TO 5250
5115 PAUSE 50
5120 PRINT "The character will appear first, followed shortly by the code and sound": PAUSE 100
5130 FOR x=1 TO 15
5140 IF B=1 THEN LET v=INT (RND*26)+1
5150 IF B=2 THEN LET v=(INT (RND*10)+1)+26
5160 IF B=1 THEN PRINT CHR$ (v+64);
5170 IF B=2 THEN PRINT CHR$ (v+21);
5180 PAUSE 50
5190 FOR y=1 TO 5
5200 BEEP c(v,y),25
5210 NEXT y
5220 PRINT " = ";c$(v)
5230 NEXT x
5240 PAUSE 50: GO TO 100
5250 IF W>2 THEN GO TO 5390
5260 PRINT "The code will appear first, followed shortly by the chracter and sound": PAUSE 100
5270 FOR x=1 TO 15
5280 IF B=1 THEN LET v=INT (RND*26)+1
5290 IF B=2 THEN LET v=(INT (RND*10)+1)+26
5300 PRINT c$(v);: PAUSE 50
5310 FOR y=1 TO 5
5320 BEEP c(v,y),25
5330 NEXT y
5340 PRINT " = ";
5350 IF B=1 THEN PRINT CHR$ (v+64)
5360 IF B=2 THEN PRINT CHR$ (v+21)
5370 NEXT x
5380 PAUSE 50: GO TO 100
5390 PRINT "The sound will be heard first, followed shortly by the character and code": PAUSE 100
5400 FOR x=1 TO 15
5410 IF B=1 THEN LET v=INT (RND*26)+1
5420 IF B=2 THEN LET v=(INT (RND*10)+1)+26
5430 FOR y=1 TO 5
5440 BEEP c(v,y),25
5450 NEXT y
5460 PAUSE 50
5470 PRINT "That was ";
5480 IF B=1 THEN PRINT CHR$ (v+64);" = ";c$(v),
5490 IF B=2 THEN PRINT CHR$ (v+21);" = ";c$(v),
5500 PAUSE 50
5510 NEXT x
5520 PAUSE 50: GO TO 100
6000 CLS : PRINT AT 1,6;"ALTER SPEED OF CODE": PRINT 
6010 PRINT "Enter a multiplication factor to alter the speed of the morse.  Values less than 1 will increase the speed"
6020 INPUT A
6030 IF A>9 THEN GO TO 6020
6040 PRINT "Please wait": LET s=s*A: LET l=l*A: GO SUB 9000
6050 GO TO 100
7000 CLS : PRINT AT 0,7;"THE MORSE CODE": PRINT 
7010 FOR X=1 TO 36
7020 IF X<27 THEN PRINT CHR$ (X+64);" = ";C$(X),
7030 IF X>26 THEN PRINT CHR$ (X+21);" = ";C$(X),
7040 NEXT X
7050 PRINT : PRINT AT 21,0;"PRESS ANY KEY TO RETURN"
7060 PAUSE 0
7070 GO TO 100
8500 LET s=.1: LET l=.3: LET O=0: LET x$=""
8510 LET f$="THIS IS A MESSAGE TO DEMONSTRATE THE MORSE CODE TUTOR    THE COMPLETE ALPHABET IS AS FOLLOWS       ABCDEFGHIJKLMNOPQRSTUVWXYZ      AND THE NUMBERS ARE       1234567890"
8520 LET q$="                               "
8530 LET h$=" "
9000 RESTORE : DIM c(36,5)
9010 FOR x=1 TO 36
9020 FOR y=1 TO 5
9030 READ c(x,y)
9040 NEXT y
9050 NEXT x
9060 DATA s,l,0,0,0,l,s,s,s,0,l,s,l,s,0,l,s,s,0,0,s,0,0,0,0,s,s,l,s,0,l,l,s,0,0,s,s,s,s,0,s,s,0,0,0,s,l,l,l,0,l,s,l,0,0,s,l,s,s,0,l,l,0,0,0,l,s,0,0,0,l,l,l,0,0,s,l,l,s,0,l,l,s,l,0,s,l,s,0,0,s,s,s,0,0,l,0,0,0,0,s,s,l,0,0,s,s,s,l,0,s,l,l,0,0,l,s,s,l,0,l,s,l,l,0,l,l,s,s,0
9070 DATA l,l,l,l,l,s,l,l,l,l,s,s,l,l,l,s,s,s,l,l,s,s,s,s,l,s,s,s,s,s,l,s,s,s,s,l,l,s,s,s,l,l,l,s,s,l,l,l,l,s
9080 DIM c$(36,9)
9090 FOR x=1 TO 36
9100 READ c$(x)
9110 DATA "._","_...","_._.","_..",".",".._.","_ _.","....","..","._ _ _","_._","._..","_ _","_.","_ _ _","._ _ .","_ _._","._.","...","_",".._","..._","._ _","_.._","_._ _","_ _..","_ _ _ _ _","._ _ _ _",".._ _ _","..._ _","...._",".....","_....","_ _...","_ _ _..","_ _ _ _."
9120 NEXT x
9130 RETURN 

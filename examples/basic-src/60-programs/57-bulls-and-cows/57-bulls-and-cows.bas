   1 REM Bulls and Cows @ Robert Erskine
  10 GO SUB 9000
  20 GO SUB 8000
  26 FOR x=1 TO 4
 100 RANDOMIZE : LET R=RND: INPUT "How many guesses do you want?";t
 110 GO SUB 1000
 120 CLS : PRINT "I have chosen a number": PAUSE 100
 130 GO SUB 2000
 135 FOR q=1 TO t
 140 INPUT "ENTER YOUR GUESS NOW (4 digits) "; LINE g$: IF LEN g$<>4 THEN PRINT #1; FLASH 1;"reinput correctly!!": PAUSE 60: GO TO 140
 145 FOR f=1 TO 4: IF CODE g$(f)<48 OR CODE g$(f)>57 THEN PRINT #1; FLASH 1;"Numbers only!!": PAUSE 60: GO TO 140: NEXT f
 150 GO SUB 200
 160 GO SUB 3000
 170 IF black<4 THEN NEXT q
 180 PAUSE 100: GO SUB 4000
 190 PRINT AT 21,4;"PRESS ANY KEY TO RESTART": PAUSE 0: GO TO 100
 200 LET black=0: LET white=0
 205 DIM a(4): DIM h(4)
 210 FOR x=1 TO 4
 215 LET a(x)=VAL (g$(x))
 217 NEXT x
 220 FOR x=1 TO 4
 230 IF a(x)=n(x) THEN LET black=black+1
 240 IF a(x)=n(x) THEN LET h(x)=1
 250 NEXT x
 260 FOR x=1 TO 4
 270 FOR y=1 TO 4
 280 IF a(x)=n(y) AND h(y)=0 THEN LET white=white+1: LET h(y)=1: GO TO 310
 290 NEXT y
 310 NEXT x
 320 PRINT g$;
 330 RETURN 
 800 PRINT AT 1,8;"Bulls and Cows": PRINT 
1000 DIM n(4): REM choose
1010 FOR x=1 TO 4
1020 LET n(x)=INT (RND*9)+1
1030 NEXT x
1040 RETURN 
2000 BORDER 0: PAPER 1: INK 7: CLS 
2010 PRINT "GUESSES     BULLS     COWS"
2020 PRINT 
2030 RETURN 
3000 IF black=0 THEN GO TO 3070
3010 LET f=13
3020 FOR x=1 TO black
3030 PRINT TAB (f); INK 0;"{90}";
3040 BEEP .1,25
3050 LET f=f+1
3060 NEXT x
3070 IF white=0 THEN GO TO 3130
3080 LET f=22
3085 FOR x=1 TO white
3090 PRINT INK 7;TAB (f);"{91}";
3100 BEEP .1,25
3110 LET f=f+1
3120 NEXT x
3130 PRINT 
3160 RETURN 
4000 IF black<4 THEN GO TO 4030
4010 CLS : PRINT AT 4,0;"You are correct. the number ",,,"I chose was ";
4020 GO TO 4040
4030 CLS : PRINT "That was not very good. The ",,,"number {AC} chose was ";
4040 FOR x=1 TO 4
4050 PRINT n(x);
4060 NEXT x
4070 PRINT : PRINT : PRINT ;"and you guessed ";
4080 FOR x=1 TO 4
4090 PRINT a(x);
4100 NEXT x
4110 PRINT 
4120 RETURN 
8010 PRINT "The object of Bulls and cows is","to guess a four digit number ","chosen by the computer. After ","each guess the computer will ","give you clues; each bull ","indicates a correct digit in thecorrect position andeach cow ","indicates a correct digit in ","the wrong position."
8020 PRINT AT 21,4;"Press any key to start"
8030 IF INKEY$="" THEN GO TO 8030
8040 RETURN 
9000 RESTORE : FOR x=USR "a" TO USR "b"+7
9010 READ n
9020 POKE x,n
9030 NEXT x
9040 DATA 0,2,3,255,126,126,66,66,0,0,3,255,126,126,66,66
9050 RETURN 

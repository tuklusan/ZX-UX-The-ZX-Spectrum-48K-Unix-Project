   1 REM toptrainer
   2 DATA "Ant ","Bee ","Cola","Dash","Emu ","Fox ","Gus ","Harp","Ibex","Jinn","Kay ","Lina","Mack","Nixy","Olly","Pug "
   5 RANDOMIZE 
  10 GO SUB 3000
  11 INK 0
  12 DIM h$(16,4): DIM h(16): DIM f(16): DIM p(16)
  14 DIM a$(8,5): DIM a(8): DIM v(2,16): DIM w(2,16)
  16 DIM t(16): DIM r(16): DIM s(16): DIM o(16): DIM q(4,16)
  18 DIM d(8)
  20 FOR i=1 TO 16
  22 READ h$(i)
  25 LET h(i)=INT (RND*10+1)
  26 LET o(i)=-1
  28 LET f(i)=0
  29 NEXT i: GO SUB 30: GO TO 100
  30 DATA 3,3,3,10,3,17,3,24
  31 DATA 8,24,13,24,18,24,18,17
  32 DATA 18,10,18,3,13,3,8,3
  35 FOR i=1 TO 12: READ w(1,i),w(2,i): NEXT i: DIM b(8)
  40 FOR i=1 TO 12
  42 LET v(1,i)=6-(4*((i-1)/4-INT ((i-1)/4)))
  44 LET v(2,i)=12-INT ((i-1)/4)
  45 NEXT i: RETURN 
 100 PAPER 1: BORDER 1: CLS 
 105 INPUT "How many players? (1-8) ";n
 107 IF n<1 OR n>8 THEN GO TO 100
 110 FOR i=1 TO n
 120 PRINT AT 21,0;"Name of Player  ";i;
 125 INPUT ":-";e$
 126 IF LEN e$>5 THEN PRINT AT 21,18;"Max 5 letters";: GO TO 125
 128 LET a$(i)=e$: LET a(i)=10000
 130 NEXT i
 135 BORDER 2
 140 INK 6: CLS : PRINT "        TOP TRAINER"
 141 INK 7: PRINT AT 2,4;"You start with {60}1000 each."
 142 PRINT "Each of you is an owner/trainer"
 144 PRINT "of horses which you can buy,"
 146 PRINT "sell, train up, and enter for"
 148 PRINT "races."
 150 PRINT AT 8,4;"You make money from winning"
 152 PRINT "races and also by betting on"
 154 PRINT "horses -yours or someone else's."
 156 PRINT AT 12,4;"Horses improve when they run"
 158 PRINT "well but lose value when they"
 160 PRINT "don't. It costs {60}500 to enter a"
 162 PRINT "horse for the race."
 164 PRINT AT 17,4;"If you go bankrupt, you lose"
 166 PRINT "the chance to train, run or bet"
 168 PRINT "on horses."
 170 GO SUB 9920
 200 BORDER 4: PAPER 6: CLS : INK 2: LET m=1: LET w3=0
 201 FOR i=2 TO 30 STEP 7
 205 FOR j=1 TO 21
 210 PRINT AT j,i;" ";
 215 NEXT j: NEXT i
 220 FOR i=1 TO 21 STEP 5
 225 FOR j=2 TO 30
 230 PRINT AT i,j;" ";
 235 NEXT j: NEXT i
 240 PRINT AT 11,10;"             ";
 250 FOR j=7 TO 15
 255 PRINT AT j,16;" ";: NEXT j
 256 FOR i=1 TO n: LET p(i)=1
 257 LET line=0: LET col=0: IF i>4 THEN LET line=1: LET col=-4
 258 PRINT AT w(1,p(i))+line,w(2,p(i))+i+col;CHR$ (48+i)
 259 NEXT i
 260 INK 2
 262 PRINT AT 2,3;"START> CHANCE {8F}SALE{8F} TRAIN  "
 265 PRINT AT 7,3;"TRAIN  ";: INK 1: PRINT "BANK BALANCE{60}";: INK 2: PRINT " {8F}SALE{8F}"
 270 PRINT AT 12,3;"CHANCE"
 272 PRINT AT 12,24;"CHANCE"
 275 PRINT AT 17,3;"{8F}SALE{8F} TRAIN  CHANCE {8F}SALE{8F}"
 280 FOR j=1 TO n
 285 PRINT AT 7+j,16;"       "
 290 PRINT AT 7+j,10;j;a$(j);
 291 IF a(j)<0 THEN PRINT "";
 292 PRINT AT 7+j,16;a(j);"";
 295 NEXT j
 300 INK 0: PRINT AT 0,0;a$(m);"'s go..."
 310 LET thro=INT (RND*6+1)
 315 GO SUB 9500
 320 PRINT AT 0,15;thro
 330 GO SUB 9500
 335 LET line=0: LET col=0: IF m>4 THEN LET line=1: LET col=-4
 336 PRINT AT w(1,p(m))+line,w(2,p(m))+m+col;" "
 337 LET x=p(m)+thro
 340 IF x>12 THEN LET x=x-12
 345 LET p(m)=x
 350 LET line=0: LET col=0: IF m>4 THEN LET line=1: LET col=-4
 352 PRINT AT w(1,p(m))+line,w(2,p(m))+m+col;CHR$ (48+m)
 355 GO SUB 9000
 358 IF x=1 THEN GO TO 450
 360 IF x=2 OR x=6 OR x=8 OR x=11 THEN GO TO 6000
 362 IF x=3 OR x=5 OR x=7 OR x=10 THEN GO TO 7000
 365 IF x=4 OR x=9 OR x=12 THEN GO TO 8000
 375 GO SUB 9900
 380 GO SUB 9000
 395 LET m=m+1
 397 IF m>n THEN LET m=1
 400 GO TO 280
 450 PAPER 0: BORDER 3: CLS : INK 6
 452 PRINT "Someone landed on START, so it's"
 455 PRINT : PRINT "time for a race...."
 460 GO SUB 9500
 470 LET r=0
 550 FOR i=1 TO n
 557 FOR j=1 TO 16
 560 IF o(j)<>i THEN GO TO 575
 562 CLS : PRINT AT 1,0;a$(i)
 563 PRINT AT 3,0;h$(j);" Cost {60}";h(j)*500: GO SUB 5400
 564 PRINT AT 7,0;"Will ";h$(j);" race today?"
 565 LET y$=INKEY$: IF y$="" THEN GO TO 565
 570 IF y$="y" THEN LET a(i)=a(i)-500: IF a(i)<0 THEN LET a(i)=a(i)+500: GO SUB 9600: GO TO 585
 572 IF y$="y" THEN LET s(j)=1: LET r=r+1: LET x=INT (h(j)+f(j)/2): GO SUB 5000
 575 NEXT j
 585 NEXT i
 599 PAPER 4: BORDER 3: CLS : LET z=0: LET a=0: LET rr=0
 600 GO SUB 4000: RESTORE 30: GO SUB 30
 605 LET rx=1
 610 LET m=INT (RND*16+1): IF w3>400 THEN GO TO 885
 615 IF s(m)=0 OR s(m)=5 THEN LET w3=w3+1: GO TO 610
 630 LET rr=rr+1: LET s(m)=5
 635 PRINT AT v(1,rr),v(2,rr);CHR$ (64+m)
 636 LET z=z+h(m)+f(m)
 637 LET p(m)=rr
 640 IF r<>rr THEN GO TO 610
 650 FOR j=1 TO 16
 655 IF s(j)<>5 THEN GO TO 662
 658 LET h9=h(j)+f(j): IF h9<=1 THEN LET h9=1
 660 INK 6: PRINT AT 0,0;"ODDS": PRINT AT rx,0;"";h$(j,1 TO 1);"=";INT (z/h9);""
 661 LET rx=rx+1
 662 NEXT j
 664 FOR i=1 TO n: INK 0
 665 IF a(i)<=0 THEN PRINT AT 20,0;a$(i);" has no cash to bet!": GO SUB 9500: GO TO 680
 666 PRINT AT 13,0;a$(i);" Bet?(Y/N)"
 667 FOR k=1 TO 10: LET y$=INKEY$: NEXT k
 668 LET y$=INKEY$: IF y$="" THEN GO TO 668
 670 IF y$="n" THEN GO TO 690
 672 PRINT "Horse's letter? ";: POKE 23658,255
 673 FOR k=1 TO 10: LET y$=INKEY$: NEXT k
 674 LET y$=INKEY$: IF y$="" THEN GO TO 674
 675 PRINT y$: POKE 23658,0
 676 FOR j=1 TO 16
 678 IF y$=h$(j,1) THEN LET b(i)=j
 679 NEXT j
 680 INPUT "How much money? ";y$: LET a=VAL y$
 683 IF a(i)<a THEN PRINT AT 21,0;"Not enough money in the kitty!": GO SUB 9500: GO TO 697
 684 LET d(i)=a: LET a(i)=a(i)-a
 690 PRINT AT 13,0;"                 "
 692 PRINT AT 14,0;"                   "
 695 PRINT AT 20,0;"                             "
 696 PRINT AT 21,0;"                             "
 697 NEXT i
 698 GO SUB 9000
 699 GO SUB 4300
 700 FOR j=1 TO 16
 705 LET ja=p(j)
 710 IF s(j)<>5 THEN GO TO 850
 720 LET r(ja)=1: IF v(2,ja)>24 THEN LET r(ja)=2
 730 IF v(1,ja)>16 THEN LET r(ja)=3
 740 IF r(ja)=3 AND v(2,ja)<10 THEN LET r(ja)=4
 750 LET m=INT (RND*5)
 760 IF m>2 THEN GO TO 780
 765 IF m=2 AND q(r(ja),ja)>0 THEN LET q(r(ja),ja)=q(r(ja),ja)-1: GO TO 780
 770 GO TO 850
 780 GO SUB 1000+100*r(ja)
 785 IF m=1 THEN GO TO 850
 800 PRINT AT v(1,ja),v(2,ja);" "
 810 LET v(1,ja)=v(1,ja)+y
 815 LET v(2,ja)=v(2,ja)+x
 820 PRINT AT v(1,ja),v(2,ja);h$(j,1 TO 1)
 840 IF r(ja)=4 AND v(2,ja)<5 THEN GO TO 860
 850 NEXT j
 855 GO TO 700
 860 GO SUB 9000
 861 PRINT AT 0,0;"The WINNER is ";h$(j): LET e$=h$(j): LET bj=j
 862 LET r=rr*1000
 863 PRINT AT 1,0;a$(o(j));" gets {60}";r;" prize": LET a(o(j))=a(o(j))+r
 865 GO SUB 9920
 867 CLS 
 868 LET z=INT (z/(h(j)+f(j))): IF z<1 THEN LET z=1
 869 GO SUB 2000: PRINT AT 2,0;e$;" won at odds of ";z;" to 1"
 870 FOR k=1 TO n
 872 IF b(k)=bj THEN LET a(k)=a(k)+b(k)*z+b(k): PRINT a$(k);"'s bet wins"
 876 NEXT k
 879 GO SUB 9920
 880 LET r=1: LET rr=1
 881 FOR j=1 TO 16: LET r(j)=1: LET s(j)=0: LET p(j)=0
 884 NEXT j
 885 CLS 
 886 GO TO 200
1100 LET x=1
1110 FOR y=1 TO -1 STEP -1: IF SCREEN$ (v(1,ja)+y,v(2,ja)+x)=" " THEN RETURN 
1120 NEXT y
1130 LET m=1: RETURN 
1200 LET y=1
1210 FOR x=-1 TO 1: IF SCREEN$ (v(1,ja)+y,v(2,ja)+x)=" " THEN RETURN 
1220 NEXT x
1230 LET m=1: RETURN 
1300 LET x=-1
1310 FOR y=1 TO -1 STEP -1: IF SCREEN$ (v(1,ja)+y,v(2,ja)+x)=" " THEN RETURN 
1320 NEXT y
1330 LET m=1: RETURN 
1400 GO TO 1300
2000 GO SUB 9000
2005 PRINT AT 0,0;"Form changes as a result of race"
2006 LET rx=0
2007 FOR j=1 TO 11
2010 FOR i=1 TO 3
2020 IF SCREEN$ (15+i,2+j)=" " THEN GO TO 2050
2025 LET x=CODE (SCREEN$ (15+i,2+j))-64
2027 LET rx=rx+1
2030 PRINT rx;" ";h$(x);
2032 IF j>=9 THEN PRINT " Will lose points";
2033 PRINT 
2034 LET f(x)=f(x)+INT ((13-j)*.75)
2050 NEXT i: NEXT j
2052 PRINT 
2055 PRINT "If any horse hasn't been given a"
2060 PRINT "mention then it has lost 4 form"
2065 PRINT "points. It should have stayed at"
2070 PRINT "home!"
2075 GO SUB 9500: GO SUB 9900: CLS 
2076 PRINT "Horse  Owner  {60} before  {60} now"
2080 FOR i=1 TO 16: IF s(i)<>5 THEN GO TO 2100
2085 LET f(i)=f(i)-4
2092 PRINT AT 1,0;h$(i);TAB (7);a$(o(i))
2095 PRINT AT i,14;t(i): PRINT AT i,22;h(i)*500+f(i)*250
2100 NEXT i
2110 RETURN 
3000 CLS : FOR j=1 TO 30
3010 INK (RND*8)
3015 PAPER (RND*8)
3020 PRINT AT RND*20,RND*21;"TOP TRAINER"
3030 NEXT j: RETURN 
4000 PRINT AT 2,8;"TTTTTTTTTTTTTTTTTTT"
4010 PRINT AT 7,8;"TTTTTTTTTTTTTTT"
4020 PRINT AT 15,0;"TTTTTTTTTTTTTTTTTTTTTTTT"
4030 PRINT AT 19,0;"TTTTTTTTTTTTTTTTTTTTTTTTTTTT"
4040 FOR i=2 TO 19: PRINT AT i,27;"T": NEXT i
4050 FOR i=7 TO 15: PRINT AT i,23;"T": NEXT i
4060 FOR i=3 TO 6: PRINT AT i,14;" ": NEXT i
4070 PRINT AT 15,4;"O": PRINT AT 15,13;" "
4090 RETURN 
4300 FOR i=3 TO 6: PRINT AT i,14;" ": NEXT i
4340 FOR i=1 TO 16: LET t(i)=INT (h(i)*500+f(i)*250): NEXT i
4350 RETURN 
5000 IF x<=0 THEN PRINT "This horse is badly off form": GO TO 5100
5005 PRINT "Points available for race...";x
5010 FOR m=1 TO 4
5020 IF m=4 THEN PRINT "The 4th quarter must be ";x: LET q(m,j)=x: GO TO 5100
5025 PRINT "Orders for quarter no. ";m;"(0-9)";
5027 FOR k=1 TO 10: LET y$=INKEY$: NEXT k
5030 LET y$=INKEY$: IF y$="" THEN GO TO 5030
5032 IF CODE (y$)<48 OR CODE (y$)>57 THEN GO TO 5030
5035 LET b=VAL y$
5040 LET x=x-b
5050 IF x<0 THEN LET b=b+x: LET x=0
5055 PRINT b
5060 LET q(m,j)=b
5070 NEXT m
5100 GO SUB 9900
5105 FOR m=1 TO 4: LET q(m,j)=0: NEXT m: RETURN 
5400 PRINT "Current value {60}";f(j)*250+h(j)*500
5405 IF (f(j)*250+h(j)*500)<=0 THEN PRINT "Which is bad news!!"
5410 RETURN 
6000 LET x=INT (RND*6+1)
6010 LET x=-250*x
6020 IF RND>.5 THEN LET x=-x
6030 LET a(m)=a(m)+x
6040 GO TO 375
7000 PRINT AT 0,0;"Does ";a$(m);" wish to sell a horse?"
7010 GO SUB 9800
7020 IF y$="n" THEN GO TO 7050
7025 GO SUB 9000
7026 FOR i=1 TO 16
7027 IF o(i)<>m THEN GO TO 7045
7028 PRINT AT 0,0;"Do you wish to sell ";h$(i): GO SUB 9800
7030 IF y$="n" THEN GO TO 7040
7031 GO SUB 9000: LET bb=INT (h(i)*500+f(i)*250): IF bb<0 THEN LET bb=0
7032 PRINT AT 0,0;h$(i);" cost {60}";h(i)*500;" Now worth {60}";bb
7033 INPUT "Buyer No. (if none type 0)";b
7035 IF b=0 THEN GO SUB 9000: PRINT AT 0,0;"OK, I'll take it for {60}";bb: GO SUB 9500
7036 IF b=0 THEN LET o(i)=-1: LET a(m)=a(m)+bb: GO TO 7040
7037 IF b>n THEN GO TO 7033
7038 INPUT "At what price {60}";a
7039 LET o(i)=b: LET a(m)=a(m)+a: LET a(b)=a(b)-a
7040 GO SUB 9000
7045 NEXT i
7050 LET offer=INT (RND*15+1)
7060 IF o(offer)<>-1 THEN GO TO 7050
7070 GO SUB 9000
7080 PRINT AT 0,0;"I'll sell you ";h$(offer);" for {60}";h(offer)*500
7100 GO SUB 9800
7105 GO SUB 9000
7110 IF y$<>"y" THEN GO TO 375
7120 PRINT AT 0,0;"OK - Done"
7125 LET o(offer)=m: LET a(m)=a(m)-h(offer)*500: GO TO 375
8000 FOR i=1 TO 16
8010 IF o(i)<>m THEN GO TO 8100
8012 IF a(m)<0 THEN PRINT AT 0,0;" You're BANKRUPT": GO SUB 9500: GO SUB 9000: GO TO 8100
8015 PRINT AT 0,0;"How much money to train ";h$(i)
8020 INPUT "{60} ";a
8030 IF a(m)-a<0 THEN PRINT AT 0,0;"Not enough cash in the kitty!": GO SUB 9500: GO TO 8050
8034 LET x=INT (RND*5+2)
8036 LET b=INT (x*a/3000): IF b>5 THEN LET b=5
8040 LET f(i)=f(i)+b: LET a(m)=a(m)-a
8050 GO SUB 9000
8100 NEXT i
8200 GO TO 375
9000 PRINT AT 0,0;"                                "
9010 RETURN 
9500 PAUSE 55: RETURN 
9800 LET y$=INKEY$
9805 IF y$="" THEN GO TO 9800
9810 RETURN 
9900 PRINT AT 0,0;"    Press any key to continue   "
9910 GO TO 9800
9920 PRINT AT 21,0;"Press any key"
9925 GO TO 9800
9960 PRINT 
9962 PRINT "cashless............."
9966 RETURN 

   1 BORDER 0: PAPER 0: INK 7: CLS 
 100 PRINT AT 0,6;"E V O L U T I O N"
 110 PRINT ' INK 6'"This semi-scientific series of"' INK 5'"routines gives you the chance to"' INK 4'"evolve from an amoeba to a human"' INK 7'"based on the theory that only"' INK 6'"the strong survive."'' INK 5'"Press ENTER to continue."
 120 PAUSE 0: CLS 
 122 PRINT "This program goes from amoeba   to frog to beaver."' INK 5'"The next program goes from      gorilla to caveman."' INK 4'"The final program of this trio  involves the present stage of   evolution - MAN and his tech-   nology."
 123 PRINT '"The intention is that you shouldtry the stages in the correct   order but after each stage you  are given a menu of options."
 124 PRINT '"Press ENTER to continue.": PAUSE 0: CLS 
 130 GO TO 1000
 140 PRINT "The first stage is as an amoeba ( {90} ). You have to eat 5 spores ( {93} ) while avoiding {91} and {92}."
 150 PRINT INK 6'"This is also a battle against   time, for when the clock at the top of the screen says 0, it    means that you have starved     because you did not eat the     spores in time."
 155 PRINT '"Move about in the water with thecursor keys 5-8."
 160 PRINT INK 5'"Press ENTER to start stage 1.": PAUSE 0: CLS : GO TO 1050
1000 LET a=0: RESTORE 1010: FOR f=USR "a" TO USR "d"+7: READ g: POKE f,g: NEXT f
1010 DATA 120,132,180,178,129,153,85,51
1020 DATA a,24,36,90,90,36,24,a
1030 DATA a,73,42,28,127,28,42,73
1040 DATA a,60,66,145,133,145,66,60
1045 GO TO 140
1050 LET ay=15: LET ax=14: DIM y(6): DIM x(6): LET a$="{91}{91}{92}{92}{93}{93}"
1055 LET t=100: LET sc=0
1060 FOR f=1 TO 6: LET y(f)=INT (RND*22): LET x(f)=INT (RND*32): PRINT BRIGHT 1;AT y(f),x(f); INK f;a$(f): NEXT f
1100 PRINT AT ay,ax;"{90}"
1110 FOR f=1 TO 5 STEP 2: FOR i=f TO f+1
1120 PRINT AT y(i),x(i);" ": LET y(i)=INT (y(i)+RND*2-RND*2): LET x(i)=INT (x(i)+RND*3-RND*3)
1125 IF f<5 THEN LET y(i)=y(i)+(y(i)<ay)-(y(i)>ay): LET x(i)=x(i)+(x(i)<ax)-(x(i)>ax)
1130 IF y(i)<a OR y(i)>21 THEN LET y(i)=11
1140 IF x(i)<a OR x(i)>31 THEN LET x(i)=15
1150 PRINT BRIGHT 1; INK f;AT y(i),x(i);a$(i)
1155 REM {FA}{AB}(ay,ax){C9}6{CB}{EC}1200
1157 PRINT AT ay,ax;" "
1160 LET ay=ay+(INKEY$="6" AND ay<21)-(INKEY$="7" AND ay>a)
1170 LET ax=ax+(INKEY$="8" AND ax<31)-(INKEY$="5" AND ax>a)
1175 LET t=t-1: PRINT AT a,15;t;" ": IF t=a THEN GO TO 1200
1176 IF ATTR (ay,ax)<>7 AND ATTR (ay,ax)<>6 THEN GO TO 1200
1177 PRINT AT ay,ax;"{90}"
1180 NEXT i: NEXT f: GO TO 1100
1200 IF ATTR (ay,ax)<69 THEN GO TO 1210
1201 PRINT FLASH 1;AT ay,ax;"{90}": FOR j=1 TO 15: BEEP .01,RND*20: NEXT j: FOR j=5 TO 6
1202 IF ay=y(j) AND ax=x(j) THEN LET wh=j
1203 NEXT j: LET y(wh)=INT (RND*22): LET x(wh)=INT (RND*32): PRINT INK wh;AT y(wh),x(wh);a$(wh)
1205 LET sc=sc+1: IF sc<5 THEN GO TO 1177
1208 CLS : PRINT "Well done you survived the first"' INK 6'"stage of evolution as an amoeba.": GO TO 8000
1210 FOR f=5 TO 30 STEP 5: BEEP .01,f: NEXT f: CLS : PRINT '"Bad luck! You failed in the 1st stage of evolution.": GO TO 8000
2000 PRINT "In this stage you have to catch flies on your tongue, while     avoiding the birds which swoop  down to try and capture their   prey- YOU !"
2010 PRINT INK 6'"Press 0 to stick your tongue out6 to move left, and 7 to move   right."' INK 5'"You have survived this stage    when you have consumed 10 flies without falling prey to the     birds."' INK 4'"Press ENTER to start."
2020 PAUSE 0: CLS 
2030 RESTORE 2040: FOR f=USR "a" TO USR "g"+7: READ g: POKE f,g: NEXT f
2040 DATA 28,34,78,79,56,32,64,48,56,68,114,242,28,4,2,12
2050 DATA 15,48,64,92,88,84,82,249,240,12,2,58,26,42,74,159
2060 DATA 0,0,0,34,85,63,24,0
2070 DATA 0,0,0,63,127,143,1,15,31,124,240,192,224,255,0,0
2100 LET x=15: LET y(1)=RND*6+13: LET x(1)=0: LET y(2)=0: LET x(2)=0: LET y(3)=y(2): LET x(3)=x(2): LET f=0
2110 INK 5: PLOT 0,7: DRAW 255,0: INK 4
2120 PRINT AT 0,15;f;AT 19,x;" {90}{91} ";AT 20,x;" {92}{93} "; INK 6;AT y(1),x(1);"{94}";AT y(3),x(3);"  "; INK 5;AT y(2),x(2);"{95}{96}"
2122 LET y(3)=y(2): LET x(3)=x(3)
2125 IF INKEY$="0" THEN GO SUB 2200
2130 IF INKEY$<>"" THEN BEEP .003,1: BEEP .003,2: BEEP .003,3: BEEP .003,4
2140 IF ATTR (18,x+2)=5 THEN GO TO 2250
2150 IF y(2)=18 THEN PRINT AT y(2),x(2);"  ": LET y(2)=0: LET x(2)=x+9: IF x(2)>30 THEN LET x(2)=30
2155 IF x(1)>29 THEN PRINT AT y(1),x(1);" ": LET x(1)=0: LET y(1)=RND*6+13
2160 PRINT AT y(1),x(1);" ";AT y(2),x(2);"  "
2180 LET y(2)=y(2)+2: LET x(2)=x(2)+(x(2)<x+1)-(x(2)>x+1): LET y(1)=y(1)+RND*1.5-RND*1.5: LET x(1)=x(1)+RND*1.5: IF y(1)>20 THEN LET y(1)=14
2190 LET x=x-(INKEY$="6" AND x>0)+(INKEY$="7" AND x<28)
2195 GO TO 2120
2200 PLOT x*8+12,17: DRAW 0,57
2202 BEEP .05,-10: BEEP .05,-6
2204 PLOT OVER 1;x*8+12,17: DRAW OVER 1;0,57
2210 IF ATTR (y(1),x(1))=4 THEN LET f=f+1: BEEP .1,-30: PRINT AT y(1),x(1);" ": LET x(1)=0: LET y(1)=RND*6+13
2220 IF f=10 THEN CLS : FOR f=10 TO 0 STEP -1: BEEP .05,f: NEXT f: PRINT '"Well done! You consumed 10 fliesand can therefore evolve to the next stage.": GO TO 8000
2230 RETURN 
2250 FOR f=1 TO 20: BEEP .01,f: NEXT f: CLS : PRINT '"You have been consumed and can  evolve no further.": GO TO 8000
3000 INK 7: PRINT "You have now evolved to a beaver"' INK 6'"In this stage you have to eat"' INK 5'"10 fish before you are eaten by"' INK 4'"the patrolling crab."
3010 PRINT '"Move using 5-8 and try to eat   the fish before the fresh-water crab does. Make sure that you   avoid the crab because if it    comes into contact with you it  will eat you and you will evolveno further."
3020 PRINT INK 5'"Press ENTER to start.": PAUSE 0: CLS 
3030 RESTORE 3040: FOR f=USR "a" TO USR "g"+7: READ g: POKE f,g: NEXT f
3040 DATA 0,0,15,16,224,159,8,12,0,32,220,10,1,254,16,24
3050 DATA 0,4,59,80,128,127,8,24,0,0,240,8,7,249,16,48
3060 DATA 0,0,8,61,191,255,255,255,12,30,{C4}10111010,255,255,{C4}10111110,30,12
3065 DATA 195,60,255,126,235,66,165,165
3070 PRINT AT 21,0; PAPER 1;"{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}{94}"
3080 FOR f=5 TO 20: PRINT INK 1; PAPER 1;AT f,0;"{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}{8F}": NEXT f
3085 LET y=20: LET x=15: LET y1=y: LET x1=x: LET f=5: LET g=0: LET f1=f: LET g1=g
3087 LET a$="{90}{91}": LET fi=0: PRINT AT 0,15;fi
3090 IF RND>.95 THEN PRINT BRIGHT 1; INK RND*4+3; PAPER 1;AT RND*15+5,RND*29+1;"{95}"
3095 IF ATTR (y,x)>64 OR ATTR (y,x+1)>64 THEN BEEP .1,0: LET fi=fi+1: PRINT AT 0,15;fi: IF fi=10 THEN PRINT AT y1,x1; INK 1; PAPER 1;"{8F}{8F}"; INK 4; FLASH 1;AT y,x;a$: FOR f=1 TO 30: BEEP .07,RND*20: NEXT f: GO TO 3250
3098 PRINT AT y1,x1; INK 1; PAPER 1;"   ";AT f1,g1;" "; INK 4;AT y,x;a$; INK 6;AT f,g;"{96}"
3115 LET y1=y: LET x1=x: LET f1=f: LET g1=g
3117 IF f=y THEN IF g=x OR g=x+1 THEN FOR f=1 TO 20: BEEP .01,f: NEXT f: GO TO 3300
3120 IF INKEY$="8" THEN LET a$="{90}{91}": LET x=x+(2 AND x<29)
3130 IF INKEY$="5" THEN LET a$="{92}{93}": LET x=x-(2 AND x>1)
3140 IF INKEY$="7" THEN IF y>5 THEN LET y=y-1
3150 IF INKEY$="6" THEN LET y=y+(y<20)
3160 LET f=INT (f+RND*1.5-RND*1.5+(f<y)-(f>y)): LET g=g+1
3170 IF f<5 OR f>20 THEN LET f=(20 AND f>20)+(5 AND f<5)
3180 IF g=31 THEN LET g=0
3190 GO TO 3090
3250 CLS : PRINT '"Well done! You survived as a    beaver and you can continue to  the next stage if you wish."
3260 GO TO 8000
3300 CLS : PRINT '"Bad luck! You can evolve no"' INK 6'"further because you have been"' INK 5'"destroyed by the crab.": GO TO 8000
8000 PRINT '"Press the key which corresponds to what you want to do next."
8010 PRINT INK 6'"1....Amoeba stage."''"2....Frog stage."''"3....Beaver stage."''"4....Load stages 4&5."''"5....Exit from the program."
8020 IF INKEY$="" THEN GO TO 8020
8030 IF INKEY$="1" THEN CLS : RUN 130
8040 IF INKEY$="2" THEN CLS : GO TO 2000
8050 IF INKEY$="3" THEN CLS : GO TO 3000
8060 IF INKEY$="4" THEN LOAD ""
8070 IF INKEY$="5" THEN STOP 
8080 GO TO 8020

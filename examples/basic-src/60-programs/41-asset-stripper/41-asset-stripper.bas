  10 BORDER 1: PAPER 1: INK 7: CLS 
  20 PRINT AT 0,9;"ASSET STRIPPER": PRINT AT 2,7;"@ R. Erskine 1982";AT 4,5;"What is your surname?"
  30 INPUT n$
  50 PRINT AT 5,4;"Enter difficulty level ";AT 6,11;"(1,2 or 3)"
  60 INPUT lev
  70 PRINT AT 7,10;"Please wait"
  80 RANDOMIZE 
  90 GO TO 3260
 100 PRINT TAB (11);"ACCOUNTS"
 140 PRINT 
 150 PRINT n$;e$
 160 PRINT 
 170 PRINT "Liquid assets ","{60}";INT ((ch+.005)*100)/100
 180 PRINT 
 190 LET q=0: LET q1=q
 200 FOR x=1 TO 10
 210 LET q=q+e(x)
 220 IF f$(x)="c" THEN GO TO 240
 230 LET q1=q1+(e(x)*d(x))
 240 NEXT x
 250 PRINT "Shares held ",INT q
 260 PRINT 
 270 PRINT "Total share value {60}";INT ((q1++.005)*100)/100
 280 PRINT 
 290 PRINT "Total assets","{60}";INT ((q1+ch+.005)*100)/100
 300 PRINT 
 310 IF q1+ch>s THEN GO TO 2720
 320 IF q1+ch<0 THEN GO TO 2760
 330 LET q3=0
 340 FOR x=1 TO 10
 345 IF f$(x)="c" THEN GO TO 355
 350 LET q3=q3+(f(x)*d(x))
 355 NEXT x
 360 IF q3+zxch>s THEN GO TO 2760
 370 IF q3+zxch<0 THEN GO TO 2720
 380 IF t$="x" AND ch+q1>zxch+q3 THEN GO TO 2720
 390 IF t$="x" AND ch+q1<zxch+q3 THEN GO TO 2760
 410 PRINT m$;" Claims assets of {60} ";q3+zxch
 420 PRINT 
 450 RETURN 
 480 PRINT TAB (10);"WIRE SERVICE"
 490 LET q=0: LET q1=0
 510 LET m(1)=asa
 520 FOR x=1 TO 10
 530 IF f$(x)="c" THEN PRINT c$(x),"Ceased trading"
 540 IF f$(x)="c" THEN GO TO 680
 550 PRINT 
 560 LET q=q+1
 570 IF b(x)>a(x) AND e(x)<510000 AND f(x)<510000 THEN PRINT c$(x),"May be ripe for takeover"
 580 PRINT 
 590 IF g(x)<1 AND w(x)>59 THEN PRINT c$(x),"Profits low"
 600 PRINT 
 610 IF w(x)<60 THEN PRINT c$(x),"Heads for trouble"
 620 PRINT 
 630 IF g(x)>5 THEN PRINT c$(x),"Set for good profits"
 640 PRINT 
 650 IF v(x)>0 AND v(x)>=1 THEN PRINT c$(x),"Announces ";INT v(x);" Redundancies"
 660 PRINT 
 670 LET q1=q1+d(x)
 675 PAUSE 100
 680 NEXT x
 690 IF q=0 THEN LET t$="x"
 700 IF q=0 THEN GO TO 110
 710 LET asa=q1/q
 720 PRINT "All share average ";INT ((asa+.005)*100)/100
 730 IF asa>m(1) THEN PRINT "up ";INT (((asa-m(1))+.005)*100)/100
 740 IF asa<m(1) THEN PRINT "down ";INT (((m(1)-asa)+.005)*100)/100
 750 IF asa>i(2) THEN PRINT "All time high"
 760 IF asa>i(2) THEN LET i(2)=asa
 770 IF asa<i(3) THEN PRINT "All time low"
 780 IF asa<i(3) THEN LET i(3)=asa
 810 RETURN 
 840 FOR x=1 TO 10
 850 IF f$(x)="c" THEN GO TO 1010
 860 IF lev=1 OR lev=2 THEN GO TO 880
 870 IF f$(x)="x" AND f(x)>0 AND f(x)<510000 THEN GO SUB 1110
 880 IF w(x)<61 AND f(x)<510000 THEN GO SUB 1105
 900 IF f$(x)="c" THEN GO TO 1010
 910 IF zxch<100 THEN GO TO 1010
 915 IF lev=1 AND RND>.5 THEN GO TO 950
 920 LET f=((((s/100)*51)-f(x))*d(x))
 930 IF (b(x)/100)*51>f AND f<zxch AND f(x)<510000 AND e(x)<510000 AND g(x)<1 THEN GO TO 2620
 940 IF f$(x)="c" THEN GO TO 1010
 950 IF zxch<100 THEN GO TO 1010
 955 LET tenth=zxch/10
 960 IF w(x)>60 AND g(x)>0 THEN GO SUB 1040
 970 IF lev=1 THEN GO TO 1010
 980 IF w(x)>60 AND g(x)>1 THEN GO SUB 1040
 990 IF w(x)>60 AND g(x)>5 THEN GO SUB 1040
1000 IF w(x)>60 AND g(x)>10 THEN GO SUB 1040
1010 NEXT x
1020 RETURN 
1040 IF (tenth/d(x))+e(x)+f(x)>l(x) THEN RETURN 
1050 IF f(x)<510000 AND (f(x)+(tenth/d(x)))>s/2 THEN RETURN 
1060 LET a(x)=a(x)+tenth*1.05
1070 LET zxch=zxch-tenth
1080 LET f(x)=f(x)+INT (tenth/d(x))
1090 LET l(x)=l(x)-INT (tenth/d(x))
1100 RETURN 
1110 LET a(x)=a(x)-((f(x)*d(x))*1.05)
1120 LET zxch=zxch+f(x)*d(x)
1130 LET l(x)=l(x)+f(x)
1140 LET f(x)=0
1150 RETURN 
1180 PRINT 
1190 PRINT TAB (9);"SHARE PRICES"
1200 PRINT 
1210 PRINT "COMPANY";TAB (11);"SHARE PRICE";TAB (24);"UP/DOWN"
1220 PRINT 
1230 FOR x=1 TO 10
1240 IF f$(x)="c" THEN PRINT c$(x);"CLOSED DOWN"
1250 IF f$(x)="c" THEN GO TO 1310
1260 IF INT d(x)=d(x) THEN LET p$=STR$ d(x)+".00"
1270 IF INT n(x)=n(x) THEN LET r$=STR$ n(x)+".00"
1280 IF INT d(x)<d(x) THEN LET p$=STR$ (INT ((d(x)+.005)*100)/100)
1290 IF INT n(x)<n(x) THEN LET r$=STR$ (INT ((n(x)+.005)*100)/100)
1300 PRINT c$(x);TAB (21-LEN p$+1);p$;TAB (30-LEN r$+1);r$
1310 NEXT x
1320 PRINT 
1380 PRINT "ALL SHARE AVERAGE ";INT ((asa+.005)*100)/100
1390 PRINT "You have {60}";INT ((ch+.005)*100)/100
1410 RETURN 
1430 PRINT "BUY HOW MANY?"
1440 INPUT y
1450 IF y*d(x)>ch THEN PRINT "You have insufficient cash"
1460 IF y*d(x)>ch THEN GO TO 1430
1470 IF y>l(x) THEN PRINT "Not enough shares available"
1480 IF y>l(x) THEN GO TO 1430
1490 IF y+e(x)>500000 AND e(x)<510000 THEN GO TO 1660
1500 LET ch=ch-(y*d(x))
1510 LET l(x)=l(x)-y
1520 LET a(x)=(a(x)+(y*d(x)))*1.05
1530 LET e(x)=e(x)+y
1540 LET x$="p"
1550 RETURN 
1570 PRINT "How many do you wish to sell?"
1580 INPUT y
1590 IF y>e(x) THEN PRINT "You do not hold that many"
1600 IF y>e(x) THEN GO TO 1570
1610 LET ch=ch+(y*d(x))
1620 LET l(x)=l(x)+y
1630 LET a(x)=a(x)-((y*d(x))*1.05)
1640 LET e(x)=e(x)-y
1645 LET x$="p"
1650 RETURN 
1680 LET t$="phaseh"
1690 LET z1=.01
1700 PRINT TAB (7);"TAKEOVER BID"
1705 PRINT 
1710 PRINT "Your shareholding is ";INT (e(x)*100)/s;" percent"
1720 PRINT "Current share price is {60}";INT ((d(x)+.005)*100)/100
1730 PRINT "There are ";INT l(x);" available"
1740 PRINT "You need ";INT (510000-e(x));" for a majority"
1750 PRINT "These cost {60}";INT (((510000-e(x))*d(x)+.005)*100)/100,"at market price"
1755 PRINT "You have {60}";INT ((ch+.005)*100)/100
1756 LET eg=0
1757 FOR v=1 TO 10
1758 IF f$(v)<>"c" THEN LET eg=eg+(f(v)*d(v))
1759 NEXT v
1760 IF RND>.10 THEN GO TO 1769
1762 PRINT "Third party wins bid"
1763 GO SUB 2040
1764 GO TO 1890
1769 PRINT "How much do you bid per share?"
1770 INPUT z
1810 IF z1>z THEN GO TO 1880
1820 LET k1=a(x)+(510000*(z+.01))
1822 LET k2=(510000-f(x))*(z+.01)
1830 IF k1>k2 AND (zxch+eg)>=k2 THEN LET z1=z+.01
1840 IF z1>z THEN PRINT m$;" bids ";INT ((z1+.005)*100)/100
1860 IF z1>z THEN GO TO 1760
1870 IF z1<z THEN GO SUB 1920
1880 IF z1>z THEN GO SUB 2170
1890 LET z1=z
1895 LET z=0
1900 IF t$="phaseh" THEN GO TO 1540
1910 IF t$="phasem" THEN GO TO 1010
1920 REM disposal
1930 PRINT 
1940 LET Z1=0
1950 LET F=0
1960 PRINT "YOU HAVE WON THE BID"
1970 LET CH=CH-(Z*(510000-E(X)))
1980 LET A(X)=A(X)+(Z*(510000-E(X)))
1990 LET E(X)=E(X)+(510000-E(X))
2000 LET L(X)=S-(E(X)+F(X))
2010 PRINT "Do you want to strip the assets of this company?"
2020 INPUT y$
2030 IF y$="n" THEN RETURN 
2040 PRINT "Assets are being distributed","amongs shareholders"
2050 LET psh=(e(x)*100)/s
2060 LET zxpsh=(f(x)*100)/s
2070 LET oo=b(x)/100
2080 LET ch=ch+(psh*oo)
2090 LET zxch=zxch+(zxpsh*oo)
2100 IF a(x)<=0 THEN GO TO 2140
2110 LET d(x)=a(x)/s
2120 LET ch=ch+(e(x)*d(x))
2130 LET zxch=zxch+(f(x)*d(x))
2140 LET f$(x)="c"
2150 LET l(x)=0
2160 RETURN 
2190 IF z1*(510000-f(x))>zxch THEN PRINT "Spectral withdraws": RETURN 
2200 PRINT m$;" has won bid"
2220 LET zxch=zxch-((510000-f(x))*z1)
2230 LET a(x)=a(x)+((510000-f(x))*z1)
2240 LET f(x)=f(x)+(510000-f(x))
2250 LET z1=0
2260 IF g(x)<1 THEN GO SUB 2040
2270 RETURN 
2290 FOR x=1 TO 10
2300 IF f$(x)="c" THEN GO TO 2590
2310 LET v(x)=0
2320 LET c(x)=0
2330 IF a(x)<10000 THEN LET a(x)=10000
2340 LET j(x)=a(x)/10
2350 LET c(x)=c(x)+j(x)
2360 IF h(x)<j(x)/1000 THEN LET h(x)=j(x)/1000
2370 IF b(x)>=a(x)/20 THEN GO TO 2400
2380 LET c(x)=c(x)+((a(x)/10)-b(x))
2390 LET b(x)=INT (a(x)/10)
2400 LET prod=j(x)/10
2410 LET rnd=INT (RND*3555)+1
2420 IF rnd=1 THEN LET w(x)=w(x)-1
2430 IF rnd=3 THEN LET w(x)=w(x)+1
2440 LET t(x)=prod*w(x)
2450 LET c(x)=c(x)+(h(x)*5000)
2460 LET prof=t(x)-c(x)
2470 LET a(x)=a(x)+t(x)
2480 LET a(x)=a(x)-c(x)
2490 IF a(x)<=10000 THEN LET v(x)=h(x)
2500 IF a(x)<=10000 THEN LET h(x)=j(x)/1000
2510 LET v(x)=v(x)-h(x)
2520 LET g(x)=(prof*100)/t(x)
2530 LET sp1=d(x)
2540 IF a(x)<10000 THEN LET a(x)=10000
2550 LET d(x)=a(x)/s
2560 LET n(x)=d(x)-sp1
2570 IF a(x)<10000 THEN LET a(x)=10000
2580 IF RND>.9 THEN LET w(x)=w(x)+10
2585 IF RND>.9 THEN LET w(x)=w(x)-10
2590 NEXT x
2610 RETURN 
2620 PRINT : PRINT 
2640 LET t$="phasem"
2660 PRINT m$;" bid for "
2670 PRINT c$(x);"takeover"
2680 LET z1=d(x)
2690 PRINT "at ";INT ((d(x)+.005)*100)/100;" per share"
2700 GO TO 1710
2740 PRINT "You have won"
2750 GO TO 2780
2770 PRINT m$;" has won","with {60}";zxch+q3
2780 PRINT "Do you want another game?"
2790 INPUT v$
2800 IF v$="y" THEN GO TO 10
2810 STOP 
2820 REM loop
2830 GO SUB 2280
2850 GO SUB 2280
2860 GO SUB 100
2870 GO SUB 460
2890 GO SUB 1180
2900 PRINT "ENTER INITIAL OF CHOSEN COMPANY"
2910 PRINT "OR P(PASS)";w$
2920 INPUT x$
2930 IF x$="p" THEN GO TO 3240
2940 FOR x=1 TO 10
2950 IF CODE c$(x)(1)=CODE x$-32 THEN GO TO 2970
2960 NEXT x
2965 GO TO 2900
2970 IF f$(x)="c" THEN GO TO 2900
2980 PRINT 
2990 PRINT c$(x)
3000 PRINT "Liquid capital {60}";INT ((a(x)+.005)*100)/100
3010 PRINT "Capital equipment {60}";INT ((b(x)+.005)*100)/100
3020 PRINT "Employees ";INT h(x)
3030 PRINT "Overheads {60}";INT ((c(x)+.005)*100)/100
3040 PRINT "Profit {60}";INT ((t(x)-c(x)+.005)*100)/100
3050 PRINT "Profit percent of turnover {60}";INT g(x)
3060 PRINT "Share price {60}";INT ((d(x)+.005)*100)/100
3070 PRINT "Shares available ";INT l(x)
3080 PRINT "Shares held by you ";INT e(x)
3090 PRINT "Percentage shares held by you ";INT ((e(x)*100)/s)
3100 PRINT "________________________________"
3120 IF e(x)>=510000 THEN PRINT "Dispose of assets?"
3130 IF e(x)>=510000 THEN INPUT a$
3140 IF e(x)<510000 THEN LET a$="n"
3150 IF e(x)>=510000 AND a$="y" THEN GO SUB 2040
3160 IF f$(x)="x" THEN PRINT "Buy (b),Sell (s),or Pass (p)"
3170 IF f$(x)="x" THEN INPUT x$
3175 IF f$(x)="c" THEN LET x$="p"
3180 IF x$<>"p" AND x$<>"s" AND x$<>"b" THEN GO TO 2900
3190 IF x$="b" THEN GO SUB 1420
3200 IF x$="s" THEN GO SUB 1560
3210 IF x$="p" THEN PRINT "Look at another company(y or n)"
3220 IF x$="p" THEN INPUT a$
3230 IF x$="p" AND a$="y" THEN GO TO 2890
3240 GO SUB 820
3250 GO TO 2850
3270 LET m$="Spectral Investments Ltd"
3280 DIM c$(10,18)
3290 LET c$(1)="ACME CORP"
3300 LET c$(2)="BRN IND."
3310 LET c$(3)="CAPRA STEEL"
3320 LET c$(4)="DELTA GROUP"
3330 LET c$(5)="ELLIOT CORP"
3340 LET c$(6)="FORAX CHEMICALS"
3350 LET c$(7)="GNS INT."
3360 LET c$(8)="HOPE HOLDINGS"
3370 LET c$(9)="INCE AND CO."
3380 LET c$(10)="JONES AND PEEKE"
3390 LET x=10
3400 DIM a(x): DIM b(x): DIM c(x): DIM t(x): DIM d(x): DIM p(x): DIM e(x): DIM f(x): DIM g(x): DIM h(x)
3500 DIM i(3)
3510 LET w$="            "
3520 DIM j(x): DIM l(x)
3540 LET e$=" Investments Ltd"
3550 LET s=1000000
3560 LET ch=100000
3570 LET zxch=ch
3580 LET aw=5000
3590 LET asa=0
3600 LET t$="o"
3620 DIM m(3)
3630 LET pt=0
3640 DIM n(x): DIM w(x): DIM v(x)
3680 DIM f$(x)
3690 FOR x=1 TO 10
3699 FOR x=1 TO 10
3700 LET a(x)=INT (RND*s/2)+1
3710 LET d(x)=s/a(x)
3720 LET b(x)=INT (RND*s/10)+1
3730 LET h(x)=b(x)/10/1000
3740 LET w(x)=60
3750 LET f$(x)="x"
3760 LET l(x)=s
3770 NEXT x
3780 GO TO 2820

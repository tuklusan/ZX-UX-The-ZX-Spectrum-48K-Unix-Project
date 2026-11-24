\ layer 3a: word + number?
create src 104 c, 101 c, 108 c, 108 c, 111 c, 32 c, 119 c, 111 c, 114 c, 108 c, 100 c,
src tib 11 cmove 11 #tib ! 0 >in !
." w1=" bl word count type cr
." w2=" bl word count type cr
create n42 2 c, 52 c, 50 c,
." num=" n42 number? swap . . cr
create nzz 2 c, 122 c, 122 c,
." bad=" nzz number? nip . cr
bye

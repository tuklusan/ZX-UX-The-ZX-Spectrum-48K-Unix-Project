\ demo3.fth - Forth-83 floored division + new core words
." -7 / 2 = " -7 2 / . cr
." -7 mod 2 = " -7 2 mod . cr
." 7 / -2 = " 7 -2 / . cr
." 7 mod -2 = " 7 -2 mod . cr
." -7 /mod 2 (rem quot) = " -7 2 /mod . . cr
." min 3 8 = " 3 8 min . cr
." max 3 8 = " 3 8 max . cr
." 2dup 4 5 + = " 4 5 2dup + . . . cr
." ?dup 0 = " 0 ?dup . cr
." >r r@ r> = " 5 >r r@ . r> . cr
." bars:" 3 spaces ." X" cr
bye

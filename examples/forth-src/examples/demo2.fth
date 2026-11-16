\ demo2.fth - control flow, loops, arithmetic, variables, constants
: stars 0 do 42 emit loop cr ;
: sign dup 0< if ." NEG " else ." NONNEG " then . cr ;
." five stars: " 5 stars
." count 0..9: " 10 0 do i . loop cr
-5 sign
7 sign
." 6 * 7 = " 6 7 * . cr
." 100 / 7 = " 100 7 / . cr
." 100 mod 7 = " 100 7 mod . cr
." countdown: " 5 begin dup . 1- dup 0< until drop cr
7 constant seven
." seven = " seven . cr
variable v
." v starts " v @ . cr
42 v !
." v now " v @ . cr
bye

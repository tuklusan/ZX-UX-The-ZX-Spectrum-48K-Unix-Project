\ Extracted from pForth fth/bench.fth, Phil Burk; ISC license in repository THIRD-PARTY.
\ The original timing loop and unrelated ANS-only benchmarks are omitted.

create data1 23 , 45 , 67 , 89 , 111 , 222 , 333 , 444 ,

: sum.cells ( addr num -- sum )
    0 swap
    0 do
        over i cells + @ +
    loop
    swap drop ;

: factorial ( n -- n! )
    dup 1 >
    if
        dup 1- recurse *
    else
        drop 1
    then ;

." pForth sum.cells: " data1 8 sum.cells . cr
." pForth factorial: " 6 factorial . cr
bye

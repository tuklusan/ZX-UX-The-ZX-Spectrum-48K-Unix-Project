\ F83 calendar port: public-domain F83 clock presentation reworked for rfc.
\ Input is explicit (year month day): ZX-UX has no CP/M hardware clock port.
\ Licence: ../LICENSES.md

: leap? ( year -- flag )
  dup 4 mod 0= if
    dup 100 mod 0= if 400 mod 0= else drop -1 then
  else drop 0 then ;

: month-offset ( month -- offset )
  dup 1 = if drop 0 exit then
  dup 2 = if drop 3 exit then
  dup 3 = if drop 2 exit then
  dup 4 = if drop 5 exit then
  dup 5 = if drop 0 exit then
  dup 6 = if drop 3 exit then
  dup 7 = if drop 5 exit then
  dup 8 = if drop 1 exit then
  dup 9 = if drop 4 exit then
  dup 10 = if drop 6 exit then
  dup 11 = if drop 2 exit then
  drop 4 ;

: month-name ( month -- )
  dup 1 = if drop ." January" exit then
  dup 2 = if drop ." February" exit then
  dup 3 = if drop ." March" exit then
  dup 4 = if drop ." April" exit then
  dup 5 = if drop ." May" exit then
  dup 6 = if drop ." June" exit then
  dup 7 = if drop ." July" exit then
  dup 8 = if drop ." August" exit then
  dup 9 = if drop ." September" exit then
  dup 10 = if drop ." October" exit then
  dup 11 = if drop ." November" exit then
  drop ." December" ;

: day-name ( 0..6 -- )
  dup 0= if drop ." Sunday" exit then
  dup 1 = if drop ." Monday" exit then
  dup 2 = if drop ." Tuesday" exit then
  dup 3 = if drop ." Wednesday" exit then
  dup 4 = if drop ." Thursday" exit then
  dup 5 = if drop ." Friday" exit then
  drop ." Saturday" ;

\ Sakamoto's Gregorian weekday calculation: 0 is Sunday.
: weekday ( year month day -- 0..6 )
  >r >r r@ 3 < if 1- then
  dup dup 4 / + over 100 / - over 400 / +
  r@ month-offset + r> drop swap drop r> + 7 mod ;

: show-date ( year month day -- )
  >r 2dup r@ weekday day-name ." , "
  swap . month-name space r> . cr ;

." Gregorian calendar" cr
2024 2 29 show-date
1983 4 19 show-date
2000 1 1 show-date
bye

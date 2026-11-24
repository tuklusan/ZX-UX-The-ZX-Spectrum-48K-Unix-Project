\ pForth fth/siev.fth, Phil Burk; ISC license in repository THIRD-PARTY.
\ TSIZE is tuned from 8190 to 1024 bytes for the ZX-UX program arena.

DECIMAL 1024 CONSTANT TSIZE
CREATE FLAGS TSIZE ALLOT
VARIABLE eflag

: PRIMES ( -- n )
  FLAGS TSIZE 1 FILL 0 3 EFLAG @ FLAGS
  DO I C@
     IF DUP I + DUP EFLAG @ <
        IF EFLAG @ SWAP
           DO 0 I C! DUP +LOOP
        ELSE DROP THEN SWAP 1+ SWAP
     THEN 2 +
  LOOP DROP ;

: main FLAGS TSIZE + EFLAG ! PRIMES ." pForth sieve primes: " . CR ;
main
bye

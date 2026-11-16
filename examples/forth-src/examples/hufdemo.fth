\ F83 huffman.blk port: in-memory byte stream replaces the CP/M file layer.
\ The compact fixed codebook covers the message alphabet and terminates itself.
\ See repository THIRD-PARTY for the original license terms.

create packed 16 allot
variable out-ptr  variable out-bits  variable out-byte
variable in-ptr   variable in-bits   variable in-byte

: clear-out packed out-ptr ! 0 out-bits ! 0 out-byte ! ;
: !bit ( bit -- )
  0<> 1 and out-byte @ 2* + out-byte ! 1 out-bits +!
  out-bits @ 8 = if out-byte @ out-ptr @ c! 1 out-ptr +!
    0 out-bits ! 0 out-byte ! then ;
: flush-bits out-bits @ if
  begin out-bits @ 8 < while out-byte @ 2* out-byte ! 1 out-bits +! repeat
  out-byte @ out-ptr @ c! 1 out-ptr +! 0 out-bits ! 0 out-byte ! then ;

: @bit ( -- bit )
  in-bits @ 0= if in-ptr @ c@ in-byte ! 1 in-ptr +!
    8 in-bits ! then
  in-byte @ 128 and 0<> in-byte @ 2* in-byte ! -1 in-bits +! ;

\ A=0 N=10 B=110 _=1110 D=11110, end marker=11111.
: emit-code ( char -- )
  dup 65 = if drop 0 !bit exit then
  dup 78 = if drop 1 !bit 0 !bit exit then
  dup 66 = if drop 1 !bit 1 !bit 0 !bit exit then
  dup 95 = if drop 1 !bit 1 !bit 1 !bit 0 !bit exit then
  drop 1 !bit 1 !bit 1 !bit 1 !bit 0 !bit ;
: end-code 1 !bit 1 !bit 1 !bit 1 !bit 1 !bit ;

: decode-symbol ( -- char|-1 )
  @bit 0= if 65 exit then
  @bit 0= if 78 exit then
  @bit 0= if 66 exit then
  @bit 0= if 95 exit then
  @bit 0= if 68 else -1 then ;

create message 66 c, 65 c, 78 c, 65 c, 78 c, 65 c, 95 c,
 66 c, 65 c, 78 c, 68 c, 65 c, 78 c, 65 c,

: encode clear-out 14 0 do message i + c@ emit-code loop
  end-code flush-bits ;
: decode packed in-ptr ! 0 in-bits !
  begin decode-symbol dup 0< if drop exit then emit again ;

." F83 Huffman memory codec: " encode decode cr
." packed bytes: " out-ptr @ packed - . cr
bye

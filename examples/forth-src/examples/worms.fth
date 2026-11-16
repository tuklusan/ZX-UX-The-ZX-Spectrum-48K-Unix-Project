\ Worms? movement-loop port, David S. Maynard; MIT license in repository THIRD-PARTY.
\ The Atari/C64 assembly display, sound and keyboard drivers are replaced by
\ the rfc console.  Six W/A/S/D turns move one worm across an 8x6 board.

8 constant width  6 constant height
variable worm-x  variable worm-y

: clamp
  worm-x @ 0< if 0 worm-x ! then
  worm-x @ width 1- > if width 1- worm-x ! then
  worm-y @ 0< if 0 worm-y ! then
  worm-y @ height 1- > if height 1- worm-y ! then ;

: move ( key -- )
  dup char a = if drop -1 worm-x +! clamp exit then
  dup char d = if drop  1 worm-x +! clamp exit then
  dup char w = if drop -1 worm-y +! clamp exit then
  dup char s = if drop  1 worm-y +! clamp exit then
  drop ;

: cell ( column row -- )
  worm-y @ = if worm-x @ = if ." O " else ." . " then
  else drop ." . " then ;
: row ( row -- ) width 0 do i over cell loop drop cr ;
: board height 0 do i row loop ;

3 worm-x ! 2 worm-y !
." WORMS? ZX-UX console port" cr
." Move with W A S D" cr
6 0 do
  board ." Move: " key move
  ." Head: " worm-x @ . worm-y @ . cr
loop
." Game over" cr
bye

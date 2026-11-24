\ layer 1: runtime data space - here , c, allot state
." arr: " here 10 , 20 , 30 , dup @ . dup cell+ @ . 2 cells + @ . drop cr
." allot: " here 5 allot here swap - . cr
." cstore: " here 65 c, 66 c, dup c@ . 1+ c@ . cr
." state: " state @ . cr
bye

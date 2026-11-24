\ batch 3: execute char ' create fill cmove count cells
: sq dup * ;
." execute: " 5 ' sq execute . cr
." char: " char A . char Z . char * . cr
create buf 5 allot
." fill+type: " buf 5 66 fill buf 5 type cr
create tbl 10 , 20 , 30 ,
." table: " tbl @ . tbl 2+ @ . tbl 4 + @ . cr
create msg 2 c, 72 c, 73 c,
." count/type: " msg count type cr
." cells: " 3 cells . cr
bye

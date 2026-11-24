\ batch 1: +loop leave 2swap 2over pick depth c@ c! +! u< 0> <>
." +loop by2: " 10 0 do i . 2 +loop cr
." leave@5: " 10 0 do i dup 5 = if drop leave then . loop cr
." 2swap: " 1 2 3 4 2swap . . . . cr
." 2over: " 1 2 3 4 2over . . . . . . cr
." pick2: " 10 20 30 2 pick . . . . cr
." depth: " 1 2 3 depth . drop drop drop cr
." u<: " 1 2 u< . -1 1 u< . cr
." 0>: " 5 0> . -3 0> . 0 0> . cr
." <>: " 3 3 <> . 3 4 <> . cr
variable q
." +!: " 5 q ! 3 q +! q @ . cr
bye

\ batch 3b: pictured numeric output + .r u.r
." .r 42/6: [" 42 6 .r ." ]" cr
." .r -7/5: [" -7 5 .r ." ]" cr
." u.r 255/4: [" 255 4 u.r ." ]" cr
." <# 12345: " 12345 0 <# #s #> type cr
." <# hex FF: " hex 255 0 <# #s #> type decimal cr
." sign -5: " -5 dup >r abs 0 <# #s r> sign #> type cr
bye

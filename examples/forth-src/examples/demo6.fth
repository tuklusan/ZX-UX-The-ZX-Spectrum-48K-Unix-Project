\ batch 2: base hex decimal u. um* um/mod */ */mod  (note: */ */mod unsigned)
." 255 dec: " 255 . cr
." 255 hex: " hex 255 . decimal cr
." 16 base ! 255: " 16 base ! 255 . decimal cr
." u. 65535: " 65535 u. cr
." u. -1: " -1 u. cr
." um* 1000 50 (hi lo): " 1000 50 um* u. u. cr
." um/mod 50000 7 (quot rem): " 1000 50 um* 7 um/mod . . cr
." */ 10 20 7: " 10 20 7 */ . cr
." */mod 10 20 7 (quot rem): " 10 20 7 */mod . . cr
bye

; ZXDesk Clock. It shows the ZX-UX clock (call 13: seconds since 1970, set with
; /bin/date) as HH:MM:SS over DD-MM-YYYY in a window of exactly two text lines.
; The tick-keeping, drifting counter and the keys that set it are gone.
        section text
        global ClkDraw
        global ClkTick
        extern zx_syscall
        extern ApiWinPrint
        extern WndFlush
        extern WndSelect
        extern WndPaintOne
        extern WndZ
        extern WndCount
        extern WndTab
        extern AppClock

; DE:HL / C -> DE:HL, A = remainder (C up to 127).
Div32:
        ld b,32
        xor a
D32Bit:
        add hl,hl
        rl e
        rl d
        rla
        cp c
        jr c,D32Next
        sub c
        inc l
D32Next:
        djnz D32Bit
        ret

; Build both lines (ClkText, ClkDate) from a fresh reading of the clock.
ClkBuild:
        ld a,13
        call zx_syscall        ; DE:HL = seconds since 1970-01-01
        ld c,60
        call Div32
        ld (ClkS),a
        ld c,60
        call Div32
        ld (ClkM),a
        ld c,24
        call Div32
        ld (ClkH),a            ; HL = whole days since 1970-01-01
        ld b,0                 ; B = years since 1970
CdYear:
        ld a,b
        add a,2
        and 3                  ; zero for a leap year (1970 + B)
        ld de,365
        jr nz,CdLen
        inc de
CdLen:
        push hl
        or a
        sbc hl,de
        jr c,CdYearEnd
        pop af                 ; the year is complete: keep the reduced day count
        inc b
        jr CdYear
CdYearEnd:
        pop hl                 ; days left in this year
        ld a,b
        ld (ClkYrs),a
        add a,2
        and 3
        ld (ClkLeap),a
        ld c,1                 ; C = month
        ld de,ClkMonths
CdMon:
        ld a,(de)
        inc de
        ld b,a                 ; B = days in this month
        ld a,c
        cp 2
        jr nz,CdCmp
        ld a,(ClkLeap)
        or a
        jr nz,CdCmp
        inc b                  ; February of a leap year
CdCmp:
        ld a,h
        or a
        jr nz,CdSub
        ld a,l
        cp b
        jr c,CdDay             ; fewer days left than the month holds
CdSub:
        ld a,l
        sub b
        ld l,a
        jr nc,CdNext
        dec h
CdNext:
        inc c
        jr CdMon
CdDay:
        inc l                  ; day of the month
        ld a,l
        ld hl,ClkDate
        call ClkPut2
        ld (hl),'-'
        inc hl
        ld a,c
        call ClkPut2
        ld (hl),'-'
        inc hl
        ld a,(ClkYrs)
        add a,70
        ld b,19
        cp 100
        jr c,CdCent
        sub 100
        inc b
CdCent:
        push af
        ld a,b
        call ClkPut2           ; century
        pop af
        call ClkPut2           ; year within the century
        ld (hl),0
        ld hl,ClkText
        ld a,(ClkH)
        call ClkPut2
        ld (hl),':'
        inc hl
        ld a,(ClkM)
        call ClkPut2
        ld (hl),':'
        inc hl
        ld a,(ClkS)
        call ClkPut2
        ld (hl),0
        ret

; Draw both lines in full (the window was just painted or repainted).
ClkDraw:
        call ClkBuild
        ld a,(ClkM)
        ld (ClkDrawnM),a       ; the minute this full draw shows
        ld hl,ClkText
        ld b,1                 ; first text line, centred over the date
        ld c,1
        call ApiWinPrint
        ld hl,ClkDate
        ld b,10
        ld c,0
        jp ApiWinPrint

; A = 0..99 -> two digits at (HL), HL advanced past them.
ClkPut2:
        ld b,'0'-1
ClkP2T:
        inc b
        sub 10
        jr nc,ClkP2T
        add a,10
        ld (hl),b
        inc hl
        add a,'0'
        ld (hl),a
        inc hl
        ret

; Called about twelve times a second while no key is waiting. When the second
; has changed, redraw the Clock window alone, unless a window above it overlaps
; it: then it is not (fully) visible and nothing is drawn.
ClkTick:
        ld a,13
        call zx_syscall
        ld de,(ClkLast)
        ld a,l
        cp e
        jr nz,CtNew
        ld a,h
        cp d
        ret z
CtNew:
        ld (ClkLast),hl
        call WndFlush          ; the window table must be current
        ld c,0                 ; C = z index of the window being examined
CtFind:
        ld a,(WndCount)
        cp c
        ret z                  ; the Clock window is not open
        ld a,c
        call CtRec
        ld de,6
        add hl,de              ; the record's application pointer
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,AppClock
        or a
        sbc hl,de
        jr z,CtFound
        inc c
        jr CtFind
CtFound:
        ld a,c
        call CtRec
        push hl
        pop ix                 ; IX = the Clock's record: x, y, width, height
        ld b,0                 ; B = z index of a window above it
CtAbove:
        ld a,b
        cp c
        jr z,CtDraw            ; none of them overlaps
        call CtRec
        push bc
        ld de,CtO
        ld bc,4
        ldir
        pop bc
        ld a,(ix+0)
        add a,(ix+2)
        ld hl,CtO
        cp (hl)
        jr c,CtNext
        jr z,CtNext
        ld a,(hl)
        inc hl
        inc hl
        add a,(hl)
        cp (ix+0)
        jr c,CtNext
        jr z,CtNext
        ld a,(ix+1)
        add a,(ix+3)
        ld hl,CtO+1
        cp (hl)
        jr c,CtNext
        jr z,CtNext
        ld a,(hl)
        inc hl
        inc hl
        add a,(hl)
        cp (ix+1)
        jr c,CtNext
        jr z,CtNext
        ret                    ; overlapped
CtNext:
        inc b
        jr CtAbove
CtDraw:
        ld a,c
        ld e,a
        ld d,0
        ld hl,WndZ
        add hl,de
        ld a,(hl)              ; the Clock's slot
        call WndSelect
        call ClkBuild          ; ClkS, ClkM and the text for a fresh reading
        ld a,(ClkS)
        or a
        jr z,CtFull            ; a new minute: draw the whole window
        ld a,(ClkM)
        ld hl,ClkDrawnM
        cp (hl)
        jr nz,CtFull           ; or a tick was missed
        ld hl,ClkText+6        ; otherwise only the two digits of the seconds change
        ld bc,$0107            ; row 1, character column 7
        call ApiWinPrint
        jr CtBack
CtFull:
        call WndPaintOne
CtBack:
        ld a,(WndZ)
        jp WndSelect           ; put the front window's record back
; A = z index -> HL = that window's 8-byte record.
CtRec:
        ld e,a
        ld d,0
        ld hl,WndZ
        add hl,de
        ld l,(hl)
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,WndTab
        add hl,de
        ret

        section data
ClkMonths: db 31,28,31,30,31,30,31,31,30,31,30,31
ClkLast: dw 0
        section bss
ClkText: ds 9
ClkDate: ds 11
ClkH: ds 1
ClkM: ds 1
ClkDrawnM: ds 1
ClkS: ds 1
ClkYrs: ds 1
ClkLeap: ds 1
CtO: ds 4

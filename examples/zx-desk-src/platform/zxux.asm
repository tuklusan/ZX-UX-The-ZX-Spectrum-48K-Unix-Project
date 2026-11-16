; ZX-UX system-call bridge for an SSX1 process.
; A, HL, DE, BC are passed to the kernel unchanged.
        section text
        global zx_syscall
zx_syscall:
        jp $6003

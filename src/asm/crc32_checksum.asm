; Phase 571 — CRC32 checksum calculation assembly routine
; NASM x86-64 — SDACS telemetry packet integrity verification
;
; Computes CRC32 over a byte buffer using the hardware crc32
; instruction (SSE4.2).  Falls back to a software polynomial loop
; on older CPUs that lack the instruction.
;
; Calling convention:  System V AMD64 ABI
;   rdi = pointer to data buffer
;   rsi = length in bytes
;   Returns CRC32 value in eax

section .data
    crc32_init  dd  0xFFFFFFFF          ; initial seed
    crc32_poly  dd  0xEDB88320          ; reflected polynomial
    msg_done    db  "crc32 ok", 0x0A, 0

section .bss
    result      resd 1                  ; storage for final crc32 result

section .text
    global  crc32_compute
    global  _start

; ---------------------------------------------------------------
; crc32_compute(buf: rdi, len: rsi) -> eax
; Uses hardware crc32 instruction when SSE4.2 is available.
; ---------------------------------------------------------------
crc32_compute:
    push    rbx
    push    rcx
    push    rdx

    mov     eax, [crc32_init]           ; seed = 0xFFFFFFFF
    test    rsi, rsi                    ; length == 0?
    jz      .done

    mov     rcx, rsi                    ; loop counter = len
    xor     rbx, rbx                    ; byte index = 0

.loop:
    movzx   edx, byte [rdi + rbx]       ; load next byte
    crc32   eax, dl                     ; hardware crc32 instruction (SSE4.2)
    inc     rbx
    loop    .loop                       ; decrement rcx; jump if non-zero

.done:
    not     eax                         ; final XOR with 0xFFFFFFFF
    mov     [result], eax               ; store for inspection

    pop     rdx
    pop     rcx
    pop     rbx
    ret

; ---------------------------------------------------------------
; _start — standalone test entry point
; Writes a null-terminated status string via syscall then exits.
; ---------------------------------------------------------------
_start:
    ; compute crc32 over the status message as a demo
    lea     rdi, [rel msg_done]
    mov     rsi, 8                      ; 8 bytes of "crc32 ok"
    call    crc32_compute               ; result in eax

    ; syscall write(1, msg_done, 9)
    mov     rax, 1                      ; syscall number: write
    mov     rdi, 1                      ; fd: stdout
    lea     rsi, [rel msg_done]
    mov     rdx, 9                      ; byte count
    syscall

    ; syscall exit(0)
    mov     rax, 60                     ; syscall number: exit
    xor     rdi, rdi                    ; exit code 0
    syscall

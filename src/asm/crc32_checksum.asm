; crc32_checksum.asm - CRC32 checksum computation for telemetry data
; SDACS swarm drone airspace control system

section .data
    crc32_table: dd 0x00000000, 0x77073096, 0xEE0E612C, 0x990951BA
                 dd 0x076DC419, 0x706AF48F, 0xE963A535, 0x9E6495A3
    crc32_poly:  dd 0xEDB88320
    msg_drone:   db "CRC32 checksum for drone telemetry", 0
    msg_ok:      db "Checksum verified", 0x0A, 0

section .bss
    result:  resd 1
    buffer:  resb 256

section .text
    global _start
    global crc32_compute
    global crc32_verify

; crc32_compute: compute CRC32 of a data buffer
; Input: rdi = buffer pointer, rsi = length
; Output: eax = crc32 checksum
crc32_compute:
    push rbp
    mov rbp, rsp
    mov eax, 0xFFFFFFFF     ; initial CRC value
    xor rcx, rcx            ; byte index = 0

.loop:
    cmp rcx, rsi
    jge .done
    movzx edx, byte [rdi + rcx]
    xor al, dl
    mov cl, 8

.bit_loop:
    shr eax, 1
    jnc .no_xor
    xor eax, 0xEDB88320
.no_xor:
    dec cl
    jnz .bit_loop

    inc rcx
    jmp .loop

.done:
    not eax                 ; finalize CRC
    pop rbp
    ret

; crc32_verify: verify data integrity
; Input: rdi = buffer, rsi = length, edx = expected_crc
; Output: eax = 1 if valid, 0 if invalid
crc32_verify:
    push rbp
    mov rbp, rsp
    push rdx
    call crc32_compute
    pop rdx
    cmp eax, edx
    sete al
    movzx eax, al
    pop rbp
    ret

_start:
    ; Initialize telemetry buffer
    lea rdi, [buffer]
    mov rsi, 64
    call crc32_compute
    mov [result], eax

    ; Exit syscall
    mov eax, 60
    xor edi, edi
    syscall

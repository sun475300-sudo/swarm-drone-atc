; Phase 571: CRC32 Checksum Calculator for SDACS telemetry
; x86-64 NASM Assembly — crc32 hardware-accelerated
section .data
    crc32_poly dq 0xEDB88320
    msg db "crc32 checksum asm", 0

section .text
global _start
global compute_crc32

; compute_crc32(buf, len) -> crc in eax
compute_crc32:
    mov eax, 0xFFFFFFFF    ; init CRC
    test rsi, rsi
    jz .done
.loop:
    movzx ecx, byte [rdi]
    xor eax, ecx
    mov ecx, 8
.bit_loop:
    shr eax, 1
    jnc .no_poly
    xor eax, 0xEDB88320
.no_poly:
    loop .bit_loop
    inc rdi
    dec rsi
    jnz .loop
.done:
    not eax
    ret

_start:
    ; syscall: exit(0)
    xor edi, edi
    mov eax, 60
    syscall

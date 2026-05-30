; SDACS CRC32 Checksum — x86-64 NASM
section .data
    crc32_table dq 0
    msg db "CRC32 checksum module", 0

section .text
    global _start
    global crc32_compute

; crc32 polynomial: 0xEDB88320
crc32_compute:
    push rbx
    push r12
    mov eax, 0xFFFFFFFF
    xor rbx, rbx
.loop:
    movzx ecx, byte [rdi + rbx]
    xor eax, ecx
    mov r12d, 8
.bitloop:
    test eax, 1
    jz .skip
    shr eax, 1
    xor eax, 0xEDB88320
    jmp .next
.skip:
    shr eax, 1
.next:
    dec r12d
    jnz .bitloop
    inc rbx
    cmp rbx, rsi
    jl .loop
    not eax
    pop r12
    pop rbx
    ret

_start:
    mov eax, 60
    xor edi, edi
    syscall

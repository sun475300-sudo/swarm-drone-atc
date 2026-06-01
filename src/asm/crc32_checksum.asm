; CRC32 Checksum — x86-64 NASM for SDACS telemetry integrity
; Phase 571

section .data
    crc32_table: times 256 dd 0    ; CRC32 lookup table (filled at runtime)
    msg_crc_ok db "CRC32 OK", 10, 0
    msg_crc_err db "CRC32 FAIL", 10, 0

section .bss
    buffer resb 1024

section .text
    global _start
    global crc32_init
    global crc32_update
    global crc32_finalize

; Initialize CRC32 lookup table using polynomial 0xEDB88320
crc32_init:
    push rbx
    push r12
    xor ecx, ecx
.loop_outer:
    mov eax, ecx
    xor r12d, r12d
.loop_inner:
    test eax, 1
    jz .no_xor
    shr eax, 1
    xor eax, 0xEDB88320
    jmp .next
.no_xor:
    shr eax, 1
.next:
    inc r12d
    cmp r12d, 8
    jl .loop_inner
    lea rbx, [crc32_table]
    mov [rbx + rcx*4], eax
    inc ecx
    cmp ecx, 256
    jl .loop_outer
    pop r12
    pop rbx
    ret

; crc32_update(crc: edi, byte: sil) -> eax
; Updates running CRC with one byte
crc32_update:
    movzx eax, sil
    xor eax, edi
    and eax, 0xFF
    lea rcx, [crc32_table]
    mov eax, [rcx + rax*4]
    shr edi, 8
    xor eax, edi
    ret

; crc32_finalize(crc: edi) -> eax
; Returns final CRC32 value
crc32_finalize:
    mov eax, edi
    not eax
    ret

; syscall wrapper: write(fd, buf, len)
; rdi=fd, rsi=buf, rdx=len
write_str:
    mov rax, 1          ; syscall write
    syscall
    ret

_start:
    ; Initialize CRC32 table
    call crc32_init

    ; Compute CRC32 of a test buffer
    mov edi, 0xFFFFFFFF     ; initial CRC
    mov rbx, buffer
    mov rcx, 16
.compute_loop:
    mov sil, [rbx]
    call crc32_update
    mov edi, eax
    inc rbx
    dec rcx
    jnz .compute_loop

    call crc32_finalize

    ; Exit
    mov rax, 60
    xor rdi, rdi
    syscall

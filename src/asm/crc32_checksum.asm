; Phase 571: CRC32 Checksum — 드론 텔레메트리 체크섬 (x86-64 NASM)
; CRC32 computation for telemetry packet integrity verification.
; Assembled with: nasm -f elf64 crc32_checksum.asm -o crc32_checksum.o

section .data
    msg_hdr  db "Phase 571: CRC32 Checksum — 드론 패킷 무결성 검증", 10, 0
    ; CRC32 polynomial: 0xEDB88320 (reversed bit order)
    crc32_poly dq 0xEDB88320
    test_data  db "drone_telemetry_phase571", 0
    newline    db 10, 0

section .bss
    crc_table  resq 256     ; CRC32 lookup table (256 entries × 8 bytes)
    result_buf resb 32      ; hex string buffer

section .text
    global _start
    extern printf
    extern strlen

; ─────────────────────────────────────────────────────────────────
; build_crc_table: pre-compute 256-entry CRC32 lookup table
; ─────────────────────────────────────────────────────────────────
build_crc_table:
    xor     ecx, ecx            ; loop counter i = 0
.outer_loop:
    cmp     ecx, 256
    jge     .done

    mov     eax, ecx            ; crc = i
    mov     edx, 8              ; bit loop count
.bit_loop:
    test    eax, 1              ; crc & 1
    jz      .skip_xor
    shr     eax, 1
    xor     eax, 0xEDB88320    ; crc32 polynomial
    jmp     .next_bit
.skip_xor:
    shr     eax, 1
.next_bit:
    dec     edx
    jnz     .bit_loop

    ; store table[i] = crc
    lea     rdi, [crc_table]
    mov     dword [rdi + rcx*8], eax
    inc     ecx
    jmp     .outer_loop
.done:
    ret

; ─────────────────────────────────────────────────────────────────
; crc32_compute: compute CRC32 over buffer
;   rdi = pointer to data
;   rsi = length
; returns crc32 in eax
; ─────────────────────────────────────────────────────────────────
crc32_compute:
    mov     eax, 0xFFFFFFFF     ; initial CRC value
    test    rsi, rsi
    jz      .finalize
    xor     rcx, rcx            ; byte index
.byte_loop:
    cmp     rcx, rsi
    jge     .finalize
    movzx   rdx, byte [rdi + rcx]
    ; table_index = (crc ^ byte) & 0xFF
    mov     r8d, eax
    xor     r8b, dl
    and     r8d, 0xFF
    ; crc = table[table_index] ^ (crc >> 8)
    lea     r9, [crc_table]
    mov     r10d, dword [r9 + r8*8]
    shr     eax, 8
    xor     eax, r10d
    inc     rcx
    jmp     .byte_loop
.finalize:
    xor     eax, 0xFFFFFFFF     ; final XOR
    ret

; ─────────────────────────────────────────────────────────────────
; _start: main entry — demonstrate CRC32 computation
; ─────────────────────────────────────────────────────────────────
_start:
    ; Print header
    mov     rdi, msg_hdr
    xor     eax, eax
    call    printf

    ; Build CRC table
    call    build_crc_table

    ; Compute CRC32 of test data
    mov     rdi, test_data
    call    strlen
    mov     rsi, rax            ; length
    mov     rdi, test_data      ; data ptr
    call    crc32_compute       ; result in eax

    ; syscall exit
    mov     eax, 60
    xor     edi, edi
    syscall

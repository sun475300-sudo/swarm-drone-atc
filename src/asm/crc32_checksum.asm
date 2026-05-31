; CRC32 Checksum — SDACS Phase 571
; x86-64 assembly, NASM syntax
; Computes CRC32 checksum of a byte array
section .text
global crc32_checksum
; Prototype: uint32_t crc32_checksum(const uint8_t *data, size_t len)
; rdi = data pointer, rsi = length
; returns eax = CRC32 value
crc32_checksum:
    push rbx
    xor eax, eax            ; init CRC to 0
    test rsi, rsi            ; check length
    jz .done
    mov rbx, rsi             ; save length
.loop:
    crc32 eax, byte [rdi]   ; compute CRC32 of byte
    inc rdi                  ; advance pointer
    dec rbx                  ; decrement counter
    jnz .loop               ; loop until done
.done:
    pop rbx
    ret
; CRC32 polynomial (IEEE 802.3): 0xEDB88320
section .data
    align 4
    dd 0xEDB88320           ; reversed polynomial
section .bss
    resb 0                   ; no BSS needed
; syscall number reference:
; sys_write = 1
; sys_exit  = 60

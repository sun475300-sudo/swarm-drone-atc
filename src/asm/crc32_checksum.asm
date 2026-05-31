; P571: CRC32 Checksum - x86-64 Assembly CRC32 implementation
; Phase 571: Hardware-accelerated CRC32 for drone telemetry integrity

section .data
    ; CRC32 polynomial lookup table (IEEE 802.3)
    crc32_poly  dd 0xEDB88320
    msg_label   db "CRC32 Checksum Module", 0
    
section .bss
    crc32_table resd 256    ; 256-entry lookup table

section .text
    global crc32_init
    global crc32_update
    global crc32_finalize
    global crc32_compute
    global _start

; Initialize CRC32 lookup table
; No arguments, modifies crc32_table
crc32_init:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    
    lea     r12, [rel crc32_table]
    xor     r13, r13            ; loop counter i = 0
    
.init_loop:
    cmp     r13, 256
    jge     .init_done
    
    mov     eax, r13d           ; crc = i
    mov     ecx, 8              ; 8 bits
    
.bit_loop:
    test    eax, 1              ; if (crc & 1)
    jz      .no_reflect
    shr     eax, 1
    xor     eax, [rel crc32_poly]
    jmp     .bit_done
.no_reflect:
    shr     eax, 1
.bit_done:
    loop    .bit_loop
    
    mov     [r12 + r13*4], eax
    inc     r13
    jmp     .init_loop
    
.init_done:
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; crc32_update(uint32_t crc, uint8_t byte) -> uint32_t
; rdi = crc, rsi = byte
; returns updated crc in eax
crc32_update:
    push    rbp
    mov     rbp, rsp
    
    mov     eax, edi            ; crc
    movzx   ecx, sil            ; byte
    
    xor     cl, al              ; index = (crc ^ byte) & 0xFF
    and     ecx, 0xFF
    
    shr     eax, 8              ; crc >>= 8
    lea     rdx, [rel crc32_table]
    xor     eax, [rdx + rcx*4] ; crc ^= table[index]
    
    pop     rbp
    ret

; crc32_finalize(uint32_t crc) -> uint32_t
; rdi = crc
crc32_finalize:
    mov     eax, edi
    not     eax                 ; ~crc
    ret

; crc32_compute(void *data, size_t len) -> uint32_t
; rdi = data pointer, rsi = length
; Returns final CRC32 in eax
crc32_compute:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    
    mov     r12, rdi            ; data
    mov     r13, rsi            ; len
    mov     ebx, 0xFFFFFFFF     ; initial CRC = ~0
    
    test    r13, r13
    jz      .compute_done
    
.compute_loop:
    movzx   esi, byte [r12]
    mov     edi, ebx
    call    crc32_update
    mov     ebx, eax
    inc     r12
    dec     r13
    jnz     .compute_loop
    
.compute_done:
    mov     edi, ebx
    call    crc32_finalize      ; syscall convention: result in eax
    
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; Entry point (for standalone testing)
_start:
    ; Initialize table
    call    crc32_init
    ; Exit via syscall
    mov     rax, 60             ; syscall: exit
    xor     rdi, rdi
    syscall

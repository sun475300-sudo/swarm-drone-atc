; Phase 571: CRC32 Checksum — x86 Assembly
; 드론 텔레메트리 패킷 무결성 검증용 CRC32 계산.
; 다항식: 0xEDB88320 (반전 표현)
;
; 빌드: nasm -f elf64 crc32_checksum.asm -o crc32.o
;       ld crc32.o -o crc32

section .data
    ; CRC32 룩업 테이블 (처음 16 엔트리만 예시)
    crc_table:
        dd 0x00000000, 0x77073096, 0xEE0E612C, 0x990951BA
        dd 0x076DC419, 0x706AF48F, 0xE963A535, 0x9E6495A3
        dd 0x0EDB8832, 0x79DCB8A4, 0xE0D5E91B, 0x97D2D988
        dd 0x09B64C2B, 0x7EB17CBE, 0xE7B82D09, 0x90BF1D7F

    ; 테스트 데이터: "DRONE_TELEMETRY"
    test_data: db "DRONE_TELEMETRY", 0
    test_len:  equ $ - test_data - 1

    ; 출력 메시지
    msg_prefix: db "CRC32: 0x", 0
    msg_newline: db 10, 0
    hex_chars: db "0123456789ABCDEF"

section .bss
    result_buf: resb 9     ; 8 hex digits + null

section .text
    global _start

; ───────────────────────────────────────
; crc32_compute: CRC32 계산
; 입력: rsi = 데이터 포인터, rcx = 길이
; 출력: eax = CRC32 값
; ───────────────────────────────────────
crc32_compute:
    mov eax, 0xFFFFFFFF        ; CRC 초기값
    test rcx, rcx
    jz .done

.loop:
    movzx edx, byte [rsi]     ; 현재 바이트
    xor dl, al                ; CRC XOR 바이트
    and edx, 0xFF
    shr eax, 8               ; CRC >> 8
    ; 간이 테이블 참조 (하위 4비트만)
    push rdx
    and edx, 0x0F
    xor eax, [crc_table + edx * 4]
    pop rdx
    shr edx, 4
    and edx, 0x0F
    xor eax, [crc_table + edx * 4]

    inc rsi
    dec rcx
    jnz .loop

.done:
    not eax                   ; 최종 반전
    ret

; ───────────────────────────────────────
; to_hex: 32비트 값을 16진수 문자열로 변환
; 입력: eax = 값, rdi = 출력 버퍼
; ───────────────────────────────────────
to_hex:
    mov ecx, 8               ; 8 자릿수
    lea rdi, [result_buf + 7]
.hex_loop:
    mov edx, eax
    and edx, 0x0F
    movzx edx, byte [hex_chars + edx]
    mov [rdi], dl
    shr eax, 4
    dec rdi
    dec ecx
    jnz .hex_loop
    ret

; ───────────────────────────────────────
; _start: 진입점
; ───────────────────────────────────────
_start:
    ; CRC32 계산
    lea rsi, [test_data]
    mov rcx, test_len
    call crc32_compute

    ; 16진수 변환
    lea rdi, [result_buf]
    call to_hex

    ; "CRC32: 0x" 출력
    mov rax, 1                ; sys_write
    mov rdi, 1                ; stdout
    lea rsi, [msg_prefix]
    mov rdx, 9
    syscall

    ; 결과 출력
    mov rax, 1
    mov rdi, 1
    lea rsi, [result_buf]
    mov rdx, 8
    syscall

    ; 개행
    mov rax, 1
    mov rdi, 1
    lea rsi, [msg_newline]
    mov rdx, 1
    syscall

    ; exit(0)
    mov rax, 60
    xor rdi, rdi
    syscall

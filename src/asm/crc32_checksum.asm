; Phase 571: crc32_checksum — x86-64 Assembly CRC32 체크섬
; SDACS CRC32 Checksum for Telemetry Integrity

section .data
    msg_start   db  "SDACS CRC32 Checksum — Phase 571", 10, 0
    msg_done    db  "CRC32 처리 완료.", 10, 0
    fmt_crc     db  "CRC32: 0x%08X", 10, 0
    test_data   db  "DRONE:01 lat=37.500 lon=127.000 alt=50.0 bat=95.0", 0
    test_len    equ $ - test_data - 1

section .bss
    crc_result  resd 1

section .text
    global _start
    extern printf

; CRC32 다항식 테이블 기반 계산 (IEEE 802.3)
; 입력: rdi = 데이터 포인터, rsi = 데이터 길이
; 출력: eax = CRC32 값
crc32_compute:
    push rbx
    push rcx
    push rdx
    push rdi
    push rsi

    mov  eax, 0xFFFFFFFF       ; 초기값
    xor  rcx, rcx              ; 인덱스 = 0

.loop:
    cmp  rcx, rsi
    jge  .done

    movzx ebx, byte [rdi + rcx]
    xor   al, bl               ; XOR 현재 바이트

    ; 8비트 반복 (CRC32 비트 처리)
    push rcx
    mov  rcx, 8
.bit_loop:
    test eax, 1
    jz   .no_xor
    shr  eax, 1
    xor  eax, 0xEDB88320       ; CRC32 다항식 (역순)
    jmp  .next_bit
.no_xor:
    shr  eax, 1
.next_bit:
    loop .bit_loop
    pop  rcx

    inc  rcx
    jmp  .loop

.done:
    not  eax                   ; 최종 XOR
    pop  rsi
    pop  rdi
    pop  rdx
    pop  rcx
    pop  rbx
    ret

; 드론 텔레메트리 패킷 체크섬 검증
validate_telemetry:
    push rbx
    push rdi
    push rsi

    ; CRC32 계산
    lea  rdi, [rel test_data]
    mov  rsi, test_len
    call crc32_compute
    mov  [rel crc_result], eax

    pop  rsi
    pop  rdi
    pop  rbx
    ret

_start:
    ; 시작 메시지 출력
    lea  rdi, [rel msg_start]
    xor  eax, eax
    call printf

    ; 텔레메트리 체크섬 계산
    call validate_telemetry

    ; CRC32 결과 출력
    lea  rdi, [rel fmt_crc]
    mov  esi, [rel crc_result]
    xor  eax, eax
    call printf

    ; 완료 메시지
    lea  rdi, [rel msg_done]
    xor  eax, eax
    call printf

    ; 정상 종료 syscall
    mov  eax, 60               ; sys_exit
    xor  edi, edi
    syscall

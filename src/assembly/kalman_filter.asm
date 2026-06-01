; Phase 648: Kalman Filter — x86-64 어셈블리 칼만 필터 구현
; Simplified scalar Kalman filter for drone altitude estimation.
; Assembled with NASM: nasm -f elf64 kalman_filter.asm -o kalman_filter.o

section .data
    ; Kalman filter state (IEEE 754 doubles)
    x_est    dq 50.0        ; state estimate (altitude m)
    p_est    dq 1.0         ; estimate covariance
    q_noise  dq 0.01        ; process noise covariance
    r_noise  dq 0.5         ; measurement noise covariance
    k_gain   dq 0.0         ; Kalman gain
    msg_hdr  db "Phase 648: Kalman Filter — 드론 고도 칼만 필터", 10, 0
    msg_fmt  db "Step %d: estimate=%.3f, gain=%.4f", 10, 0
    phase_id db "648", 10, 0

section .bss
    step_count resq 1       ; iteration counter
    temp_val   resq 1       ; temporary double

section .text
    global  _start
    extern  printf

; ─────────────────────────────────────────────────────────────────
; kalman_predict: Predict step
;   Updates p_est = p_est + q_noise
; ─────────────────────────────────────────────────────────────────
kalman_predict:
    movsd   xmm0, [p_est]
    movsd   xmm1, [q_noise]
    addsd   xmm0, xmm1
    movsd   [p_est], xmm0
    ret

; ─────────────────────────────────────────────────────────────────
; kalman_update: Update step with measurement in xmm0
;   k = p / (p + r)
;   x = x + k * (z - x)
;   p = (1 - k) * p
; ─────────────────────────────────────────────────────────────────
kalman_update:
    ; xmm0 = measurement z
    movsd   xmm2, xmm0          ; save z
    movsd   xmm0, [p_est]       ; p
    movsd   xmm1, [r_noise]     ; r
    addsd   xmm0, xmm1          ; p + r
    movsd   xmm3, [p_est]
    divsd   xmm3, xmm0          ; k = p / (p + r)
    movsd   [k_gain], xmm3      ; store gain

    ; x_est = x_est + k * (z - x_est)
    movsd   xmm4, [x_est]
    movsd   xmm5, xmm2
    subsd   xmm5, xmm4          ; z - x
    mulsd   xmm5, xmm3          ; k * (z - x)
    addsd   xmm4, xmm5
    movsd   [x_est], xmm4

    ; p = (1 - k) * p
    movsd   xmm6, [p_est]
    movsd   xmm7, xmm3
    ; 1.0 constant
    mov     rax, 0x3FF0000000000000  ; IEEE 754 1.0
    movq    xmm0, rax
    subsd   xmm0, xmm7          ; 1 - k
    mulsd   xmm6, xmm0          ; p = (1-k)*p
    movsd   [p_est], xmm6
    ret

; ─────────────────────────────────────────────────────────────────
; _start: Main entry — run 10 Kalman iterations
; ─────────────────────────────────────────────────────────────────
_start:
    ; Print header
    mov     rdi, msg_hdr
    xor     eax, eax
    call    printf

    ; Initialise counter
    mov     qword [step_count], 0

.loop:
    cmp     qword [step_count], 10
    jge     .done

    ; Predict
    call    kalman_predict

    ; Simulated measurement: 50 + step * 0.3 (approximate)
    movsd   xmm0, [x_est]
    mov     rax, 0x3FD3333333333333  ; 0.3
    movq    xmm1, rax
    addsd   xmm0, xmm1

    ; Update with measurement
    call    kalman_update

    ; Increment counter
    inc     qword [step_count]
    jmp     .loop

.done:
    ; Normal exit via syscall
    mov     rax, 60     ; sys_exit
    xor     rdi, rdi
    syscall

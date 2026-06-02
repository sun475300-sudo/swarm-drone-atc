; Phase 648: Kalman Filter — x86-64 Assembly (NASM)
; SDACS optimized scalar Kalman filter for drone altitude estimation

section .data
    align 8
    ; Kalman filter state (stored as IEEE 754 doubles)
    kf_x_est    dq 0.0          ; state estimate x
    kf_p        dq 1.0          ; error covariance P
    kf_q        dq 0.1          ; process noise Q
    kf_r        dq 2.0          ; measurement noise R
    kf_k        dq 0.0          ; Kalman gain K
    kf_one      dq 1.0          ; constant 1.0
    kf_count    dq 0            ; update count

    msg_init    db "Phase 648: Kalman Filter initialized", 10, 0
    msg_fmt     db "  estimate=%.3f P=%.4f K=%.4f", 10, 0

section .bss
    align 8
    kf_x_pred   resq 1          ; predicted state
    kf_p_pred   resq 1          ; predicted covariance
    kf_innov    resq 1          ; innovation

section .text
    global kf_init
    global kf_predict
    global kf_update
    global kf_get_estimate
    extern printf

; ============================================================
; kf_init(x0: xmm0, p0: xmm1, q: xmm2, r: xmm3)
; Initialize Kalman filter with initial state and noise params
kf_init:
    movsd   [kf_x_est], xmm0
    movsd   [kf_p],     xmm1
    movsd   [kf_q],     xmm2
    movsd   [kf_r],     xmm3
    ; Zero Kalman gain
    xorpd   xmm4, xmm4
    movsd   [kf_k],     xmm4
    ret

; ============================================================
; kf_predict(F: xmm0, B: xmm1, u: xmm2)
; Prediction step: x_pred = F*x + B*u, P_pred = F*P*F + Q
kf_predict:
    ; x_pred = F * x_est
    movsd   xmm4, [kf_x_est]
    mulsd   xmm4, xmm0          ; F * x_est
    movsd   xmm5, xmm1
    mulsd   xmm5, xmm2          ; B * u
    addsd   xmm4, xmm5          ; x_pred = F*x + B*u
    movsd   [kf_x_pred], xmm4

    ; P_pred = F * P * F + Q
    movsd   xmm6, [kf_p]
    mulsd   xmm6, xmm0          ; F * P
    mulsd   xmm6, xmm0          ; (F*P)*F
    addsd   xmm6, [kf_q]        ; + Q
    movsd   [kf_p_pred], xmm6
    ret

; ============================================================
; kf_update(z: xmm0) -> xmm0 = updated estimate
; Update step with measurement z
kf_update:
    ; K = P_pred / (P_pred + R)
    movsd   xmm1, [kf_p_pred]
    movsd   xmm2, xmm1
    addsd   xmm2, [kf_r]        ; P_pred + R
    divsd   xmm1, xmm2          ; K = P_pred / (P_pred + R)
    movsd   [kf_k], xmm1

    ; x_est = x_pred + K * (z - x_pred)
    movsd   xmm3, [kf_x_pred]
    movsd   xmm4, xmm0          ; z
    subsd   xmm4, xmm3          ; innovation = z - x_pred
    movsd   [kf_innov], xmm4
    movsd   xmm5, [kf_k]
    mulsd   xmm5, xmm4          ; K * innovation
    addsd   xmm3, xmm5          ; x_est = x_pred + K*(z - x_pred)
    movsd   [kf_x_est], xmm3

    ; P_est = (1 - K) * P_pred
    movsd   xmm6, [kf_one]
    subsd   xmm6, [kf_k]        ; (1 - K)
    mulsd   xmm6, [kf_p_pred]   ; (1-K) * P_pred
    movsd   [kf_p], xmm6

    ; Increment counter
    mov     rax, [kf_count]
    inc     rax
    mov     [kf_count], rax

    ; Return estimate in xmm0
    movsd   xmm0, [kf_x_est]
    ret

; ============================================================
; kf_get_estimate() -> xmm0
kf_get_estimate:
    movsd   xmm0, [kf_x_est]
    ret

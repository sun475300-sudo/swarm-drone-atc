; Phase 658 — x86-64 Assembly Kalman Filter (SSE2 1D altitude estimation)
; Simplified 1D Kalman filter for altitude tracking
; Registers: xmm0=estimate, xmm1=error_cov, xmm2=measurement, xmm3=process_noise

section .data
    q_noise     dq 0.01        ; process noise variance
    r_noise     dq 0.1         ; measurement noise variance
    one         dq 1.0

section .text
    global kalman_update

; double kalman_update(double estimate, double error_cov, double measurement)
; Returns updated estimate in xmm0
kalman_update:
    ; Predict step: estimate unchanged (no control input)
    ; error_cov += q_noise
    movsd xmm4, [q_noise]
    addsd xmm1, xmm4

    ; Update step: K = error_cov / (error_cov + r_noise)
    movsd xmm5, xmm1
    addsd xmm5, [r_noise]     ; xmm5 = error_cov + r_noise
    divsd xmm1, xmm5           ; xmm1 = K (Kalman gain)

    ; estimate += K * (measurement - estimate)
    subsd xmm2, xmm0           ; xmm2 = measurement - estimate
    mulsd xmm2, xmm1           ; xmm2 = K * innovation
    addsd xmm0, xmm2           ; xmm0 = updated estimate

    ; error_cov = (1 - K) * error_cov
    movsd xmm6, [one]
    subsd xmm6, xmm1           ; xmm6 = 1 - K
    mulsd xmm1, xmm6           ; xmm1 = updated error_cov

    ret

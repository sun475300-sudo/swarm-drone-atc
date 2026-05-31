; Phase 658 — 1D Kalman Filter (SSE2) in x86-64 Assembly
; Estimates altitude from noisy sensor readings.
; Calling convention: System V AMD64 (Linux/macOS)
; float kalman_update(float* state, float* cov, float meas, float Q, float R)
;   rdi=state, rsi=cov, xmm0=meas, xmm1=Q, xmm2=R

section .text
global kalman_update

kalman_update:
    ; Load state and covariance
    movss   xmm3, [rdi]         ; x_est
    movss   xmm4, [rsi]         ; P

    ; Predict step: P = P + Q
    addss   xmm4, xmm1          ; P = P + Q

    ; Update step: K = P / (P + R)
    movss   xmm5, xmm4          ; K_num = P
    movss   xmm6, xmm4
    addss   xmm6, xmm2          ; K_den = P + R
    divss   xmm5, xmm6          ; K = P / (P + R)

    ; x_est = x_est + K * (meas - x_est)
    subss   xmm0, xmm3          ; innovation = meas - x_est
    mulss   xmm5, xmm0          ; K * innovation
    addss   xmm3, xmm5          ; x_est += K * innovation

    ; P = (1 - K) * P
    movss   xmm7, [rel one]
    subss   xmm7, xmm5          ; (1 - K)  [approx]
    mulss   xmm4, xmm7

    ; Store results
    movss   [rdi], xmm3
    movss   [rsi], xmm4

    ; Return x_est
    movss   xmm0, xmm3
    ret

section .data
one:    dd  1.0

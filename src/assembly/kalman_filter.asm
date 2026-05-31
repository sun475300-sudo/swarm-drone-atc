; P658: Kalman Filter - x86-64 Assembly stub
; Scalar Kalman filter implementation for 1D state estimation
; Calling convention: System V AMD64 ABI

section .data
    ; Default noise parameters
    process_noise   dq 0.001       ; Q
    measurement_noise dq 0.1      ; R
    state_estimate  dq 0.0        ; x_hat
    error_covariance dq 1.0       ; P

section .text
    global kalman_predict
    global kalman_update
    global kalman_get_estimate

; kalman_predict(double control_input)
; xmm0 = control input
; Updates state_estimate and error_covariance
kalman_predict:
    ; x_hat = x_hat + control_input
    movsd   xmm1, [rel state_estimate]
    addsd   xmm1, xmm0
    movsd   [rel state_estimate], xmm1
    ; P = P + Q
    movsd   xmm2, [rel error_covariance]
    movsd   xmm3, [rel process_noise]
    addsd   xmm2, xmm3
    movsd   [rel error_covariance], xmm2
    ret

; kalman_update(double measurement)
; xmm0 = measurement
; Returns updated estimate in xmm0
kalman_update:
    ; K = P / (P + R)
    movsd   xmm1, [rel error_covariance]    ; P
    movsd   xmm2, [rel measurement_noise]   ; R
    movsd   xmm3, xmm1
    addsd   xmm3, xmm2                      ; P + R
    divsd   xmm1, xmm3                      ; K = P/(P+R)
    ; x_hat = x_hat + K * (measurement - x_hat)
    movsd   xmm4, [rel state_estimate]
    subsd   xmm0, xmm4                      ; measurement - x_hat
    mulsd   xmm0, xmm1                      ; K * innovation
    addsd   xmm4, xmm0
    movsd   [rel state_estimate], xmm4
    ; P = (1 - K) * P
    movsd   xmm5, [rel error_covariance]
    movsd   xmm6, xmm1
    movsd   xmm7, [rel error_covariance]
    mulsd   xmm6, xmm7
    subsd   xmm5, xmm6
    movsd   [rel error_covariance], xmm5
    movsd   xmm0, xmm4
    ret

; kalman_get_estimate() -> double
kalman_get_estimate:
    movsd   xmm0, [rel state_estimate]
    ret

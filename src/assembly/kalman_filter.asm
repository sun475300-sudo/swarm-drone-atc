; Kalman Filter (1D altitude) — SDACS Phase 656
; SSE2 scalar implementation
section .text
global kalman_predict
kalman_predict:
    ; x_hat = F * x_hat_prev
    movsd xmm0, [rdi]       ; load state
    mulsd xmm0, [rsi]       ; multiply by F
    movsd [rdx], xmm0       ; store result
    ret
section .data
    dq 1.0                  ; F = 1.0 (constant velocity model)

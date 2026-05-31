; Phase 658 — Kalman Filter (x86-64 Assembly / NASM)
; 드론 1D 위치 추정을 위한 스칼라 칼만 필터
;
; 인터페이스 (C 호출 규약 — System V AMD64 ABI):
;   void kalman_update(double *x_est,   ; rdi: 상태 추정값
;                      double *p_est,   ; rsi: 오차 공분산
;                      double  z_meas,  ; xmm0: 관측값
;                      double  q_noise, ; xmm1: 프로세스 노이즈 분산
;                      double  r_noise) ; xmm2: 관측 노이즈 분산

section .text
global kalman_update

kalman_update:
    ; -- 예측 단계 --
    ; x_pred = x_est  (상수 속도 모델 생략)
    ; p_pred = p_est + q_noise
    movsd   xmm3, [rsi]         ; xmm3 = *p_est
    addsd   xmm3, xmm1          ; xmm3 = p_pred = p + Q

    ; -- 갱신 단계 --
    ; K = p_pred / (p_pred + R)
    movsd   xmm4, xmm3          ; xmm4 = p_pred
    addsd   xmm4, xmm2          ; xmm4 = p_pred + R
    movsd   xmm5, xmm3
    divsd   xmm5, xmm4          ; xmm5 = K (칼만 이득)

    ; x_new = x_est + K * (z - x_est)
    movsd   xmm6, [rdi]         ; xmm6 = *x_est
    movsd   xmm7, xmm0          ; xmm7 = z
    subsd   xmm7, xmm6          ; xmm7 = innovation = z - x_est
    mulsd   xmm7, xmm5          ; xmm7 = K * innovation
    addsd   xmm6, xmm7          ; xmm6 = x_new
    movsd   [rdi], xmm6         ; *x_est = x_new

    ; p_new = (1 - K) * p_pred
    movsd   xmm8, [rel one]
    subsd   xmm8, xmm5          ; xmm8 = 1 - K
    mulsd   xmm8, xmm3          ; xmm8 = p_new
    movsd   [rsi], xmm8         ; *p_est = p_new

    ret

section .data
align 8
one:    dq 1.0

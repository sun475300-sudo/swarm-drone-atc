; SDACS Kalman Filter — x86-64 Assembly (NASM)
; 군집드론 칼만 필터 위치 추정

section .data
    ; 칼만 필터 상태 변수 (double precision)
    state_x     dq  0.0     ; 추정 위치 X
    state_y     dq  0.0     ; 추정 위치 Y
    state_z     dq  0.0     ; 추정 위치 Z (고도)
    vel_x       dq  0.0     ; 속도 X
    vel_y       dq  0.0     ; 속도 Y
    vel_z       dq  0.0     ; 속도 Z

    ; 공분산 행렬 대각 요소
    P_pos       dq  1.0     ; 위치 불확실도
    P_vel       dq  1.0     ; 속도 불확실도

    ; 노이즈 파라미터
    Q_pos       dq  0.01    ; 프로세스 노이즈 (위치)
    Q_vel       dq  0.1     ; 프로세스 노이즈 (속도)
    R_meas      dq  0.5     ; 측정 노이즈

    ; 칼만 게인
    K_gain      dq  0.0

    msg_init    db  "Kalman Filter initialized", 10, 0
    msg_predict db  "Predict step complete", 10, 0
    msg_update  db  "Update step complete", 10, 0

section .bss
    meas_buf    resq 3      ; 측정값 버퍼 [x, y, z]
    innov_buf   resq 3      ; 혁신 벡터 버퍼

section .text
    global _start
    global kalman_predict
    global kalman_update
    global kalman_get_state

; 칼만 예측 단계
; rdi = dt (double, 시간 간격)
kalman_predict:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32

    ; state_x += vel_x * dt
    movsd   xmm0, [rel state_x]
    movsd   xmm1, [rel vel_x]
    mulsd   xmm1, xmm0          ; vel_x * dt (dt가 xmm0에)
    ; (실제 구현에서는 dt 인수 사용)
    addsd   xmm0, xmm1
    movsd   [rel state_x], xmm0

    ; P_pos += Q_pos (공분산 전파)
    movsd   xmm0, [rel P_pos]
    movsd   xmm1, [rel Q_pos]
    addsd   xmm0, xmm1
    movsd   [rel P_pos], xmm0

    leave
    ret

; 칼만 업데이트 단계
; xmm0 = 측정값 x, xmm1 = 측정값 y, xmm2 = 측정값 z
kalman_update:
    push    rbp
    mov     rbp, rsp

    ; 칼만 게인 계산: K = P / (P + R)
    movsd   xmm3, [rel P_pos]
    movsd   xmm4, [rel R_meas]
    addsd   xmm4, xmm3          ; P + R
    divsd   xmm3, xmm4          ; K = P / (P + R)
    movsd   [rel K_gain], xmm3

    ; 상태 업데이트: x = x + K * (z - x)
    movsd   xmm4, [rel state_x]
    subsd   xmm0, xmm4          ; z - x (혁신)
    mulsd   xmm0, xmm3          ; K * 혁신
    addsd   xmm4, xmm0          ; x_new = x + K*(z-x)
    movsd   [rel state_x], xmm4

    ; 공분산 업데이트: P = (1 - K) * P
    movsd   xmm5, [rel K_gain]
    movsd   xmm6, [rel P_pos]
    movsd   xmm7, [rel P_pos]
    mov     rax, 0x3FF0000000000000  ; 1.0 as IEEE 754
    movq    xmm0, rax
    subsd   xmm0, xmm5          ; 1 - K
    mulsd   xmm0, xmm6          ; (1-K) * P
    movsd   [rel P_pos], xmm0

    leave
    ret

; 현재 상태 반환 (rdi = 출력 버퍼 포인터)
kalman_get_state:
    movsd   xmm0, [rel state_x]
    movsd   [rdi], xmm0
    movsd   xmm1, [rel state_y]
    movsd   [rdi+8], xmm1
    movsd   xmm2, [rel state_z]
    movsd   [rdi+16], xmm2
    ret

_start:
    ; 종료
    mov     eax, 60
    xor     edi, edi
    syscall

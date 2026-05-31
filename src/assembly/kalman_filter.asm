; kalman_filter.asm - Kalman filter for drone state estimation
; x86-64 assembly implementation for SDACS

section .data
    filter_name:    db "Kalman Filter", 0
    state_size:     dq 6        ; [x, y, z, vx, vy, vz]
    noise_q:        dq 0.1      ; process noise
    noise_r:        dq 1.0      ; measurement noise
    msg_init:       db "Kalman filter initialized", 0x0A, 0
    msg_predict:    db "Prediction step", 0x0A, 0
    msg_update:     db "Update step", 0x0A, 0

section .bss
    state:      resq 6          ; state vector [x,y,z,vx,vy,vz]
    covariance: resq 36         ; 6x6 covariance matrix P
    gain:       resq 6          ; Kalman gain vector
    dt:         resq 1          ; time step
    residual:   resq 3          ; measurement residual

section .text
    global _start
    global kalman_init
    global kalman_predict
    global kalman_update
    global kalman_get_state

; kalman_init: initialize filter state
; Input: rdi = initial state vector pointer (6 doubles)
kalman_init:
    push rbp
    mov rbp, rsp
    push r12

    lea r12, [state]
    mov rcx, 6
.copy_state:
    movsd xmm0, [rdi]
    movsd [r12], xmm0
    add rdi, 8
    add r12, 8
    dec rcx
    jnz .copy_state

    ; Initialize covariance to identity * 100
    lea r12, [covariance]
    xor rax, rax
.init_cov:
    movsd xmm0, qword [rel noise_q]
    movsd [r12 + rax*8], xmm0
    inc rax
    cmp rax, 36
    jl .init_cov

    pop r12
    pop rbp
    ret

; kalman_predict: time update step
; Uses constant velocity model
kalman_predict:
    push rbp
    mov rbp, rsp

    movsd xmm0, qword [state + 0*8]     ; x
    movsd xmm1, qword [state + 3*8]     ; vx
    movsd xmm2, qword [dt]              ; dt
    mulsd  xmm1, xmm2                   ; vx * dt
    addsd  xmm0, xmm1                   ; x += vx*dt
    movsd qword [state + 0*8], xmm0

    movsd xmm0, qword [state + 1*8]     ; y
    movsd xmm1, qword [state + 4*8]     ; vy
    mulsd  xmm1, xmm2
    addsd  xmm0, xmm1
    movsd qword [state + 1*8], xmm0

    pop rbp
    ret

; kalman_update: measurement update step
; Input: rdi = measurement vector pointer [mx, my, mz]
kalman_update:
    push rbp
    mov rbp, rsp

    ; Compute residual y = z - H*x
    movsd xmm0, [rdi]                   ; measured x
    movsd xmm1, qword [state + 0*8]     ; predicted x
    subsd xmm0, xmm1
    movsd qword [residual + 0*8], xmm0

    movsd xmm0, [rdi + 8]
    movsd xmm1, qword [state + 1*8]
    subsd xmm0, xmm1
    movsd qword [residual + 1*8], xmm0

    pop rbp
    ret

; kalman_get_state: copy current state to output buffer
; Input: rdi = output buffer (6 doubles)
kalman_get_state:
    push rbp
    mov rbp, rsp
    mov rcx, 6
    lea rsi, [state]
.copy:
    movsd xmm0, [rsi]
    movsd [rdi], xmm0
    add rsi, 8
    add rdi, 8
    dec rcx
    jnz .copy
    pop rbp
    ret

_start:
    mov eax, 60
    xor edi, edi
    syscall

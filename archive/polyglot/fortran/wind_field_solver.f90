! Phase 577: Wind Field Solver — Fortran 90
! 3D 풍장 수치해석: Navier-Stokes 간이 솔버,
! 유한차분법(FDM), 야코비 반복법.

module wind_field_types
    implicit none

    integer, parameter :: dp = selected_real_kind(15, 307)

    type :: WindFieldParams
        integer :: nx = 32        ! X 격자 수
        integer :: ny = 32        ! Y 격자 수
        integer :: nz = 16        ! Z 격자 수
        real(dp) :: dx = 100.0_dp ! 격자 간격 (m)
        real(dp) :: dy = 100.0_dp
        real(dp) :: dz = 50.0_dp
        real(dp) :: dt = 1.0_dp   ! 시간 스텝 (s)
        real(dp) :: nu = 15.0_dp  ! 동점성계수 (m^2/s)
        real(dp) :: rho = 1.225_dp ! 공기밀도 (kg/m^3)
    end type

    type :: WindField
        real(dp), allocatable :: u(:,:,:)  ! X 풍속
        real(dp), allocatable :: v(:,:,:)  ! Y 풍속
        real(dp), allocatable :: w(:,:,:)  ! Z 풍속
        real(dp), allocatable :: p(:,:,:)  ! 압력
        type(WindFieldParams) :: params
    end type

end module wind_field_types

module wind_field_solver
    use wind_field_types
    implicit none

contains

    !─── 풍장 초기화 ───
    subroutine init_wind_field(wf, params)
        type(WindField), intent(inout) :: wf
        type(WindFieldParams), intent(in) :: params
        integer :: nx, ny, nz

        wf%params = params
        nx = params%nx; ny = params%ny; nz = params%nz

        allocate(wf%u(nx, ny, nz))
        allocate(wf%v(nx, ny, nz))
        allocate(wf%w(nx, ny, nz))
        allocate(wf%p(nx, ny, nz))

        wf%u = 5.0_dp    ! 기본 서풍 5 m/s
        wf%v = 0.0_dp
        wf%w = 0.0_dp
        wf%p = 101325.0_dp  ! 표준 대기압 (Pa)
    end subroutine

    !─── 라플라시안 (야코비) ───
    function laplacian_3d(field, i, j, k, dx, dy, dz) result(lap)
        real(dp), intent(in) :: field(:,:,:)
        integer, intent(in) :: i, j, k
        real(dp), intent(in) :: dx, dy, dz
        real(dp) :: lap
        integer :: ni, nj, nk

        ni = size(field, 1)
        nj = size(field, 2)
        nk = size(field, 3)

        lap = 0.0_dp

        ! X 방향
        if (i > 1 .and. i < ni) then
            lap = lap + (field(i+1,j,k) - 2*field(i,j,k) + field(i-1,j,k)) / (dx*dx)
        end if

        ! Y 방향
        if (j > 1 .and. j < nj) then
            lap = lap + (field(i,j+1,k) - 2*field(i,j,k) + field(i,j-1,k)) / (dy*dy)
        end if

        ! Z 방향
        if (k > 1 .and. k < nk) then
            lap = lap + (field(i,j,k+1) - 2*field(i,j,k) + field(i,j,k-1)) / (dz*dz)
        end if
    end function

    !─── 확산 스텝 (점성) ───
    subroutine diffusion_step(wf)
        type(WindField), intent(inout) :: wf
        real(dp), allocatable :: u_new(:,:,:), v_new(:,:,:), w_new(:,:,:)
        integer :: i, j, k, nx, ny, nz
        real(dp) :: nu, dt, dx, dy, dz

        nx = wf%params%nx; ny = wf%params%ny; nz = wf%params%nz
        nu = wf%params%nu; dt = wf%params%dt
        dx = wf%params%dx; dy = wf%params%dy; dz = wf%params%dz

        allocate(u_new(nx, ny, nz))
        allocate(v_new(nx, ny, nz))
        allocate(w_new(nx, ny, nz))

        u_new = wf%u; v_new = wf%v; w_new = wf%w

        do k = 2, nz - 1
            do j = 2, ny - 1
                do i = 2, nx - 1
                    u_new(i,j,k) = wf%u(i,j,k) + nu * dt * &
                        laplacian_3d(wf%u, i, j, k, dx, dy, dz)
                    v_new(i,j,k) = wf%v(i,j,k) + nu * dt * &
                        laplacian_3d(wf%v, i, j, k, dx, dy, dz)
                    w_new(i,j,k) = wf%w(i,j,k) + nu * dt * &
                        laplacian_3d(wf%w, i, j, k, dx, dy, dz)
                end do
            end do
        end do

        wf%u = u_new; wf%v = v_new; wf%w = w_new

        deallocate(u_new, v_new, w_new)
    end subroutine

    !─── 풍속 크기 계산 ───
    function wind_speed(wf, i, j, k) result(speed)
        type(WindField), intent(in) :: wf
        integer, intent(in) :: i, j, k
        real(dp) :: speed

        speed = sqrt(wf%u(i,j,k)**2 + wf%v(i,j,k)**2 + wf%w(i,j,k)**2)
    end function

    !─── 최대 풍속 ───
    function max_wind_speed(wf) result(max_speed)
        type(WindField), intent(in) :: wf
        real(dp) :: max_speed, spd
        integer :: i, j, k

        max_speed = 0.0_dp
        do k = 1, wf%params%nz
            do j = 1, wf%params%ny
                do i = 1, wf%params%nx
                    spd = wind_speed(wf, i, j, k)
                    if (spd > max_speed) max_speed = spd
                end do
            end do
        end do
    end function

    !─── 난류 강도 계산 ───
    function turbulence_intensity(wf) result(ti)
        type(WindField), intent(in) :: wf
        real(dp) :: ti, mean_u, mean_v, mean_w, std_u
        integer :: n

        n = wf%params%nx * wf%params%ny * wf%params%nz
        mean_u = sum(wf%u) / n
        mean_v = sum(wf%v) / n
        mean_w = sum(wf%w) / n

        std_u = sqrt(sum((wf%u - mean_u)**2) / n)
        ti = std_u / max(abs(mean_u), 0.01_dp)
    end function

    !─── 정리 ───
    subroutine cleanup_wind_field(wf)
        type(WindField), intent(inout) :: wf
        if (allocated(wf%u)) deallocate(wf%u)
        if (allocated(wf%v)) deallocate(wf%v)
        if (allocated(wf%w)) deallocate(wf%w)
        if (allocated(wf%p)) deallocate(wf%p)
    end subroutine

end module wind_field_solver

!─── 메인 프로그램 ───
program main
    use wind_field_types
    use wind_field_solver
    implicit none

    type(WindField) :: wf
    type(WindFieldParams) :: params
    integer :: step
    real(dp) :: max_spd, ti

    params%nx = 16; params%ny = 16; params%nz = 8
    params%dt = 0.5_dp

    call init_wind_field(wf, params)

    print *, "=== SDACS Wind Field Solver ==="
    print *, "Grid:", params%nx, "x", params%ny, "x", params%nz

    do step = 1, 20
        call diffusion_step(wf)
        max_spd = max_wind_speed(wf)
        ti = turbulence_intensity(wf)
        if (mod(step, 5) == 0) then
            print '(A,I4,A,F8.3,A,F8.5)', " Step ", step, &
                "  max_wind=", max_spd, "  TI=", ti
        end if
    end do

    call cleanup_wind_field(wf)
    print *, "Simulation complete."
end program main

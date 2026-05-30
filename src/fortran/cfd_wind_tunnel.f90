! SDACS CFD Wind Tunnel — Fortran 90
! 드론 군집 풍동 시뮬레이션 전산 유체역학

module wind_tunnel_module
    implicit none
    private

    integer, parameter :: dp = selected_real_kind(15, 307)

    type, public :: WindTunnel
        real(dp) :: length    ! m
        real(dp) :: width     ! m
        real(dp) :: height    ! m
        real(dp) :: inlet_velocity   ! m/s
        integer  :: nx, ny, nz
        real(dp), allocatable :: u(:,:,:)   ! x-velocity
        real(dp), allocatable :: v(:,:,:)   ! y-velocity
        real(dp), allocatable :: w(:,:,:)   ! z-velocity
        real(dp), allocatable :: p(:,:,:)   ! pressure
    contains
        procedure :: initialize => tunnel_init
        procedure :: solve_euler_step => tunnel_step
        procedure :: get_velocity_at => tunnel_velocity_at
        procedure :: turbulence_intensity => tunnel_turbulence
        procedure :: free => tunnel_free
    end type WindTunnel

    public :: compute_drag_coefficient
    public :: compute_lift_coefficient

contains

    subroutine tunnel_init(this, L, W, H, U_in, nx, ny, nz)
        class(WindTunnel), intent(inout) :: this
        real(dp), intent(in) :: L, W, H, U_in
        integer, intent(in) :: nx, ny, nz

        this%length = L; this%width = W; this%height = H
        this%inlet_velocity = U_in
        this%nx = nx; this%ny = ny; this%nz = nz

        allocate(this%u(nx, ny, nz), this%v(nx, ny, nz))
        allocate(this%w(nx, ny, nz), this%p(nx, ny, nz))

        this%u = U_in
        this%v = 0.0_dp
        this%w = 0.0_dp
        this%p = 101325.0_dp
    end subroutine tunnel_init

    subroutine tunnel_step(this, dt)
        class(WindTunnel), intent(inout) :: this
        real(dp), intent(in) :: dt
        real(dp) :: nu = 1.5e-5_dp  ! 공기 동점성계수
        integer :: i, j, k

        ! 단순화된 오일러 방정식 (비점성 유동)
        do k = 2, this%nz - 1
            do j = 2, this%ny - 1
                do i = 2, this%nx - 1
                    ! 대류 항 (1차 upwind)
                    this%u(i,j,k) = this%u(i,j,k) - dt * &
                        (this%u(i,j,k) - this%u(i-1,j,k)) / (this%length / this%nx)
                end do
            end do
        end do

        ! 경계 조건: 입구 속도 유지
        this%u(1,:,:) = this%inlet_velocity
    end subroutine tunnel_step

    function tunnel_velocity_at(this, x, y, z) result(vel)
        class(WindTunnel), intent(in) :: this
        real(dp), intent(in) :: x, y, z
        real(dp) :: vel(3)
        integer :: i, j, k

        i = max(1, min(this%nx, int(x / this%length * this%nx) + 1))
        j = max(1, min(this%ny, int(y / this%width  * this%ny) + 1))
        k = max(1, min(this%nz, int(z / this%height * this%nz) + 1))

        vel(1) = this%u(i,j,k)
        vel(2) = this%v(i,j,k)
        vel(3) = this%w(i,j,k)
    end function tunnel_velocity_at

    function tunnel_turbulence(this) result(ti)
        class(WindTunnel), intent(in) :: this
        real(dp) :: ti, u_mean, u_std, u_sq_sum
        integer :: n

        n = this%nx * this%ny * this%nz
        u_mean = sum(this%u) / real(n, dp)
        u_sq_sum = sum((this%u - u_mean)**2)
        u_std = sqrt(u_sq_sum / real(n, dp))
        ti = u_std / (abs(u_mean) + 1.0e-10_dp)
    end function tunnel_turbulence

    subroutine tunnel_free(this)
        class(WindTunnel), intent(inout) :: this
        if (allocated(this%u)) deallocate(this%u, this%v, this%w, this%p)
    end subroutine tunnel_free

    function compute_drag_coefficient(frontal_area, drag_force, dynamic_pressure) result(cd)
        real(dp), intent(in) :: frontal_area, drag_force, dynamic_pressure
        real(dp) :: cd
        cd = drag_force / (dynamic_pressure * frontal_area + 1.0e-10_dp)
    end function compute_drag_coefficient

    function compute_lift_coefficient(wing_area, lift_force, dynamic_pressure) result(cl)
        real(dp), intent(in) :: wing_area, lift_force, dynamic_pressure
        real(dp) :: cl
        cl = lift_force / (dynamic_pressure * wing_area + 1.0e-10_dp)
    end function compute_lift_coefficient

end module wind_tunnel_module

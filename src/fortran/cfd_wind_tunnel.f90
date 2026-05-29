! Phase 639: CFD Wind Tunnel — Fortran 3D Finite Difference
! 풍동 시뮬레이션 3D 유한차분법

module cfd_wind_tunnel
    implicit none

    integer, parameter :: NX = 30, NY = 30, NZ = 10
    real(8), parameter :: DX = 1.0d0, DY = 1.0d0, DZ = 1.0d0
    real(8), parameter :: DT = 0.001d0
    real(8), parameter :: VISCOSITY = 0.01d0

    type :: WindField
        real(8) :: u(NX, NY, NZ)    ! x-velocity
        real(8) :: v(NX, NY, NZ)    ! y-velocity
        real(8) :: w(NX, NY, NZ)    ! z-velocity
        real(8) :: p(NX, NY, NZ)    ! pressure
        real(8) :: rho(NX, NY, NZ)  ! density
        integer :: step_count
        real(8) :: total_energy
    end type

contains

    subroutine init_field(field)
        type(WindField), intent(inout) :: field
        integer :: i, j, k

        field%u = 0.0d0
        field%v = 0.0d0
        field%w = 0.0d0
        field%p = 101325.0d0  ! atmospheric pressure (Pa)
        field%rho = 1.225d0   ! air density (kg/m^3)
        field%step_count = 0
        field%total_energy = 0.0d0

        ! inlet boundary: uniform flow
        do j = 1, NY
            do k = 1, NZ
                field%u(1, j, k) = 10.0d0  ! 10 m/s inlet
            end do
        end do
    end subroutine

    subroutine diffuse_step(field)
        type(WindField), intent(inout) :: field
        real(8) :: u_new(NX, NY, NZ), v_new(NX, NY, NZ), w_new(NX, NY, NZ)
        real(8) :: alpha
        integer :: i, j, k

        alpha = VISCOSITY * DT / (DX * DX)
        u_new = field%u
        v_new = field%v
        w_new = field%w

        do k = 2, NZ-1
            do j = 2, NY-1
                do i = 2, NX-1
                    u_new(i,j,k) = field%u(i,j,k) + alpha * ( &
                        field%u(i+1,j,k) + field%u(i-1,j,k) + &
                        field%u(i,j+1,k) + field%u(i,j-1,k) + &
                        field%u(i,j,k+1) + field%u(i,j,k-1) - &
                        6.0d0 * field%u(i,j,k))

                    v_new(i,j,k) = field%v(i,j,k) + alpha * ( &
                        field%v(i+1,j,k) + field%v(i-1,j,k) + &
                        field%v(i,j+1,k) + field%v(i,j-1,k) + &
                        field%v(i,j,k+1) + field%v(i,j,k-1) - &
                        6.0d0 * field%v(i,j,k))

                    w_new(i,j,k) = field%w(i,j,k) + alpha * ( &
                        field%w(i+1,j,k) + field%w(i-1,j,k) + &
                        field%w(i,j+1,k) + field%w(i,j-1,k) + &
                        field%w(i,j,k+1) + field%w(i,j,k-1) - &
                        6.0d0 * field%w(i,j,k))
                end do
            end do
        end do

        field%u = u_new
        field%v = v_new
        field%w = w_new
    end subroutine

    subroutine compute_energy(field)
        type(WindField), intent(inout) :: field
        integer :: i, j, k

        field%total_energy = 0.0d0
        do k = 1, NZ
            do j = 1, NY
                do i = 1, NX
                    field%total_energy = field%total_energy + 0.5d0 * field%rho(i,j,k) * &
                        (field%u(i,j,k)**2 + field%v(i,j,k)**2 + field%w(i,j,k)**2)
                end do
            end do
        end do
    end subroutine

    subroutine simulate(field, n_steps)
        type(WindField), intent(inout) :: field
        integer, intent(in) :: n_steps
        integer :: step

        do step = 1, n_steps
            call diffuse_step(field)
            field%step_count = field%step_count + 1
        end do
        call compute_energy(field)
    end subroutine

end module cfd_wind_tunnel

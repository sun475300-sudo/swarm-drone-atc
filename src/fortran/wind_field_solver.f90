! wind_field_solver.f90 - Wind field numerical solver for SDACS
! Solves wind field equations for drone airspace control

module wind_field_types
    implicit none
    integer, parameter :: dp = kind(1.0d0)

    type :: wind_vector
        real(dp) :: u  ! East-West component
        real(dp) :: v  ! North-South component
        real(dp) :: w  ! Vertical component
    end type wind_vector

    type :: grid_point
        real(dp) :: x, y, z
        type(wind_vector) :: wind
        real(dp) :: pressure
        real(dp) :: temperature
        real(dp) :: density
    end type grid_point
end module wind_field_types

module wind_field_solver
    use wind_field_types
    implicit none

    integer, parameter :: NX = 50, NY = 50, NZ = 20
    real(dp), parameter :: DX = 100.0_dp   ! Grid spacing in meters
    real(dp), parameter :: DY = 100.0_dp
    real(dp), parameter :: DZ = 50.0_dp
    real(dp), parameter :: DT = 0.5_dp     ! Time step in seconds

    type(grid_point), allocatable :: grid(:,:,:)
    integer :: nx_pts, ny_pts, nz_pts

contains

    subroutine initialize_grid(n_x, n_y, n_z)
        integer, intent(in) :: n_x, n_y, n_z
        integer :: i, j, k

        nx_pts = n_x
        ny_pts = n_y
        nz_pts = n_z
        allocate(grid(nx_pts, ny_pts, nz_pts))

        do k = 1, nz_pts
            do j = 1, ny_pts
                do i = 1, nx_pts
                    grid(i,j,k)%x = (i-1) * DX
                    grid(i,j,k)%y = (j-1) * DY
                    grid(i,j,k)%z = (k-1) * DZ
                    grid(i,j,k)%wind%u = 0.0_dp
                    grid(i,j,k)%wind%v = 0.0_dp
                    grid(i,j,k)%wind%w = 0.0_dp
                    grid(i,j,k)%pressure = 101325.0_dp * exp(-grid(i,j,k)%z / 8500.0_dp)
                    grid(i,j,k)%temperature = 288.15_dp - 0.0065_dp * grid(i,j,k)%z
                    grid(i,j,k)%density = 1.225_dp * exp(-grid(i,j,k)%z / 8500.0_dp)
                end do
            end do
        end do
    end subroutine initialize_grid

    subroutine set_boundary_conditions(wind_speed, wind_direction)
        real(dp), intent(in) :: wind_speed, wind_direction
        real(dp) :: u0, v0
        integer :: i, j, k

        u0 = wind_speed * cos(wind_direction * 3.14159265_dp / 180.0_dp)
        v0 = wind_speed * sin(wind_direction * 3.14159265_dp / 180.0_dp)

        do k = 1, nz_pts
            do j = 1, ny_pts
                grid(1, j, k)%wind%u = u0 * (grid(1,j,k)%z / 100.0_dp)**0.143_dp
                grid(1, j, k)%wind%v = v0 * (grid(1,j,k)%z / 100.0_dp)**0.143_dp
            end do
        end do
    end subroutine set_boundary_conditions

    subroutine solve_wind_advection(n_steps)
        integer, intent(in) :: n_steps
        integer :: step, i, j, k
        real(dp) :: du_dx, dv_dy, dw_dz

        do step = 1, n_steps
            do k = 2, nz_pts-1
                do j = 2, ny_pts-1
                    do i = 2, nx_pts-1
                        du_dx = (grid(i+1,j,k)%wind%u - grid(i-1,j,k)%wind%u) / (2.0_dp * DX)
                        dv_dy = (grid(i,j+1,k)%wind%v - grid(i,j-1,k)%wind%v) / (2.0_dp * DY)
                        dw_dz = (grid(i,j,k+1)%wind%w - grid(i,j,k-1)%wind%w) / (2.0_dp * DZ)

                        grid(i,j,k)%wind%u = grid(i,j,k)%wind%u - DT * &
                            (grid(i,j,k)%wind%u * du_dx + &
                             grid(i,j,k)%wind%v * dv_dy)
                    end do
                end do
            end do
        end do
    end subroutine solve_wind_advection

    function get_wind_at_position(x, y, z) result(wind)
        real(dp), intent(in) :: x, y, z
        type(wind_vector) :: wind
        integer :: i, j, k

        i = max(1, min(nx_pts, int(x / DX) + 1))
        j = max(1, min(ny_pts, int(y / DY) + 1))
        k = max(1, min(nz_pts, int(z / DZ) + 1))

        wind = grid(i, j, k)%wind
    end function get_wind_at_position

    subroutine compute_wind_gradient(i, j, k, grad_u, grad_v)
        integer, intent(in) :: i, j, k
        real(dp), intent(out) :: grad_u, grad_v

        if (i > 1 .and. i < nx_pts) then
            grad_u = (grid(i+1,j,k)%wind%u - grid(i-1,j,k)%wind%u) / (2.0_dp * DX)
        else
            grad_u = 0.0_dp
        end if

        if (j > 1 .and. j < ny_pts) then
            grad_v = (grid(i,j+1,k)%wind%v - grid(i,j-1,k)%wind%v) / (2.0_dp * DY)
        else
            grad_v = 0.0_dp
        end if
    end subroutine compute_wind_gradient

    subroutine cleanup_grid()
        if (allocated(grid)) then
            deallocate(grid)
        end if
    end subroutine cleanup_grid

end module wind_field_solver

! SDACS Wind Field Solver — Fortran 90
! Solves atmospheric wind field equations for drone flight planning.

module wind_field_solver
    implicit none

    real, parameter :: PI = 3.14159265358979
    real, parameter :: GRAVITY = 9.81
    real, parameter :: AIR_DENSITY_SEA_LEVEL = 1.225  ! kg/m^3
    real, parameter :: WIND_SHEAR_EXPONENT = 0.143

    integer, parameter :: MAX_GRID_X = 256
    integer, parameter :: MAX_GRID_Y = 256
    integer, parameter :: MAX_GRID_Z = 64

    type :: WindVector
        real :: u  ! East component  (m/s)
        real :: v  ! North component (m/s)
        real :: w  ! Up component    (m/s)
    end type WindVector

    type :: WindField
        type(WindVector), allocatable :: grid(:,:,:)
        real :: dx, dy, dz
        integer :: nx, ny, nz
    end type WindField

contains

    subroutine init_wind_field(field, nx, ny, nz, dx, dy, dz)
        type(WindField), intent(inout) :: field
        integer, intent(in) :: nx, ny, nz
        real, intent(in) :: dx, dy, dz

        field%nx = nx
        field%ny = ny
        field%nz = nz
        field%dx = dx
        field%dy = dy
        field%dz = dz

        allocate(field%grid(nx, ny, nz))
        call zero_wind_field(field)
    end subroutine init_wind_field

    subroutine zero_wind_field(field)
        type(WindField), intent(inout) :: field
        integer :: i, j, k

        do k = 1, field%nz
            do j = 1, field%ny
                do i = 1, field%nx
                    field%grid(i,j,k)%u = 0.0
                    field%grid(i,j,k)%v = 0.0
                    field%grid(i,j,k)%w = 0.0
                end do
            end do
        end do
    end subroutine zero_wind_field

    subroutine apply_wind_shear(field, surface_speed, surface_dir, ref_height)
        type(WindField), intent(inout) :: field
        real, intent(in) :: surface_speed, surface_dir, ref_height
        integer :: i, j, k
        real :: height, speed, angle_rad

        angle_rad = surface_dir * PI / 180.0

        do k = 1, field%nz
            height = real(k - 1) * field%dz + 0.5 * field%dz
            if (height < 0.1) height = 0.1
            speed = surface_speed * (height / ref_height) ** WIND_SHEAR_EXPONENT

            do j = 1, field%ny
                do i = 1, field%nx
                    field%grid(i,j,k)%u = speed * cos(angle_rad)
                    field%grid(i,j,k)%v = speed * sin(angle_rad)
                    field%grid(i,j,k)%w = 0.0
                end do
            end do
        end do
    end subroutine apply_wind_shear

    subroutine interpolate_wind(field, x, y, z, wv)
        type(WindField), intent(in) :: field
        real, intent(in) :: x, y, z
        type(WindVector), intent(out) :: wv
        integer :: ix, iy, iz
        real :: fx, fy, fz

        ix = max(1, min(int(x / field%dx) + 1, field%nx - 1))
        iy = max(1, min(int(y / field%dy) + 1, field%ny - 1))
        iz = max(1, min(int(z / field%dz) + 1, field%nz - 1))

        fx = (x / field%dx) - real(ix - 1)
        fy = (y / field%dy) - real(iy - 1)
        fz = (z / field%dz) - real(iz - 1)

        ! Trilinear interpolation of wind components
        wv%u = (1.0-fx)*(1.0-fy)*(1.0-fz)*field%grid(ix,iy,iz)%u &
             + fx*(1.0-fy)*(1.0-fz)*field%grid(ix+1,iy,iz)%u &
             + (1.0-fx)*fy*(1.0-fz)*field%grid(ix,iy+1,iz)%u &
             + fx*fy*(1.0-fz)*field%grid(ix+1,iy+1,iz)%u &
             + (1.0-fx)*(1.0-fy)*fz*field%grid(ix,iy,iz+1)%u &
             + fx*(1.0-fy)*fz*field%grid(ix+1,iy,iz+1)%u &
             + (1.0-fx)*fy*fz*field%grid(ix,iy+1,iz+1)%u &
             + fx*fy*fz*field%grid(ix+1,iy+1,iz+1)%u

        wv%v = (1.0-fx)*(1.0-fy)*(1.0-fz)*field%grid(ix,iy,iz)%v &
             + fx*(1.0-fy)*(1.0-fz)*field%grid(ix+1,iy,iz)%v &
             + (1.0-fx)*fy*(1.0-fz)*field%grid(ix,iy+1,iz)%v &
             + fx*fy*(1.0-fz)*field%grid(ix+1,iy+1,iz)%v &
             + (1.0-fx)*(1.0-fy)*fz*field%grid(ix,iy,iz+1)%v &
             + fx*(1.0-fy)*fz*field%grid(ix+1,iy,iz+1)%v &
             + (1.0-fx)*fy*fz*field%grid(ix,iy+1,iz+1)%v &
             + fx*fy*fz*field%grid(ix+1,iy+1,iz+1)%v

        wv%w = 0.0
    end subroutine interpolate_wind

    subroutine free_wind_field(field)
        type(WindField), intent(inout) :: field
        if (allocated(field%grid)) deallocate(field%grid)
    end subroutine free_wind_field

end module wind_field_solver

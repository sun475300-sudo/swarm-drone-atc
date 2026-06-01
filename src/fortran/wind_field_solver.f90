! Wind Field Solver — Fortran 90 for SDACS atmospheric modeling
! Phase 577

module wind_field_solver
  implicit none

  integer, parameter :: dp = kind(1.0d0)
  real(dp), parameter :: PI = 3.14159265358979323846_dp
  real(dp), parameter :: EARTH_RADIUS = 6371000.0_dp

  type :: WindVector
    real(dp) :: u, v, w       ! velocity components (m/s)
    real(dp) :: x, y, z       ! position (m)
    real(dp) :: temperature   ! K
    real(dp) :: pressure      ! Pa
    real(dp) :: humidity      ! 0-1
  end type WindVector

  type :: WindField
    integer  :: nx, ny, nz
    real(dp) :: dx, dy, dz
    type(WindVector), allocatable :: grid(:,:,:)
  end type WindField

contains

  subroutine init_wind_field(field, nx, ny, nz, dx, dy, dz)
    type(WindField), intent(out) :: field
    integer, intent(in) :: nx, ny, nz
    real(dp), intent(in) :: dx, dy, dz

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
          field%grid(i,j,k)%u = 0.0_dp
          field%grid(i,j,k)%v = 0.0_dp
          field%grid(i,j,k)%w = 0.0_dp
          field%grid(i,j,k)%temperature = 288.15_dp
          field%grid(i,j,k)%pressure = 101325.0_dp
          field%grid(i,j,k)%humidity = 0.5_dp
        end do
      end do
    end do
  end subroutine zero_wind_field

  subroutine apply_wind_shear(field, shear_rate)
    type(WindField), intent(inout) :: field
    real(dp), intent(in) :: shear_rate
    integer :: i, j, k
    do k = 1, field%nz
      do j = 1, field%ny
        do i = 1, field%nx
          field%grid(i,j,k)%u = field%grid(i,j,k)%u + &
                                 shear_rate * k * field%dz
        end do
      end do
    end do
  end subroutine apply_wind_shear

  subroutine interpolate_wind(field, x, y, z, u_out, v_out, w_out)
    type(WindField), intent(in) :: field
    real(dp), intent(in) :: x, y, z
    real(dp), intent(out) :: u_out, v_out, w_out
    integer :: ix, iy, iz
    real(dp) :: fx, fy, fz

    ix = max(1, min(field%nx-1, int(x / field%dx) + 1))
    iy = max(1, min(field%ny-1, int(y / field%dy) + 1))
    iz = max(1, min(field%nz-1, int(z / field%dz) + 1))

    fx = mod(x, field%dx) / field%dx
    fy = mod(y, field%dy) / field%dy
    fz = mod(z, field%dz) / field%dz

    ! Trilinear interpolation
    u_out = (1.0_dp-fx)*(1.0_dp-fy)*(1.0_dp-fz)*field%grid(ix,iy,iz)%u + &
            fx*(1.0_dp-fy)*(1.0_dp-fz)*field%grid(ix+1,iy,iz)%u + &
            (1.0_dp-fx)*fy*(1.0_dp-fz)*field%grid(ix,iy+1,iz)%u + &
            fx*fy*(1.0_dp-fz)*field%grid(ix+1,iy+1,iz)%u + &
            (1.0_dp-fx)*(1.0_dp-fy)*fz*field%grid(ix,iy,iz+1)%u + &
            fx*(1.0_dp-fy)*fz*field%grid(ix+1,iy,iz+1)%u + &
            (1.0_dp-fx)*fy*fz*field%grid(ix,iy+1,iz+1)%u + &
            fx*fy*fz*field%grid(ix+1,iy+1,iz+1)%u

    v_out = field%grid(ix,iy,iz)%v
    w_out = field%grid(ix,iy,iz)%w
  end subroutine interpolate_wind

  function wind_magnitude(u, v, w) result(mag)
    real(dp), intent(in) :: u, v, w
    real(dp) :: mag
    mag = sqrt(u**2 + v**2 + w**2)
  end function wind_magnitude

  subroutine free_wind_field(field)
    type(WindField), intent(inout) :: field
    if (allocated(field%grid)) deallocate(field%grid)
  end subroutine free_wind_field

end module wind_field_solver

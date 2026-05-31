! Phase 639 — CFD Wind Tunnel Simulation (Fortran 90)
! 드론 공역 내 풍속장 계산용 간이 CFD 솔버

module cfd_wind_tunnel
  implicit none

  integer, parameter :: dp = selected_real_kind(15, 307)

  type :: WindField
    integer :: nx, ny, nz
    real(dp), allocatable :: u(:,:,:)   ! x-방향 풍속 [m/s]
    real(dp), allocatable :: v(:,:,:)   ! y-방향 풍속 [m/s]
    real(dp), allocatable :: w(:,:,:)   ! z-방향 풍속 [m/s]
  end type WindField

contains

  ! 균일 유입 경계조건으로 풍속장을 초기화한다.
  subroutine init_uniform_flow(field, nx, ny, nz, u0)
    type(WindField), intent(out) :: field
    integer,         intent(in)  :: nx, ny, nz
    real(dp),        intent(in)  :: u0

    field%nx = nx; field%ny = ny; field%nz = nz
    allocate(field%u(nx,ny,nz), field%v(nx,ny,nz), field%w(nx,ny,nz))

    field%u = u0
    field%v = 0.0_dp
    field%w = 0.0_dp
  end subroutine init_uniform_flow

  ! 간이 난류 모델 — Smagorinsky LES 서브그리드 스케일
  subroutine apply_sgs_turbulence(field, cs, dx)
    type(WindField), intent(inout) :: field
    real(dp),        intent(in)    :: cs   ! Smagorinsky 상수 (~0.17)
    real(dp),        intent(in)    :: dx   ! 격자 간격 [m]

    real(dp) :: nu_t, S_mag
    integer  :: i, j, k

    do k = 2, field%nz - 1
      do j = 2, field%ny - 1
        do i = 2, field%nx - 1
          S_mag = abs(field%u(i+1,j,k) - field%u(i-1,j,k)) / (2.0_dp * dx)
          nu_t  = (cs * dx)**2 * S_mag
          field%u(i,j,k) = field%u(i,j,k) + nu_t * S_mag * dx
        end do
      end do
    end do
  end subroutine apply_sgs_turbulence

  ! 주어진 위치에서 풍속 벡터를 선형 보간한다.
  function interpolate_wind(field, x, y, z, dx) result(wind_vec)
    type(WindField), intent(in) :: field
    real(dp),        intent(in) :: x, y, z, dx
    real(dp)                    :: wind_vec(3)

    integer :: ix, iy, iz

    ix = max(1, min(field%nx, int(x / dx) + 1))
    iy = max(1, min(field%ny, int(y / dx) + 1))
    iz = max(1, min(field%nz, int(z / dx) + 1))

    wind_vec(1) = field%u(ix, iy, iz)
    wind_vec(2) = field%v(ix, iy, iz)
    wind_vec(3) = field%w(ix, iy, iz)
  end function interpolate_wind

  ! 풍속장 메모리를 해제한다.
  subroutine free_field(field)
    type(WindField), intent(inout) :: field
    if (allocated(field%u)) deallocate(field%u)
    if (allocated(field%v)) deallocate(field%v)
    if (allocated(field%w)) deallocate(field%w)
  end subroutine free_field

end module cfd_wind_tunnel

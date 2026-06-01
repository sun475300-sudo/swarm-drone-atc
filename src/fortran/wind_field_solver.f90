! Phase 577: Wind Field Solver — 드론 풍속장 수치 해석 (Fortran)
! Finite-difference wind field solver for drone path planning.
module wind_field_module
  implicit none
  integer, parameter :: PHASE = 577
  integer, parameter :: NX = 32, NY = 32, NZ = 16
  real(8), parameter :: DX = 10.0d0, DY = 10.0d0, DZ = 5.0d0
  real(8), parameter :: DT = 0.05d0
  real(8), parameter :: NU = 1.5d-5   ! kinematic viscosity of air

  ! Wind velocity components
  real(8) :: u(NX, NY, NZ)   ! x-component
  real(8) :: v(NX, NY, NZ)   ! y-component
  real(8) :: w(NX, NY, NZ)   ! z-component
  real(8) :: p(NX, NY, NZ)   ! pressure field

contains

  ! Initialize wind field with boundary layer profile
  subroutine init_wind_field(base_speed, direction_deg)
    real(8), intent(in) :: base_speed, direction_deg
    real(8) :: angle, ux, uy
    integer :: i, j, k
    real(8) :: z_eff, roughness_len

    angle = direction_deg * 3.14159265d0 / 180.0d0
    ux = base_speed * cos(angle)
    uy = base_speed * sin(angle)
    roughness_len = 0.03d0  ! open terrain roughness length (m)

    do k = 1, NZ
      do j = 1, NY
        do i = 1, NX
          z_eff = max(roughness_len, k * DZ)
          ! Log-law wind profile
          u(i,j,k) = ux * log(z_eff / roughness_len) / log(10.0d0 / roughness_len)
          v(i,j,k) = uy * log(z_eff / roughness_len) / log(10.0d0 / roughness_len)
          w(i,j,k) = 0.0d0
          p(i,j,k) = 101325.0d0 - 1.2d0 * 9.81d0 * k * DZ
        end do
      end do
    end do
  end subroutine init_wind_field

  ! Compute wind speed at a given (continuous) position
  real(8) function wind_speed_at(px, py, pz)
    real(8), intent(in) :: px, py, pz
    integer :: ix, iy, iz
    real(8) :: spd

    ix = max(1, min(NX, int(px / DX) + 1))
    iy = max(1, min(NY, int(py / DY) + 1))
    iz = max(1, min(NZ, int(pz / DZ) + 1))

    spd = sqrt(u(ix,iy,iz)**2 + v(ix,iy,iz)**2 + w(ix,iy,iz)**2)
    wind_speed_at = spd
  end function wind_speed_at

  ! One finite-difference update step (simplified advection)
  subroutine step_wind_field()
    real(8) :: u_new(NX, NY, NZ), v_new(NX, NY, NZ)
    integer :: i, j, k

    do k = 1, NZ
      do j = 2, NY-1
        do i = 2, NX-1
          ! Simplified 1st-order upwind advection
          u_new(i,j,k) = u(i,j,k) - DT / DX * u(i,j,k) * (u(i,j,k) - u(i-1,j,k)) &
                       + NU * DT / (DX*DX) * (u(i+1,j,k) - 2.0d0*u(i,j,k) + u(i-1,j,k))
          v_new(i,j,k) = v(i,j,k) - DT / DY * v(i,j,k) * (v(i,j,k) - v(i,j-1,k)) &
                       + NU * DT / (DY*DY) * (v(i,j+1,k) - 2.0d0*v(i,j,k) + v(i,j-1,k))
        end do
      end do
    end do

    u(2:NX-1, 2:NY-1, :) = u_new(2:NX-1, 2:NY-1, :)
    v(2:NX-1, 2:NY-1, :) = v_new(2:NX-1, 2:NY-1, :)
  end subroutine step_wind_field

  ! Compute domain-average wind speed
  real(8) function avg_wind_speed()
    integer :: i, j, k
    real(8) :: total
    total = 0.0d0
    do k = 1, NZ
      do j = 1, NY
        do i = 1, NX
          total = total + sqrt(u(i,j,k)**2 + v(i,j,k)**2)
        end do
      end do
    end do
    avg_wind_speed = total / real(NX * NY * NZ, 8)
  end function avg_wind_speed

end module wind_field_module

! ── Main program ─────────────────────────────────────────────────
program wind_field_solver
  use wind_field_module
  implicit none
  integer  :: step
  real(8)  :: avg_spd

  write(*,'(A,I4)') 'Phase ', PHASE
  write(*,'(A)')    'Wind Field Solver — 드론 풍속장 수치 해석 (Fortran CFD)'

  call init_wind_field(8.0d0, 45.0d0)  ! 8 m/s at 45 degrees

  avg_spd = avg_wind_speed()
  write(*,'(A,F6.3,A)') 'Initial avg wind: ', avg_spd, ' m/s'

  do step = 1, 10
    call step_wind_field()
  end do

  avg_spd = avg_wind_speed()
  write(*,'(A,F6.3,A)') 'After 10 steps:   ', avg_spd, ' m/s'

  write(*,'(A,F6.2)') 'Wind at (50,50,30): ', wind_speed_at(50.0d0, 50.0d0, 30.0d0)
  write(*,'(A)') 'Wind field solver complete.'
end program wind_field_solver

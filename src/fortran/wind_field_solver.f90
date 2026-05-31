! Phase 577 — Fortran wind field solver module with wind calculation subroutine
! SDACS atmospheric wind model for swarm drone trajectory planning

module wind_field_solver
  implicit none

  ! Constants for wind field computation
  real, parameter :: PI = 3.14159265358979_8
  real, parameter :: EARTH_RADIUS_M = 6371000.0_8
  real, parameter :: AIR_DENSITY_SEA = 1.225_8      ! kg/m^3 at sea level
  real, parameter :: LAPSE_RATE = 0.0065_8           ! K/m standard atmosphere
  real, parameter :: REF_TEMP_K = 288.15_8           ! reference temperature K

  ! Wind vector type
  type :: WindVector
    real :: u   ! East component  (m/s)
    real :: v   ! North component (m/s)
    real :: w   ! Vertical component (m/s)
    real :: speed   ! magnitude (m/s)
    real :: direction_deg  ! meteorological direction
  end type WindVector

  ! Wind field grid cell
  type :: WindCell
    real :: lat
    real :: lon
    real :: alt_m
    type(WindVector) :: wind
    real :: turbulence_intensity
  end type WindCell

  ! 3D wind field grid
  type :: WindField
    integer :: nx, ny, nz
    real :: origin_lat, origin_lon
    real :: cell_size_m
    real :: alt_base_m, alt_step_m
    type(WindCell), allocatable :: cells(:,:,:)
    real :: timestamp_s
    logical :: initialized
  end type WindField

contains

  ! Initialize a wind field grid
  subroutine init_wind_field(wf, nx, ny, nz, origin_lat, origin_lon, cell_size, alt_base, alt_step)
    type(WindField), intent(inout) :: wf
    integer, intent(in) :: nx, ny, nz
    real, intent(in) :: origin_lat, origin_lon, cell_size, alt_base, alt_step

    wf%nx = nx
    wf%ny = ny
    wf%nz = nz
    wf%origin_lat = origin_lat
    wf%origin_lon = origin_lon
    wf%cell_size_m = cell_size
    wf%alt_base_m = alt_base
    wf%alt_step_m = alt_step
    wf%timestamp_s = 0.0
    wf%initialized = .true.
    allocate(wf%cells(nx, ny, nz))
  end subroutine init_wind_field

  ! Compute wind speed magnitude from components
  pure real function wind_speed(u, v, w)
    real, intent(in) :: u, v, w
    wind_speed = sqrt(u*u + v*v + w*w)
  end function wind_speed

  ! Compute meteorological wind direction from U/V components
  pure real function wind_direction(u, v)
    real, intent(in) :: u, v
    real :: dir
    dir = atan2(-u, -v) * (180.0 / PI)
    if (dir < 0.0) dir = dir + 360.0
    wind_direction = dir
  end function wind_direction

  ! Main wind calculation subroutine — power-law vertical wind profile
  subroutine calc_wind_profile(alt_m, ref_wind_u, ref_wind_v, ref_alt_m, alpha, wv)
    real, intent(in) :: alt_m           ! query altitude (m)
    real, intent(in) :: ref_wind_u      ! reference U wind component (m/s)
    real, intent(in) :: ref_wind_v      ! reference V wind component (m/s)
    real, intent(in) :: ref_alt_m       ! reference altitude (m)
    real, intent(in) :: alpha           ! wind shear exponent (0.143 open terrain)
    type(WindVector), intent(out) :: wv

    real :: ratio, scale

    if (ref_alt_m <= 0.0 .or. alt_m <= 0.0) then
      wv%u = 0.0; wv%v = 0.0; wv%w = 0.0
      wv%speed = 0.0; wv%direction_deg = 0.0
      return
    end if

    ratio = alt_m / ref_alt_m
    scale = ratio ** alpha   ! power law wind profile

    wv%u = ref_wind_u * scale
    wv%v = ref_wind_v * scale
    wv%w = 0.0
    wv%speed = wind_speed(wv%u, wv%v, wv%w)
    wv%direction_deg = wind_direction(wv%u, wv%v)
  end subroutine calc_wind_profile

  ! Populate entire wind field grid using a uniform reference wind
  subroutine fill_wind_field(wf, ref_u, ref_v, ref_alt, alpha)
    type(WindField), intent(inout) :: wf
    real, intent(in) :: ref_u, ref_v, ref_alt, alpha

    integer :: ix, iy, iz
    real :: cell_alt

    do iz = 1, wf%nz
      cell_alt = wf%alt_base_m + (iz - 1) * wf%alt_step_m
      do iy = 1, wf%ny
        do ix = 1, wf%nx
          wf%cells(ix, iy, iz)%alt_m = cell_alt
          call calc_wind_profile(cell_alt, ref_u, ref_v, ref_alt, alpha, &
                                 wf%cells(ix, iy, iz)%wind)
          wf%cells(ix, iy, iz)%turbulence_intensity = 0.1 + 0.02 * (iz - 1)
        end do
      end do
    end do
  end subroutine fill_wind_field

  ! Free allocated wind field memory
  subroutine destroy_wind_field(wf)
    type(WindField), intent(inout) :: wf
    if (allocated(wf%cells)) deallocate(wf%cells)
    wf%initialized = .false.
  end subroutine destroy_wind_field

end module wind_field_solver

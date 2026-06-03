! Phase 639: CFD Wind Tunnel — Fortran 90
! SDACS computational fluid dynamics simulation for drone aerodynamics

module cfd_wind_tunnel
    implicit none
    integer, parameter :: dp = kind(1.0d0)

    type :: GridPoint
        real(dp) :: x, y, z
        real(dp) :: u, v, w   ! velocity components
        real(dp) :: p         ! pressure
    end type GridPoint

    type :: WindTunnel
        integer               :: nx, ny, nz
        real(dp)              :: inlet_velocity
        real(dp)              :: viscosity
        type(GridPoint), allocatable :: grid(:,:,:)
    end type WindTunnel

contains

    subroutine init_tunnel(tunnel, nx, ny, nz, v_inlet, mu)
        type(WindTunnel), intent(out) :: tunnel
        integer,  intent(in) :: nx, ny, nz
        real(dp), intent(in) :: v_inlet, mu

        tunnel%nx             = nx
        tunnel%ny             = ny
        tunnel%nz             = nz
        tunnel%inlet_velocity = v_inlet
        tunnel%viscosity      = mu

        allocate(tunnel%grid(nx, ny, nz))
        ! Initialize uniform inflow
        tunnel%grid%u = v_inlet
        tunnel%grid%v = 0.0_dp
        tunnel%grid%w = 0.0_dp
        tunnel%grid%p = 101325.0_dp  ! atmospheric pressure (Pa)
    end subroutine init_tunnel

    real(dp) function drag_coefficient(tunnel, frontal_area) result(cd)
        type(WindTunnel), intent(in) :: tunnel
        real(dp),         intent(in) :: frontal_area
        real(dp) :: rho, dyn_pressure, drag_force

        rho          = 1.225_dp  ! air density kg/m^3
        dyn_pressure = 0.5_dp * rho * tunnel%inlet_velocity**2
        drag_force   = dyn_pressure * frontal_area * 0.47_dp  ! sphere Cd ~0.47
        cd           = drag_force / (dyn_pressure * frontal_area)
    end function drag_coefficient

    subroutine free_tunnel(tunnel)
        type(WindTunnel), intent(inout) :: tunnel
        if (allocated(tunnel%grid)) deallocate(tunnel%grid)
    end subroutine free_tunnel

end module cfd_wind_tunnel

program wind_tunnel_demo
    use cfd_wind_tunnel
    implicit none
    type(WindTunnel) :: tunnel
    real(dp) :: cd

    call init_tunnel(tunnel, 20, 10, 10, 10.0_dp, 1.8e-5_dp)
    cd = drag_coefficient(tunnel, 0.05_dp)
    write(*,'(A,F6.3)') 'Phase 639: Drag coefficient Cd = ', cd
    call free_tunnel(tunnel)
end program wind_tunnel_demo

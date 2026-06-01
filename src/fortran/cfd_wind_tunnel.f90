! Phase 639 — Fortran CFD Wind Tunnel (3D Finite Difference Method)
! Simulates wind velocity field around drone swarm obstacles

module wind_tunnel
  implicit none
  integer, parameter :: dp = kind(1.0d0)

contains

  !> Initialize a 3D velocity field with uniform inflow.
  subroutine init_field(nx, ny, nz, u, v, w, u_inf)
    integer, intent(in)  :: nx, ny, nz
    real(dp), intent(out) :: u(nx,ny,nz), v(nx,ny,nz), w(nx,ny,nz)
    real(dp), intent(in)  :: u_inf
    u = u_inf
    v = 0.0_dp
    w = 0.0_dp
  end subroutine init_field

  !> Single Jacobi iteration step for pressure Poisson equation.
  subroutine pressure_step(nx, ny, nz, p, rhs, dx)
    integer, intent(in)  :: nx, ny, nz
    real(dp), intent(inout) :: p(nx,ny,nz)
    real(dp), intent(in)    :: rhs(nx,ny,nz), dx
    integer :: i, j, k
    real(dp) :: inv6
    inv6 = 1.0_dp / 6.0_dp
    do k = 2, nz-1
      do j = 2, ny-1
        do i = 2, nx-1
          p(i,j,k) = inv6 * (p(i-1,j,k) + p(i+1,j,k) + &
                              p(i,j-1,k) + p(i,j+1,k) + &
                              p(i,j,k-1) + p(i,j,k+1) - &
                              dx*dx*rhs(i,j,k))
        end do
      end do
    end do
  end subroutine pressure_step

end module wind_tunnel

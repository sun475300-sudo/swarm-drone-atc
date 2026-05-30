! Phase 577: wind_field_solver — Fortran 기반 풍장 수치 해석
! SDACS Wind Field Solver for Drone Flight Planning

module wind_field_types
    implicit none
    integer, parameter :: dp = selected_real_kind(15, 307)

    type :: WindVector
        real(dp) :: u   ! 동풍 성분 (m/s)
        real(dp) :: v   ! 북풍 성분 (m/s)
        real(dp) :: w   ! 수직 성분 (m/s)
    end type WindVector

    type :: GridPoint
        real(dp) :: x, y, z
        type(WindVector) :: wind
        real(dp) :: pressure
        real(dp) :: temperature
    end type GridPoint

end module wind_field_types


module wind_field_solver
    use wind_field_types
    implicit none

    integer, parameter :: NX = 10, NY = 10, NZ = 5
    real(dp), parameter :: PI = 3.141592653589793_dp
    real(dp), parameter :: G  = 9.81_dp    ! 중력 가속도

contains

    ! 대기 경계층 풍 프로파일 (로그 풍속 법칙)
    subroutine log_wind_profile(z, z0, u_ref, z_ref, u_out)
        real(dp), intent(in)  :: z, z0, u_ref, z_ref
        real(dp), intent(out) :: u_out
        if (z <= z0) then
            u_out = 0.0_dp
        else
            u_out = u_ref * log(z / z0) / log(z_ref / z0)
        end if
    end subroutine log_wind_profile

    ! 바람 전단 계산 (wind shear)
    subroutine compute_wind_shear(z_array, u_array, n, shear_out)
        integer,  intent(in)  :: n
        real(dp), intent(in)  :: z_array(n), u_array(n)
        real(dp), intent(out) :: shear_out(n-1)
        integer :: i
        do i = 1, n-1
            shear_out(i) = (u_array(i+1) - u_array(i)) / (z_array(i+1) - z_array(i))
        end do
    end subroutine compute_wind_shear

    ! 풍장 격자 초기화
    subroutine init_wind_grid(grid, dx, dy, dz, u_ref, z_ref, z0)
        type(GridPoint), intent(out) :: grid(NX, NY, NZ)
        real(dp), intent(in) :: dx, dy, dz, u_ref, z_ref, z0
        integer :: ix, iy, iz
        real(dp) :: z, u_val

        do iz = 1, NZ
            z = iz * dz
            call log_wind_profile(z, z0, u_ref, z_ref, u_val)
            do iy = 1, NY
                do ix = 1, NX
                    grid(ix, iy, iz)%x = ix * dx
                    grid(ix, iy, iz)%y = iy * dy
                    grid(ix, iy, iz)%z = z
                    grid(ix, iy, iz)%wind%u = u_val
                    grid(ix, iy, iz)%wind%v = 0.5_dp * u_val * sin(PI * ix / NX)
                    grid(ix, iy, iz)%wind%w = 0.1_dp * u_val * cos(PI * iz / NZ)
                    grid(ix, iy, iz)%pressure    = 101325.0_dp * exp(-G * z / (287.0_dp * 288.15_dp))
                    grid(ix, iy, iz)%temperature = 288.15_dp - 0.0065_dp * z
                end do
            end do
        end do
    end subroutine init_wind_grid

    ! 드론 위치에서 바람 보간 (선형)
    subroutine interpolate_wind(grid, dx, dy, dz, px, py, pz, wind_out)
        type(GridPoint), intent(in)  :: grid(NX, NY, NZ)
        real(dp), intent(in)         :: dx, dy, dz, px, py, pz
        type(WindVector), intent(out) :: wind_out
        integer :: ix, iy, iz
        real(dp) :: fx, fy, fz

        ix = max(1, min(NX-1, int(px / dx)))
        iy = max(1, min(NY-1, int(py / dy)))
        iz = max(1, min(NZ-1, int(pz / dz)))
        fx = (px / dx) - ix
        fy = (py / dy) - iy
        fz = (pz / dz) - iz

        wind_out%u = grid(ix, iy, iz)%wind%u * (1.0_dp - fx) + grid(ix+1, iy, iz)%wind%u * fx
        wind_out%v = grid(ix, iy, iz)%wind%v * (1.0_dp - fy) + grid(ix, iy+1, iz)%wind%v * fy
        wind_out%w = grid(ix, iy, iz)%wind%w * (1.0_dp - fz) + grid(ix, iy, iz+1)%wind%w * fz
    end subroutine interpolate_wind

    ! 풍에너지 계산
    real(dp) function wind_energy(wv, rho)
        type(WindVector), intent(in) :: wv
        real(dp), intent(in) :: rho  ! 공기 밀도
        real(dp) :: speed_sq
        speed_sq = wv%u**2 + wv%v**2 + wv%w**2
        wind_energy = 0.5_dp * rho * speed_sq
    end function wind_energy

end module wind_field_solver


program main
    use wind_field_types
    use wind_field_solver
    implicit none

    type(GridPoint) :: grid(NX, NY, NZ)
    type(WindVector) :: w_interp
    real(dp) :: dx, dy, dz, u_ref, z_ref, z0
    real(dp) :: shear_z(NZ), shear_u(NZ), shear_out(NZ-1)
    integer :: iz

    write(*,*) 'SDACS Wind Field Solver — Phase 577'
    write(*,*)

    dx    = 10.0_dp   ! 격자 간격 (m)
    dy    = 10.0_dp
    dz    = 20.0_dp   ! 고도 간격 (m)
    u_ref = 8.0_dp    ! 기준 풍속 (m/s)
    z_ref = 10.0_dp   ! 기준 고도 (m)
    z0    = 0.1_dp    ! 조도 길이 (m, 개방 지형)

    write(*,*) '풍장 격자 초기화...'
    call init_wind_grid(grid, dx, dy, dz, u_ref, z_ref, z0)

    write(*,'(A)') '고도별 풍속 프로파일:'
    do iz = 1, NZ
        write(*,'(4X,A,F6.1,A,F6.2,A,F6.2,A,F6.2,A)') &
            'z=', grid(1,1,iz)%z, 'm: u=', grid(1,1,iz)%wind%u, &
            ' v=', grid(1,1,iz)%wind%v, ' w=', grid(1,1,iz)%wind%w, ' m/s'
        shear_z(iz) = grid(1,1,iz)%z
        shear_u(iz) = grid(1,1,iz)%wind%u
    end do

    ! 풍 전단 계산
    call compute_wind_shear(shear_z, shear_u, NZ, shear_out)
    write(*,*)
    write(*,'(A)') '풍 전단 (wind shear):'
    do iz = 1, NZ-1
        write(*,'(4X,F8.4,A)') shear_out(iz), ' (1/s)'
    end do

    ! 드론 위치 풍 보간
    write(*,*)
    call interpolate_wind(grid, dx, dy, dz, 45.0_dp, 55.0_dp, 50.0_dp, w_interp)
    write(*,'(A,F6.2,A,F6.2,A,F6.2,A)') &
        '드론 위치 풍 보간: u=', w_interp%u, ' v=', w_interp%v, ' w=', w_interp%w, ' m/s'

    write(*,*)
    write(*,*) '풍장 수치 해석 완료.'

end program main

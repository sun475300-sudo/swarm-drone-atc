! CFD Wind Tunnel — SDACS Phase 640
module cfd_tunnel
    implicit none
    contains
    subroutine wind(vel, result)
        real, intent(in) :: vel
        real, intent(out) :: result
        result = vel * 1.225
    end subroutine wind
end module cfd_tunnel

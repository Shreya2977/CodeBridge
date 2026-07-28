program newton_raphson
    implicit none
    real(8) :: x0, x, fx, fpx
    integer :: i

    read(*,*) x0
    x = x0

    ! find root of f(x) = x^2 - 2  (i.e. sqrt(2))
    do i = 1, 50
        fx = x*x - 2.0d0
        fpx = 2.0d0 * x
        if (abs(fpx) < 1.0d-12) exit
        x = x - fx / fpx
        if (abs(fx) < 1.0d-10) exit
    end do

    print '(F10.6)', x
end program newton_raphson

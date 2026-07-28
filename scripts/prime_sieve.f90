program prime_sieve
    implicit none
    integer :: n, i, j
    logical, allocatable :: is_composite(:)

    read(*,*) n
    allocate(is_composite(n))
    is_composite = .false.

    do i = 2, n
        if (.not. is_composite(i)) then
            do j = i*i, n, i
                if (j >= 2) is_composite(j) = .true.
            end do
        end if
    end do

    do i = 2, n
        if (.not. is_composite(i)) print *, i
    end do
end program prime_sieve

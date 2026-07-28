program bubble_sort
    implicit none
    integer :: n, i, j, temp
    integer, allocatable :: arr(:)

    read(*,*) n
    allocate(arr(n))
    do i = 1, n
        read(*,*) arr(i)
    end do

    do i = 1, n - 1
        do j = 1, n - i
            if (arr(j) > arr(j+1)) then
                temp = arr(j)
                arr(j) = arr(j+1)
                arr(j+1) = temp
            end if
        end do
    end do

    do i = 1, n
        print *, arr(i)
    end do
end program bubble_sort

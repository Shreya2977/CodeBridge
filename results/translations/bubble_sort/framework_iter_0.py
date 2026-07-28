def bubble_sort():
    n = int(input())
    arr = [int(input()) for _ in range(n)]

    for i in range(n - 1):
        for j in range(n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]

    for num in arr:
        print(num)

bubble_sort()
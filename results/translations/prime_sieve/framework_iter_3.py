n = int(input())
is_composite = [False] * n

for i in range(2, n):
    if not is_composite[i]:
        for j in range(i*i, n, i):
            is_composite[j] = True

for i in range(2, n):
    if not is_composite[i]:
        print(f"{i:10}")
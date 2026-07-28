n = int(input())
is_composite = [False] * (n + 1)

for i in range(2, n + 1):
    if not is_composite[i]:
        for j in range(i*i, n + 1, i):
            if j >= 2:
                is_composite[j] = True

for i in range(2, n + 1):
    if not is_composite[i]:
        print(f"{i:10}")
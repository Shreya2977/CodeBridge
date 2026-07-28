def newton_raphson():
    x0 = float(input())
    x = x0

    # find root of f(x) = x^2 - 2  (i.e. sqrt(2))
    for i in range(50):
        fx = x * x - 2.0
        fpx = 2.0 * x
        if abs(fpx) < 1.0e-12:
            break
        x = x - fx / fpx
        if abs(fx) < 1.0e-10:
            break

    print(f"{x:.6f}")

newton_raphson()
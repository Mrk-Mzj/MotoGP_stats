import matplotlib.pyplot as plt

xs = [0, 1, 2]
ys = [2.5, 4, 3]
plt.plot(xs, ys, "-o")
for x, y in zip(xs, ys):
    plt.text(x, y, str(x), color="red", fontsize=12)
plt.show

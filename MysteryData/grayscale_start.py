import numpy as np, matplotlib.pyplot as plt

files = ["Mystery1.csv", "Mystery2.data", "Mystery3.data", "Mystery4.data", "Mystery5.data"]

for f in files:
    a = np.loadtxt(f, delimiter=",")
    print(f"{f:16} shape={str(a.shape):14} "
          f"min={a.min():>10.3g} max={a.max():>10.3g} "
          f"mean={a.mean():>10.3g} distinct={len(np.unique(a))}")

CMAP = "gray"

fig, axes = plt.subplots(2, 5, figsize=(24, 9))
for i, f in enumerate(files):
    a = np.loadtxt(f, delimiter=",")
    axes[0,i].imshow(np.log1p(a), cmap=CMAP)
    axes[0,i].set_title(f"{f}\nlog")
    axes[1,i].imshow(a, vmax=np.percentile(a, 95), cmap=CMAP)
    axes[1,i].set_title("clipped at p95")
plt.tight_layout(); plt.show()
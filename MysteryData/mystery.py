from PIL import Image
import numpy as np, matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb


files = ["Mystery1.csv", "Mystery2.data", "Mystery3.data", "Mystery4.data", "Mystery5.data"]

def create_show_image(rgb, f):
    img = Image.fromarray(rgb)
    img.save(f.rsplit(".", 1)[0] + ".png")
    plt.figure(figsize=(6, 6))
    plt.imshow(img)
    plt.title(f)
    plt.axis("off")
    plt.show()

for f in files:
    a = np.loadtxt(f, delimiter=",")
    
    # Divide by 1000 to normalize values to make life easier in RGB calculations
    t = np.clip(a / 1000.0, 0, 1)
    
    # Messing with hsv values to make color mapping more gradual, these produce an image that resembles what I'm trying to recreate
    hue = (3 * t) % 1.0
    saturation = np.ones_like(t)
    brightness = np.clip(
    np.minimum(t, 1 - t) / 0.05,
    0,
    1
)

    hsv = np.stack([hue, saturation, brightness], axis=-1)
    rgb = np.round(255 * hsv_to_rgb(hsv)).astype(np.uint8)
    
    create_show_image(rgb, f)
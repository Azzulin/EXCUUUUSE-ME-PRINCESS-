"""Tiles PNG shots into one contact sheet (4 per row), using pngstat's reader. Usage: sheet.py out.png in1.png ..."""
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from pngstat import read_png, write_png  # noqa: E402

imgs = [read_png(p)[..., :3] for p in sys.argv[2:]]
imgs = [i[::max(1, i.shape[1] // 480), ::max(1, i.shape[1] // 480)] for i in imgs]
h = max(i.shape[0] for i in imgs)
w = max(i.shape[1] for i in imgs)
cols = 3
rows = (len(imgs) + cols - 1) // cols
sheet = np.zeros((rows * (h + 4), cols * (w + 4), 3), np.uint8)
for k, im in enumerate(imgs):
    r, c = divmod(k, cols)
    sheet[r * (h + 4):r * (h + 4) + im.shape[0], c * (w + 4):c * (w + 4) + im.shape[1]] = im
write_png(sys.argv[1], sheet)
print('sheet', sheet.shape)

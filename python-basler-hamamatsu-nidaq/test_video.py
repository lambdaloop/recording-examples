from skvideo import io
import matplotlib.pyplot as plt
import numpy as np

fname = 'videos/2021-07-14--20-06-14_4.avi'
reader = io.FFmpegReader(fname, outputdict={'-pix_fmt': 'rgb48le'})

img = next(reader)

plt.imshow(img / np.max(img))
plt.show()
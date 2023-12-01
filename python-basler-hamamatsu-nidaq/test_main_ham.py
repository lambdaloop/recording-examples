from cam_pylon import PylonCamera
from cam_ham import HamamatsuCamera
from dac_trigger import DACTrigger
from writers import Previewer
from multiprocessing import Queue
from pypylon import pylon

# tlFactory = pylon.TlFactory.GetInstance()
# devices = tlFactory.EnumerateDevices()
# for device in devices:
#     print(device.GetSerialNumber())

# serial_nums = ['22728396', '23810097', '23810098']

cams = [HamamatsuCamera(verbose=True)]
trigger = DACTrigger()
previewer = Previewer()

# setup everything

qs = [Queue() for _ in cams]
for q, cam in zip(qs, cams):
    cam.setup(q)
dims = [cam.get_dims() for cam in cams]
ranges = [cam.get_range() for cam in cams]
previewer.setup(qs, dims, ranges)

trigger.setup(length=3, fps_ham=30.0)

# start collecting
for cam in cams:
    cam.start(n_frames=40)
trigger.start()
previewer.start()

# wait to finish collection
arr = trigger.finish()
for cam in cams:
    result = cam.finish()

import matplotlib.pyplot as plt
plt.figure(1)
plt.clf()
plt.subplot(2, 1, 1)
plt.plot(arr)
plt.subplot(2, 1, 2)
plt.imshow(result, cmap='gray')
plt.draw()
plt.show(block=False)
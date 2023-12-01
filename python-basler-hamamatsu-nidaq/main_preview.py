from numpy.lib.arraysetops import isin
from cam_pylon import PylonCamera
from dac_trigger import DACTrigger
from writers import Previewer, empty_queues
from multiprocessing import Queue
from pypylon import pylon
from cam_ham import HamamatsuCamera
import time

tlFactory = pylon.TlFactory.GetInstance()
devices = tlFactory.EnumerateDevices()
for device in devices:
    print(device.GetSerialNumber())

ham_params = {
    'fps': 20.0,
    'exposure': 0.010,
    'trigger': False, 
    'roi': {'x': 128, 'width': 1000,
            'y': 128, 'height': 1000},
}

serial_nums = ['22728396', '23810097', '23810098']

basler_params_default = {
    'trigger': True,
    'exposure': 0.002
}
rois_basler = [
    {'x': 64, 'y': 100, 'width': 320, 'height': 300},
    {'x': 64, 'y': 100, 'width': 320, 'height': 300},
    {'x': 64, 'y': 100, 'width': 320, 'height': 300},
]
basler_params = []
for roi in rois_basler:
    d = dict(basler_params_default)
    d['roi'] = roi
    basler_params.append(d)

cams = [PylonCamera(s, p) for s, p in zip(serial_nums, basler_params)]  + \
       [HamamatsuCamera(ham_params, verbose=True)]
# cams = [HamamatsuCamera(verbose=True)]
# cams[0].verbose = True

trigger = DACTrigger()
previewer = Previewer()

# setup everything
trigger.setup(length=1.0, fps_basler=20.0, fps_ham=20.0, repeat=True)

qs = [Queue() for _ in cams]
for q, cam in zip(qs, cams):
    cam.setup(outq=q)
dims = [cam.get_dims() for cam in cams]
ranges = [cam.get_range() for cam in cams]
previewer.setup(qs, dims, ranges)

for cam in cams:
    if isinstance(cam, HamamatsuCamera):
        cam.downsample = 4 ## too slow to plot otherwise

# start collecting
for cam in cams:
    cam.start()
trigger.start()

previewer.start()

# wait to finish collection
for cam in cams:
    if isinstance(cam, HamamatsuCamera):
        cam.should_stop = True

print('trigger')
arr = trigger.finish()

time.sleep(0.1)
empty_queues(qs)

print('cameras')
for cam in cams:
    result = cam.finish()
print('finished?')


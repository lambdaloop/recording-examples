from cam_pylon import PylonCamera
from cam_ham import HamamatsuCamera
from dac_trigger import DACTrigger
from writers import Previewer, VideoCollector
from multiprocessing import Queue
from pypylon import pylon
import os
from datetime import datetime
import time
import toml

import warnings
warnings.simplefilter("ignore", ResourceWarning)

import atexit
import os
import readline

histfile = 'history'
try:
    readline.read_history_file(histfile)
    readline.set_history_length(1000)
except FileNotFoundError:
    pass
atexit.register(readline.write_history_file, histfile)

suffix = input("Experiment name: ")
suffix = suffix.strip()
if suffix == '':
    suffix = 'test'

# tlFactory = pylon.TlFactory.GetInstance()
# devices = tlFactory.EnumerateDevices()
# for device in devices:
#     print(device.GetSerialNumber())

prefix = r'E:\Data'
d = datetime.now().strftime('%Y-%m-%d')
t = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
name = t + '_' + suffix
folder = os.path.join(prefix, d)
os.makedirs(folder, exist_ok=True)
fname_format = os.path.join(folder, name + '_{}.avi')
fname_toml = os.path.join(folder, name + '.toml')

serial_nums = ['22728396', '23810097', '23810098']

length = 3.0

p_ham = {
    'fps': 100.0,
    'exposure': 0.01,
    'trigger': True, 
    'roi': {'x': 128, 'width': 1000,
            'y': 128, 'height': 1000},
}

serial_nums = ['22728396', '23810097', '23810098']

p_basler = {
    'trigger': True,
    'fps': 200.0,
    'exposure': 0.002
}
rois_basler = [
    {'x': 96, 'y': 384, 'width': 640, 'height': 500},
    {'x': 0, 'y': 0, 'width': 832, 'height': 632},
    {'x': 0, 'y': 0, 'width': 832, 'height': 632},
]
basler_params = []
for roi in rois_basler:
    d = dict(p_basler)
    d['roi'] = roi
    basler_params.append(d)

v_basler = {'-vcodec': 'h264_nvenc', 
            '-cq': '24', '-pix_fmt': 'yuv420p',
            '-preset': 'll', '-tune': 'ull'}
v_ham = {'-crf': '20', '-pix_fmt': 'yuv444p10le'}

nframes_basler = int(p_basler['fps'] * length)
nframes_ham = int(p_ham['fps'] * length)

cams = [PylonCamera(s, p) for s, p in zip(serial_nums, basler_params)]
cams += [HamamatsuCamera(p_ham)]
cams[0].verbose = True

all_fps = [p_basler['fps'] for _ in serial_nums] + [p_ham['fps']]

cam_names = [cam.get_name() for cam in cams]
all_params = [cam.get_params() for cam in cams]
param_dict = dict(zip(cam_names, all_params))
fnames = [ fname_format.format(x) for x in cam_names ]

with open(fname_toml, 'w') as f:
    toml.dump(param_dict, f)

vc_params = [v_basler if isinstance(c, PylonCamera) else v_ham for c in cams]
video_writers = [VideoCollector(fname, fps, v) 
                for fname, fps, v in zip(fnames, all_fps, vc_params)]

trigger = DACTrigger()

# setup everything
trigger.setup(length=length+2.0/p_ham['fps'], 
              fps_basler=p_basler['fps'], 
              fps_ham=p_ham['fps'])

qs = [Queue() for _ in cams]
for q, cam, vw in zip(qs, cams, video_writers):
    cam.setup(q)
    vw.setup(q)

# start collecting
for vw in video_writers:
    vw.start()
for cam in cams:
    if isinstance(cam, HamamatsuCamera):
        cam.start(nframes=nframes_ham)
    else:
        cam.start(nframes=nframes_basler)

time.sleep(2.0) # give cameras time to setup
trigger.start()

# wait to finish collection
print('finish')
arr = trigger.finish()

print('cams ')
for cam in cams:
    result = cam.finish()

print('writers')
for vw in video_writers:
    vw.finish()


print('done')

# print('plot')
# import matplotlib.pyplot as plt
# plt.figure(1)
# plt.clf()
# plt.subplot(2, 1, 1)
# plt.plot(arr)
# plt.subplot(2, 1, 2)
# plt.imshow(result, cmap='gray')
# plt.draw()
# plt.show(block=True)
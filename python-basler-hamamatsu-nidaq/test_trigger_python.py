import nidaqmx
from nidaqmx.constants import AcquisitionType
import numpy as np
import threading
import time

def acquire_data(task, n_samples, outdict):
    task.start()
    arr = task.read(n_samples)
    outdict['out'] = arr
    task.stop()

dac_rate = 10000.0
frame_rate = 200.0

n_samp = int(7.0 * dac_rate)
sig = np.zeros(n_samp)

interval = dac_rate / frame_rate 
# box_width = int(interval / 3)
box_width = 20
i = 1000
while i < n_samp:
    i += interval
    ix = int(round(i))
    sig[ix:ix+box_width] = 5

out = np.array([sig, sig])

task = nidaqmx.Task()
task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
task.ao_channels.add_ao_voltage_chan("Dev1/ao1")
task.timing.cfg_samp_clk_timing(dac_rate, sample_mode=AcquisitionType.FINITE, 
    samps_per_chan=len(out[0]))

task2 = nidaqmx.Task()
task2.ai_channels.add_ai_voltage_chan("Dev1/ai0")
task2.timing.cfg_samp_clk_timing(dac_rate, sample_mode=AcquisitionType.CONTINUOUS)


dd = dict()
read_thread = threading.Thread(target=acquire_data, args=(task2, n_samp+200, dd))
read_thread.start()
task.start()
task.write(out, auto_start=False)
read_thread.join()
task.stop()


task.close()
task2.close()

arr = dd['out']

import matplotlib.pyplot as plt

plt.figure(1)
plt.clf()
plt.plot(arr)
plt.draw()
plt.show(block=True)
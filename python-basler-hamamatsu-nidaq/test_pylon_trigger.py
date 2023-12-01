
import nidaqmx
from nidaqmx.constants import AcquisitionType, WAIT_INFINITELY
import numpy as np
import threading
import time

def read_dac(task, n_samples, outdict):
    task.start()
    arr = task.read(n_samples)
    outdict['out'] = arr
    outdict['run'] = True
    task.stop()

def write_dac(task, towrite):
    task.write(towrite, auto_start=False)
    task.start()
    task.wait_until_done(timeout=10)
    task.stop()

def get_trigger_signal(frame_rate, n_samp, dac_rate):
    sig = np.zeros(n_samp)
    interval = dac_rate / frame_rate 
    box_width = min(30, interval // 2)
    i = 20
    while i < n_samp:
        i += interval
        ix = int(round(i))
        sig[ix:ix+box_width] = 3.5
    return sig

def setup_trigger(fps_basler=50.0, fps_ham=30.0, dac_rate=10000.0, length=1.0):
    n_samp = int(length * dac_rate)
    sig_basler = get_trigger_signal(fps_basler, n_samp, dac_rate)
    sig_ham = get_trigger_signal(fps_ham, n_samp, dac_rate)

    out = np.array([sig_ham, sig_basler])

    task_r = nidaqmx.Task()
    task_r.ai_channels.add_ai_voltage_chan("Dev1/ai0")
    task_r.timing.cfg_samp_clk_timing(dac_rate, sample_mode=AcquisitionType.CONTINUOUS)

    task_w = nidaqmx.Task()
    task_w.ao_channels.add_ao_voltage_chan("Dev1/ao0")
    task_w.ao_channels.add_ao_voltage_chan("Dev1/ao1")
    task_w.timing.cfg_samp_clk_timing(dac_rate, sample_mode=AcquisitionType.FINITE, 
        samps_per_chan=len(out[0]))

    dd = {'run': False}
    read_thread = threading.Thread(target=read_dac, args=(task_r, n_samp+200, dd))
    write_thread = threading.Thread(target=write_dac, args=(task_w, out))

    threads = (read_thread, write_thread)
    tasks = (task_r, task_w)

    return threads, tasks, dd

def start_trigger(threads, tasks, commdict):
    read_thread, write_thread = threads
    read_thread.start()
    write_thread.start()

def finish_trigger(threads, tasks, commdict):
    read_thread, write_thread = threads
    task_r, task_w = tasks
    read_thread.join()
    write_thread.join()
    task_w.close()
    task_r.close()
    arr = commdict['out']
    return arr

if __name__ == '__main__':
    trigger_params = setup_trigger()
    start_trigger(*trigger_params)
    arr = finish_trigger(*trigger_params)

    import matplotlib.pyplot as plt

    plt.figure(1)
    plt.clf()
    plt.plot(arr)
    plt.draw()
    plt.show(block=False)
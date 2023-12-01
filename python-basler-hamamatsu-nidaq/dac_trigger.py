
import nidaqmx
from nidaqmx.constants import AcquisitionType, WAIT_INFINITELY
import numpy as np
import threading
import time



def get_trigger_signal(frame_rate, n_samp, dac_rate):
    sig = np.zeros(n_samp)
    interval = dac_rate / frame_rate 
    box_width = min(20, interval - 10)
    i = 0
    while i < n_samp:
        i += interval
        ix = int(round(i))
        sig[ix:ix+box_width] = 5
    return sig

class DACTrigger():
    def __init__(self, 
                 channels_in=["Dev1/ai0"], 
                 channels_out=["Dev1/ao0", "Dev1/ao1"]):
        self.channels_in = channels_in
        self.channels_out = channels_out
    
    def setup(self, fps_basler=50.0, fps_ham=30.0, dac_rate=10000.0, length=1.0, repeat=False):
        self.length = length
        n_samp = int(length * dac_rate)
        self.repeat = repeat
        sig_basler = get_trigger_signal(fps_basler, n_samp, dac_rate)
        sig_ham = get_trigger_signal(fps_ham, n_samp, dac_rate)

        out = np.array([sig_ham, sig_basler])

        self.commdict = {'run': False}
        if len(self.channels_in) > 0:
            self.task_r = task_r = nidaqmx.Task()
            for ch in self.channels_in:
                task_r.ai_channels.add_ai_voltage_chan(ch)
            task_r.timing.cfg_samp_clk_timing(dac_rate, sample_mode=AcquisitionType.CONTINUOUS)
            self.read_thread = threading.Thread(target=self.read_dac, args=(n_samp+200,))
        else:
            self.task_r = None
            self.read_thread = None

        if len(self.channels_out) > 0:
            self.task_w = task_w = nidaqmx.Task()
            for ch in self.channels_out:
                task_w.ao_channels.add_ao_voltage_chan(ch)
            task_w.timing.cfg_samp_clk_timing(dac_rate, sample_mode=AcquisitionType.FINITE, 
                samps_per_chan=len(out[0]))
            self.write_thread = threading.Thread(target=self.write_dac, args=(out,))
        else:
            self.task_w = None
            self.write_thread = None

    def read_dac(self, n_samples):
        self.task_r.start()
        arr = self.task_r.read(n_samples, timeout=self.length+1)
        self.commdict['out'] = arr
        self.commdict['run'] = True
        self.task_r.stop()

    def write_dac(self, towrite):
        task = self.task_w
        while True:
            task.write(towrite, auto_start=False)
            task.start()
            task.wait_until_done(timeout=self.length+1)
            task.stop()
            if not self.repeat: break
        task.stop()

    def start(self):
        if self.read_thread:
            self.read_thread.start()
        if self.write_thread:
            self.write_thread.start()

    def finish(self):
        self.repeat = False
        if self.read_thread: self.read_thread.join()
        if self.write_thread: self.write_thread.join()
        if self.task_w: self.task_w.close()
        if self.task_r: self.task_r.close()
        arr = self.commdict['out']
        return arr

if __name__ == '__main__':
    trigger = DACTrigger()
    trigger.setup()
    trigger.start()
    arr = trigger.finish()
    
    import matplotlib.pyplot as plt

    plt.figure(1)
    plt.clf()
    plt.plot(arr)
    plt.draw()
    plt.show(block=False)
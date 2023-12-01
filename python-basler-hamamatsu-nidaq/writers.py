

import time
from multiprocessing import Queue
from queue import Empty

import matplotlib.pyplot as plt
import numpy as np
from imageio import get_writer
import threading
import skvideo.io

def empty_queues(queues):
    for q in queues:
        while q.qsize() > 0:
            q.get()

class Previewer():
    def __init__(self):
        pass

    def on_close(self, event):
        self.should_stop = True

    def setup(self, queues, dims, ranges):
        self.queues = queues
        n = len(queues)
        self.ims = []
        self.fig = plt.figure(2)
        self.fig.canvas.mpl_connect('close_event', self.on_close)
        plt.clf()
        for i, (dim, r) in enumerate(zip(dims, ranges)):
            plt.subplot(1, n, i+1)
            z = np.zeros(dim)
            im = plt.imshow(z, vmin=r[0], vmax=r[1], 
                            aspect='equal', cmap='gray')
            plt.axis('off')
            plt.title(i+1)
            self.ims.append(im)
        plt.draw()
        plt.show(block=False)
        plt.tight_layout()
        plt.pause(0.001)

        self.should_stop = False

    def start(self):
        finished = [False for _ in self.queues]
        while True:
            if all(finished) or self.should_stop: break
            for i, q in enumerate(self.queues):
                if finished[i]: continue
                try:
                    d = q.get(timeout=0.01)
                except Empty:
                    continue
                while q.qsize() > 0:
                    d = q.get()
                if d is None:
                    finished[i] = True
                else:                
                    self.ims[i].set_data(d)
            try:
                self.fig.canvas.flush_events()
                plt.draw()
                plt.pause(0.001)
            except:
                break

        plt.close('all')

    def finish(self):
        for q in self.queues:
            q.close()

        
def wrap_frame(frame):
    if len(frame.shape) == 3:
        return frame
    elif frame.dtype == 'uint8':
        return frame
    elif frame.dtype == 'uint16':
        # out = np.zeros(frame.shape + (3,), dtype='uint8')
        # out[:, :, 1] = np.right_shift(frame, 8)
        # out[:, :, 0] = np.mod(frame, 256) 
        ## TODO: figure out how to do this in 12 bits
        # out = np.left_shift(np.clip(frame, 0, 2**10-1), 6)
        out = np.zeros(frame.shape + (3,), dtype='uint16')
        f = np.mod(frame, 2**10)
        out[:, :, 2] = np.left_shift(f, 6)
        out[:, :, 1] = np.left_shift(np.clip(frame, 0, 2**10-1), 6)
        out[:, :, 0] = np.left_shift(np.right_shift(frame, 10), 6)
        return out


class VideoCollector():
    def __init__(self, videoname, fps, params={}):
        self.videoname = videoname
        self.fps = fps
        self.params = params
    
    def setup(self, inq):
        self.inq = inq
        # self.writer = get_writer(
        #     self.videoname,
        #     fps=self.fps,
        #     codec='libx264', 
        #     quality=None,  # disables variable compression...0 to 10
        #     bitrate=None, #1000000, # set bit rate
        #     pixelformat='yuv420p10le',  # widely used
        #     ffmpeg_params=['-preset','ultrafast','-crf','20', 
        #                    '-tune', 'zerolatency'],
        #     input_params=None,
        # )
        outputdict = {
            '-vcodec': 'libx264', 
            '-pix_fmt': 'yuv444p10le',
            '-crf': '20', 
            '-preset': 'ultrafast', 
            '-tune': 'zerolatency'
        }
        for k,v in self.params.items():
            outputdict[k] = v
        self.writer = skvideo.io.FFmpegWriter(self.videoname, inputdict={
            '-framerate': str(self.fps)
        }, outputdict=outputdict)
        self.save_thread = threading.Thread(target=self._save)

    def _save(self):
        while True:
            frame = self.inq.get()
            if frame is None:
                break
            else:
                wrapped = wrap_frame(frame)
                self.writer.writeFrame(wrapped)
        self.writer.close()

    def start(self):
        self.save_thread.start()
    
    def finish(self):
        self.save_thread.join()
        self.inq.close()


from hamamatsu.dcam import \
    EImagePixelType, EReadoutSpeed, ESubArrayMode, ETriggerActive, ETriggerPolarity, ETriggerSource
from hamamatsu.dcam import dcam, Stream, copy_frame
import time
import threading

class HamamatsuCamera():
    def __init__(self, params={}, verbose=False):
        self.verbose = verbose
        self.camera_params = params

    def _setup_camera(self):
        dcam.open()
        camera = dcam[0]
        self.camera = camera
        camera.open()

        pp = self.camera_params

        camera['image_pixel_type'] = EImagePixelType.MONO16

        camera['readout_speed'] = EReadoutSpeed.FAST


        if pp.get('trigger', True):
            camera['trigger_source'] = ETriggerSource.EXTERNAL
            camera['trigger_active'] = ETriggerActive.SYNCREADOUT
            camera['trigger_polarity'] = ETriggerPolarity.POSITIVE
        else:
            camera['trigger_source'] = ETriggerSource.INTERNAL
        camera['trigger_delay'] = 0 # go go go

        camera['exposure_time'] = pp.get('exposure', 0.010)

        # crop window
        if pp.get('roi', False):
            roi = pp['roi']
            camera['subarray_hsize'] = roi['width']
            camera['subarray_vsize'] = roi['height']
            camera['subarray_hpos'] = roi['x']
            camera['subarray_vpos'] = roi['y']
            camera['subarray_mode'] = ESubArrayMode.ON
        else:
            camera['subarray_mode'] = ESubArrayMode.OFF            

    def get_name(self):
        return 'ham'

    def get_params(self):
        return self.camera_params

    def setup(self, outq=None, downsample=1):
        self._setup_camera()
        self.outq = outq
        self.downsample = downsample

    def get_dims(self):
        width = self.camera['image_width'].value
        height = self.camera['image_height'].value
        return (height, width)

    def get_range(self):
        return (0, 1024)

    def _collect(self):
        ds = self.downsample
        framenum = 0
        while True:
            with Stream(self.camera, self.nframes) as stream:
                self.camera.start()
                t = time.time()
                for i, frame_buffer in enumerate(stream):
                    if self.should_stop: break
                    self.latest = frame = copy_frame(frame_buffer)
                    if self.outq is not None:
                        if ds > 1:
                            self.outq.put(frame[::ds, ::ds])
                        else:
                            self.outq.put(frame)
                    dt = time.time() - t + 1e-6
                    t += dt
                    framenum += 1
                    if self.verbose:
                        print('{} {:.3f} {:.3f}'.format(framenum, dt, 1/dt))

            if self.should_stop or (not self.repeat):
                break
        if self.outq is not None:
            self.outq.put(None)

    def start(self, nframes=-1):
        if nframes < 0:
            self.nframes = 120
            self.repeat = True
        else:
            self.nframes = nframes
            self.repeat = False
        self.should_stop = False
        self.collect_thread = threading.Thread(target=self._collect)
        self.collect_thread.start()

    def finish(self, force=False):
        if self.repeat or force:
            self.should_stop = True
            self.repeat = False
        self.collect_thread.join()
        self.camera.close()
        return self.latest
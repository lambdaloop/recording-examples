from pypylon import pylon
from pypylon import genicam
import time
import threading
import numpy as np

class PylonCamera():
    def __init__(self, serialnum, params={}, verbose=False):
        tlFactory = pylon.TlFactory.GetInstance()
        devices = tlFactory.EnumerateDevices()
        self.device = None
        for device in devices:
            s = device.GetSerialNumber()
            if s == serialnum:
                self.device = device
                break
        if self.device is None:
            raise ValueError("Camera with serial number {} not found".format(serialnum))
        
        self.camera = pylon.InstantCamera(tlFactory.CreateDevice(self.device))
        self.serialnum = serialnum
        self.camera_params = dict(params)
        self.verbose = verbose

    def _setup_camera(self):
        camera = self.camera
        pp = self.camera_params
        camera.Open()

        # TODO: setup cropping here
        camera.Width = camera.Width.Max
        camera.Height = camera.Height.Max
        camera.ExposureTime = pp.get('exposure', 0.002) * 1e6 # in microseconds
        camera.Gain = camera.Gain.Max

        camera.PixelFormat = "Mono8"

        # camera.AcquisitionFrameRate = 200.0
        camera.AcquisitionFrameRate = pp.get('fps', camera.ResultingFrameRate())

        camera.MaxNumBuffer = 100

        camera.LineSelector= "Line4"
        camera.LineMode= "Output"
        camera.LineInverter=False
        camera.LineSource="ExposureActive"

        if pp.get('trigger', True):
            camera.LineSelector="Line3"
            camera.LineMode="Input"
            camera.TriggerSelector="FrameStart"
            camera.TriggerMode="On"
            camera.TriggerSource="Line3"
            camera.TriggerActivation="RisingEdge"
            camera.TriggerDelay=0
        else:
            camera.TriggerMode = "Off"

        if pp.get('roi', False):
            roi = pp['roi']
            camera.OffsetX = 0
            camera.OffsetY = 0
            camera.Width = roi['width']
            camera.Height = roi['height']
            camera.OffsetX = roi['x']
            camera.OffsetY = roi['y']

    def get_name(self):
        return self.serialnum

    def get_params(self):
        return self.camera_params

    def setup(self, outq=None):
        self._setup_camera()
        self.outq = outq
        self.collect_thread = threading.Thread(target=self._collect)

    def get_dims(self):
        width = self.camera.Width.GetValue()
        height = self.camera.Height.GetValue()
        return (height, width)

    def get_range(self):
        return (0, 255)

    def _collect(self):
        print('start acquisition')
        self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
        # self.camera.WaitForFrameTriggerReady(100)
        result = self.camera.RetrieveResult(10000, 
                    pylon.TimeoutHandling_ThrowException)
        self.latest = latest = np.copy(result.Array)
        # result.Release()
        if self.outq is not None:
            self.outq.put(latest)
        t = time.time()
        framenum = 1
        while self.nframes < 0 or framenum < self.nframes:
            try:
                result = self.camera.RetrieveResult(
                    2000, pylon.TimeoutHandling_ThrowException)
            except:
                break
            
            self.latest = latest = np.copy(result.Array)
            # result.Release()
            if self.outq is not None:
                self.outq.put(latest)
            dt = time.time() - t + 1e-6
            t += dt
            framenum += 1
            if self.verbose:
                if framenum % 50 == 0:
                    print('{} {} {:.3f} {:.3f}'.format(
                        framenum, result.NumberOfSkippedImages, dt, 1/dt))
            if result.NumberOfSkippedImages > 0:
                print(self.serialnum + " " + "A"*30 + "!!!!!")

        if self.outq is not None:
            self.outq.put(None)

    def start(self, nframes=-1):
        self.nframes = nframes
        self.collect_thread.start()

    def finish(self):
        self.collect_thread.join()
        self.camera.Close()
        return self.latest
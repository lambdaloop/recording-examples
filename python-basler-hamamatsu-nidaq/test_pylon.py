from pypylon import pylon
from pypylon import genicam
import time

tlFactory = pylon.TlFactory.GetInstance()
devices = tlFactory.EnumerateDevices()

camera = pylon.InstantCamera(tlFactory.CreateDevice(devices[2]))
camera.Open()

camera.Width = camera.Width.Max
camera.Height = camera.Height.Max
camera.ExposureTime = 2*1000 # in microseconds
camera.Gain = camera.Gain.Max

# camera.AcquisitionFrameRate = 200.0
camera.AcquisitionFrameRate = camera.ResultingFrameRate()

camera.MaxNumBuffer = 1000

camera.LineSelector= "Line4"
camera.LineMode= "Output"
camera.LineInverter=False
camera.LineSource="ExposureActive"

#Set Line 3 to trigger
camera.LineSelector="Line3"
camera.LineMode="Input"
camera.TriggerSelector="FrameStart"
camera.TriggerMode="On"
camera.TriggerSource="Line3"
camera.TriggerActivation="RisingEdge"
camera.TriggerDelay=0

camera.StartGrabbing(pylon.GrabStrategy_LatestImages)
print('start acquisition')
t = time.time()
framenum = 0
for i in range(1000):
    camera.WaitForFrameTriggerReady(100)
    result = camera.RetrieveResult(
        10000, pylon.TimeoutHandling_ThrowException)
    print(result.NumberOfSkippedImages)
    dt = time.time() - t
    t += dt
    framenum += 1
    print('{} {:.3f} {:.3f}'.format(framenum, dt, 1/dt))

camera.Close()

import matplotlib.pyplot as plt
plt.figure(1)
plt.clf()
plt.imshow(result.Array, cmap='gray')
plt.draw()
plt.show(block=False)
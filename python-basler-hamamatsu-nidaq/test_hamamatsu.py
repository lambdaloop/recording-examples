import logging
from hamamatsu.dcam import \
    EImagePixelType, EReadoutSpeed, ESubArrayMode, ETriggerActive, ETriggerPolarity, ETriggerSource
from hamamatsu.dcam import dcam, Stream, copy_frame
import time

logging.basicConfig(level=logging.INFO)
dcam.open()
camera = dcam[0]
camera.open()

camera['image_pixel_type'] = EImagePixelType.MONO16

camera['readout_speed'] = EReadoutSpeed.FAST

# camera['trigger_source'] = ETriggerSource.INTERNAL
camera['trigger_source'] = ETriggerSource.EXTERNAL
camera['trigger_active'] = ETriggerActive.SYNCREADOUT
camera['trigger_polarity'] = ETriggerPolarity.POSITIVE
camera['trigger_delay'] = 0 # go go go

camera['exposure_time'] = 1/30.0-0.001

# crop window
camera['subarray_hpos'] = 100
camera['subarray_hsize'] = 2000
camera['subarray_vpos'] = 200
camera['subarray_vsize'] = 1900
camera['subarray_mode'] = ESubArrayMode.OFF

# print(camera.info)
# # print(camera['image_width'].value, camera['image_height'].value)

# Simple acquisition example
nb_frames = 10
# camera["exposure_time"] = 0.1
with Stream(camera, nb_frames) as stream:
        logging.info("start acquisition")
        camera.start()
        t = time.time()
        for i, frame_buffer in enumerate(stream):
            frame = copy_frame(frame_buffer)
            dt = time.time() - t
            t += dt
            logging.info(f"acquired frame #%d/%d %.3f %.3f %s", i+1, nb_frames, dt, 1/dt, frame.shape)
        logging.info("finished acquisition")

# exposure_time
#  'intensity_lut_mode',
#  'intensity_lut_page',
#  trigger_mode
#  trigger_delay

#  'subarray_hpos',
#  'subarray_hsize',
#  'subarray_mode',
#  'subarray_vpos',
#  'subarray_vsize',

import matplotlib.pyplot as plt
plt.figure(1)
plt.clf()
plt.imshow(frame)
plt.draw()
plt.show(block=False)
#!/usr/bin/env ipython

import netifaces
from goprocam import constants
from goprocam.GoProCamera import GoPro
import io
import time
import threading
from subprocess import Popen, PIPE
import sys
import re

if len(sys.argv) >= 2:
    length = int(sys.argv[1])
else:
    length = 5

# socket address is 172.2X.1YZ.51:8080
# last 51 doesn't always show up, so we don't match against that
gopro_ip_regex = r'172\.2([0-9])\.1([0-9][0-9])\.[0-9]+'

ips = []
devices = []
for device in netifaces.interfaces():
    addresses = netifaces.ifaddresses(device).get(netifaces.AF_INET, [])
    for row in addresses:
        if re.match(gopro_ip_regex, row['addr']):
            address = row['addr'].split('.')
            address[len(address) - 1] = "51"
            ip = ".".join(address)
            ips.append(ip)
            devices.append(device)

    # if device[:4] == 'enxd': # not sure if fullproof
    #     ip = GoPro.getWebcamIP(device)
    #     ips.append(ip)
    #     devices.append(device)

print(devices)
print(ips)
# device = devices[0]
# ip = ips[0]

gopros = []
for device, ip in zip(devices, ips):
    gopro = GoPro(
        ip_address=ip, camera=constants.gpcontrol,
        webcam_device=device,
        api_type=constants.ApiServerType.OPENGOPRO)
    gopros.append(gopro)



for gopro in gopros:
    try:
        gopro._request('gopro/camera/control/wired_usb?p=1')
    except:
        pass  # sometimes throws 500 server error when camera is already on wired control mode
    # video mode
    gopro.mode(constants.Mode.VideoMode)
    # no stream
    gopro._request('gopro/camera/stream/stop')
    # best performance
    # gopro._request('gopro/camera/setting?setting=173&option=0')
    # 1080p
    # gopro._request('gopro/camera/setting?setting=2&option=9')
    # 120Hz
    gopro._request('gopro/camera/setting?setting=3&option=1')
    # 240Hz
    # gopro._request('gopro/camera/setting?setting=3&option=0')
    # superview
    # gopro._request('gopro/camera/setting?setting=121&option=3')
    gopro._request('gopro/camera/setting?setting=121&option=0') # wide
    # hypersmooth off
    gopro._request('gopro/camera/setting?setting=135&option=0')
    # auto power down 30 min
    gopro._request('gopro/camera/setting?setting=59&option=7')


time.sleep(1.0)

def record_video(gopro, length):
    gopro.shutter(constants.start)
    time.sleep(length)
    gopro.shutter(constants.stop)

threads = []
for gopro in gopros:
    t = threading.Thread(target=record_video, args=(gopro, length))
    threads.append(t)

for t in threads:
    t.start()

for t in threads:
    t.join()

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
import os
from io import BytesIO
import json
from datetime import datetime, timedelta

if len(sys.argv) >= 2:
    length = int(sys.argv[1])
else:
    length = 2

# socket address is 172.2X.1YZ.51:8080
# last 51 doesn't always show up, so we don't match against that
# gopro_ip_regex = r'172\.2([0-9])\.1([0-9][0-9])\.[0-9]+'
gopro_ip_regex = r'10\.5\.5\.[0-9]+'

GOPRO_URL = 'http://10.5.5.9:8080'

devices = []
for device in netifaces.interfaces():
    addresses = netifaces.ifaddresses(device).get(netifaces.AF_INET, [])
    for row in addresses:
        if re.match(gopro_ip_regex, row['addr']):
            devices.append(device)

import pycurl

def send_curl_request(interface, url, out=None):
    # Create a new CURL object
    curl = pycurl.Curl()

    if out is None:
        out = BytesIO()
    curl.setopt(curl.WRITEDATA, out)

    # Set the interface
    curl.setopt(curl.INTERFACE, interface)

    # Set the URL to send request
    curl.setopt(curl.URL, url)

    # Send the HTTP GET request
    curl.perform()

    # Close the CURL connection
    curl.close()

    if isinstance(out, BytesIO):
        body = out.getvalue()
        return body


def gopro_request(device, url):
    path = os.path.join(GOPRO_URL, url)
    return send_curl_request(device, path)

def gopro_json(device, url):
    path = os.path.join(GOPRO_URL, url)
    raw = send_curl_request(device, path)
    text = raw.decode('utf8')
    return json.loads(text)

def gopro_download(device, path, fname):
    url = os.path.join(GOPRO_URL, path)
    with open(fname, 'wb') as f:
        curl = pycurl.Curl()
        curl.setopt(curl.WRITEDATA, f)
        curl.setopt(curl.INTERFACE, device)
        curl.setopt(curl.URL, url)
        curl.perform()
        curl.close()


def flatten_list(x):
    out = []
    for sublist in x:
        out.extend(sublist)
    return out

print(devices)
# print(ips)
# device = devices[0]
# ip = ips[0]

# gopros = []
# for device, ip in zip(devices, ips):
#     gopro = GoPro(
#         ip_address=ip, camera=constants.gpcontrol,
#         webcam_device=device,
#         api_type=constants.ApiServerType.OPENGOPRO)
#     gopros.append(gopro)



for device in devices:
    print(device)
    # video mode
    gopro_request(device, 'gopro/camera/presets/set_group?id=1000')
    # no stream
    gopro_request(device, 'gopro/camera/stream/stop')
    # best performance
    # gopro._request('gopro/camera/setting?setting=173&option=0')
    # 1080p
    gopro_request(device, 'gopro/camera/setting?setting=2&option=9')
    # 120Hz
    gopro_request(device, 'gopro/camera/setting?setting=3&option=1')
    # 240Hz
    # gopro._request('gopro/camera/setting?setting=3&option=0')
    # superview
    # gopro._request('gopro/camera/setting?setting=121&option=3')
    gopro_request(device, 'gopro/camera/setting?setting=121&option=0') # wide
    # hypersmooth off
    gopro_request(device, 'gopro/camera/setting?setting=135&option=0')
    # auto power down
    gopro_request(device, 'gopro/camera/setting?setting=59&option=0') # never
    # gopro_request(device, 'gopro/camera/setting?setting=59&option=7') # 30 min

    now = datetime.now() - timedelta(hours=1) # gopro is offset by 1 hour
    gopro_request(device, 'gopro/camera/set_date_time?date={}&time={}'.format(
        now.strftime('%Y_%m_%d'), now.strftime('%H_%M_%S')))


time.sleep(1.0)

def record_video(device, length):
    gopro_request(device, 'gopro/camera/shutter/start')
    # gopro.shutter(constants.start)
    time.sleep(length)
    gopro_request(device, 'gopro/camera/shutter/stop')
    # gopro.shutter(constants.stop)

threads = []
for device in devices:
    t = threading.Thread(target=record_video, args=(device, length))
    threads.append(t)

for t in threads:
    start_time = time.time()
    t.start()

for t in threads:
    t.join()

time.sleep(0.5)
# download media example
if False:
    device = devices[0]
    media = gopro_json(device, 'gopro/media/list')['media']
    all_fs = []
    for row in media:
        for f in row['fs']:
            f['d'] = row['d']
        all_fs.extend(row['fs'])
    all_fs_s = sorted(all_fs, key=lambda x: int(x['cre']))
    last = all_fs_s[-1]

    gopro_request(device, 'gopro/media/turbo_transfer?p=1')

    # url: http://10.5.5.9:8080/videos/DCIM/100GOPRO/GH010397.MP4
    path = 'videos/DCIM/{}/{}'.format(last['d'], last['n'])
    gopro_download(device, path, 'test.mp4')

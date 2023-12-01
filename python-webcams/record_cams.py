#!/usr/bin/env python3

import matplotlib.pyplot as plt
import cv2
import numpy as np
import sys
# import skvideo.io
from datetime import datetime
import os.path
import time
import queue
import threading
import argparse
import time


def record(new_session=False, num_cams=4, recording_length=None, target_fps=85, vid_height=360, vid_width=640,
           calibration=False, display_plot=False, should_record=True, outbase='videos-raw'):
    if new_session:
        session = datetime.now().strftime('session-%Y-%m-%d--%H-%M-%S')
        folder = os.path.join(outbase, session)
        os.makedirs(folder)
        print("session:", session)
        return 0

    all_sessions = [os.path.join(outbase, d) for d in os.listdir(outbase)
                    if os.path.isdir(os.path.join(outbase, d))]
    session = max(all_sessions, key=os.path.getmtime)
    session = os.path.basename(session)


    ############ BLE timestamp sent ############
    if calibration:
        trial = 'calibration'
    else:
        trial = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')

    print("session:", session)
    print("trial:", trial)

    outfolder = os.path.join(outbase, session, trial)
    os.makedirs(outfolder, exist_ok=True)

    caps = []
    for cam_id in range(num_cams):
        cap = cv2.VideoCapture(cam_id)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FPS, target_fps)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, vid_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, vid_height)
        caps.append(cap)

    im_test = np.zeros((vid_height, vid_width, 3))

    ims = []

    if display_plot:
        fig = plt.figure(num='Calibration')
        fig.canvas.mpl_connect('close_event', handle_close)
        plt.clf()
        for i in range(6):
            plt.subplot(3, 2, i + 1)
            im = plt.imshow(im_test, aspect='equal')
            plt.axis('off')
            plt.title('camera {}'.format(i))
            ims.append(im)
        plt.draw()
        plt.tight_layout()
        plt.show(block=False)

    if should_record:
        writers = []
        queues = []
        threads = []

        for i in range(num_cams):
            outname = os.path.join(outfolder, 'cam{}.avi'.format(i + 1))
            # writer = skvideo.io.FFmpegWriter(outname, inputdict={
            #         '-framerate': str(target_fps),
            # }, outputdict={
            #     '-vcodec': 'h264'
            # })
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            writer = cv2.VideoWriter(outname, fourcc, target_fps,
                                     (vid_width, vid_height))
            writers.append(writer)

            q = queue.Queue()
            queues.append(q)

            thread = threading.Thread(target=write_frame_thread,
                                      args=(writer, q))
            threads.append(thread)

    ############ Capture frames ############

    # warm up the cameras
    for i in range(10):
        for capnum, cap in enumerate(caps):
            ret, frame = cap.read()

    if should_record:
        for t in threads:
            t.start()

    count = 0
    frame_len = 1 / float(target_fps)
    real_fps = 0
    time_start = time.time()
    first_frame_time = 0
    failed = 0

    frame_times = []

    try:
        while True:
            t = time.time()

            if recording_length is not None and \
                    t - time_start > recording_length:
                raise KeyboardInterrupt

            frames = []
            for capnum, cap in enumerate(caps):
                ret, frame = cap.read()
                if not ret:  # put a blank frame if reading fails
                    frame = im_test
                    failed += 1
                if should_record:
                    queues[capnum].put_nowait(frame)
                frames.append(frame)

            frame_times.append(t)

            if count == 0:
                first_frame_time = t
                time_start = t

            if count % 10 == 0:
                length = time.time() - time_start

                if failed > 0:
                    print(
                        'length: {:4.2f} secs, fps: {:.3f}, framecount: {}, FAILED: {}'.format(length, real_fps, count,
                                                                                               failed))
                else:
                    print('length: {:4.2f} secs, fps: {:.3f}, framecount: {}'.format(length, real_fps, count))

                if display_plot:
                    for capnum, frame in enumerate(frames):
                        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        ims[capnum].set_data(img_rgb)

                    plt.draw()
                    plt.pause(0.0001)

            diff = time.time() - t
            if frame_len > diff:
                time.sleep(frame_len - diff)

            if count > 10:
                real_fps = 1.0 / (time.time() - t)
                offset = (real_fps - target_fps) * 1e-6  # feedback to get right fps
                if frame_len > diff:
                    frame_len += np.clip(offset, -1e-5, 1e-5)

            count += 1


    except KeyboardInterrupt:
        print('Keyboard interrupt!!')
        out = {
            'startcam_time': first_frame_time,
            'frame_times': np.array(frame_times)
        }
        outfile_cam = os.path.join(outfolder, 'frametimes.npz')
        np.savez_compressed(outfile_cam, frame_times=np.array(frame_times))

        if should_record:
            for q in queues:
                q.put_nowait(None)
            for t in threads:
                t.join()
        for i in range(num_cams):
            caps[i].release()
            if should_record:
                writers[i].release()
                # writers[i].close() # if using skvideo
        if display_plot:
            plt.show(block=False)
            plt.pause(3)
            plt.clf()


def write_frame_thread(writer, q):
    while True:
        frame = q.get(block=True)
        if frame is None:
            return
        writer.write(frame)
        # writer.writeFrame(frame)


def handle_close(evt):
    raise KeyboardInterrupt



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Select video attributes for this session',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--new-session', action='store_true',
                        help='create a new session and exit')
    parser.add_argument('--num-cams', type=int, default=4,
                        help='number of cameras to record from')
    parser.add_argument('--length', type=int, default=None,
                        help='video length in seconds')
    parser.add_argument('--fps', type=int, default=90,
                        help='video fps target')
    parser.add_argument('--height', type=int, default=360,
                        help='video height in pixels')
    parser.add_argument('--width', type=int, default=640,
                        help='video width in pixels')
    parser.add_argument('--calibration', action='store_true',
                        help='this is a calibration video')
    parser.add_argument('--preview', action='store_true',
                        help='preview the cameras while recording')
    parser.add_argument('--no-record', action='store_true',
                        help='do not record')
    parser.add_argument('--output-path', type=str, default='videos-raw',
                        help="Path to output folder")

    args = parser.parse_args()
    new_session = args.new_session
    num_cams = args.num_cams
    recording_length = args.length
    target_fps = args.fps
    vid_height = args.height
    vid_width = args.width
    calibration = args.calibration
    display_plot = args.preview
    should_record = not args.no_record
    outbase = args.output_path

    if calibration:
        vid_height = 720
        vid_width = 1280
        target_fps = 30
        no_device = True
        display_plot = True

    record(new_session, num_cams, recording_length, target_fps, vid_height, vid_width, calibration, display_plot,
           should_record, outbase)

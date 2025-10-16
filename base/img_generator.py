import numpy as np
import cv2
import time
import threading

''' 
This module will serve as a 'virtual camera' that creates frames at a set framerate and resolution.
''' 

class ImageGenerator:
    def __init__(self, framerate=30, resolution=(1000, 1000)):
        
        self.framerate = framerate

        self.width = resolution[0]
        self.height = resolution[1]

        self.running = False
        self.thread = None

        self.frame = None

        self.frame_count = 0

        self.last_execution_time = 0
        self.avg_execution_time = 0

        self.frame_done_callback = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.generate_frames)
        self.thread.start()
        print(f"Image generator started. Resolution: {self.width}x{self.height}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.thread = None
        self.frame = None
        print(f"Image generator stopped. Total frames generated: {self.frame_count}")

    def generate_frames(self):
        while self.running:
            start_time = time.perf_counter()

            source_frame = np.random.randint(0, 4096, (self.height, self.width, 3), dtype=np.uint16)

            # convert to synthetic BayerRG pattern (same as Basler Camera)
            bayer = np.empty((self.height, self.width), dtype=np.uint16)
            bayer[0::2, 0::2] = source_frame[0::2, 0::2, 0]  # R
            bayer[0::2, 1::2] = source_frame[0::2, 1::2, 1]  # G
            bayer[1::2, 0::2] = source_frame[1::2, 0::2, 1]  # G
            bayer[1::2, 1::2] = source_frame[1::2, 1::2, 2]  # B

            end_time = time.perf_counter()
            self.last_execution_time = end_time - start_time
            #print(f"Frame generation execution time: {execution_time:.6f} seconds")
            self.frame_count += 1

            time.sleep(1/self.framerate)

            if self.frame_done_callback:
                self.frame_done_callback(bayer)

    def get_frame(self):
        return self.frame

    def is_running(self):
        return self.running

    def calculate_avg_execution_time(self):
        pass

    def register_callback(self, callback):
        self.frame_done_callback = callback
    



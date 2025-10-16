import cv2
import numpy as np
import time
import threading

class ImageProcessor:
    def __init__(self):
        self.thread = None
        self.running = False

        self._raw_frame = None
        self._processed_frame = None

        self.frame_done_callback = None

        self.scale_factor = 1.0 / 4095.0

    def start(self):
        print("Image processor started")
        self.running = True
        self.thread = threading.Thread(target=self.process_frames)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.thread = None
        print("Image processor stopped")
    
    def process_frames(self):
        while self.running:
            if self._raw_frame is not None:
                start_time = time.perf_counter()
                
                rgb = cv2.cvtColor(self._raw_frame, cv2.COLOR_BayerRG2RGB)
                rgb = cv2.normalize(rgb, None, alpha=0.0, beta=1.0, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)

                end_time = time.perf_counter()
                execution_time = end_time - start_time
                print(f"Image processing execution time: {execution_time:.6f} seconds")

                if self.frame_done_callback:
                    self.frame_done_callback(rgb.ravel())
    
    def register_callback(self, callback):
        self.frame_done_callback = callback
    
    def is_running(self):
        return self.running

    def set_raw_frame(self, raw_frame):
        
        self._raw_frame = raw_frame
    
    
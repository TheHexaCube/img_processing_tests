import cv2
import numpy as np
import time
import threading

class ImageProcessor:
    def __init__(self):
        self.thread = None
        self.running = False

        self.frame_done_callback = None

    def start(self):
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
            pass
    
    def register_callback(self, callback):
        self.frame_done_callback = callback
    
    def is_running(self):
        return self.running
    
    